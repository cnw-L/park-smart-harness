"""agent_loop 真实模型调用层 — OpenAI-compatible (qwen/vLLM)。

不依赖 smart_park_assistant 任何包；直接用 openai 官方 SDK。
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from .config import LoopConfig
from .llm import ModelTurn
from .messages import Message, ToolCallReq

# ── 默认配置（本地 qwen vLLM）────────────────────────────────────────────────
_DEFAULT_BASE_URL = "http://localhost:6008/v1"
_DEFAULT_API_KEY  = "local-vllm-llm"
_DEFAULT_MODEL    = "chat"
_DEFAULT_TIMEOUT  = 60.0


# ── 小工具函数（模块私有）────────────────────────────────────────────────────

def _safe_json(s: str | None) -> dict:
    """把 tool_call arguments 字符串解为 dict；格式有误时返回 {}（不崩溃）。"""
    try:
        return json.loads(s or "{}")
    except (json.JSONDecodeError, ValueError):
        return {}


def _reasoning_text(message: Any) -> str:
    """从 OpenAI message 对象中提取思考链文本（兼容 qwen reasoning / reasoning_content）。"""
    reasoning = getattr(message, "reasoning", None)
    if reasoning is None:
        reasoning = getattr(message, "reasoning_content", None)
    if isinstance(reasoning, str):
        return reasoning
    if reasoning:
        return str(reasoning)
    return ""


def _qwen_extra_body(enable_thinking: bool) -> dict:
    """生成 qwen/vLLM 的 extra_body（控制 thinking 开关）。"""
    return {"chat_template_kwargs": {"enable_thinking": enable_thinking}}


# ── 主类 ─────────────────────────────────────────────────────────────────────

class OpenAIModelCaller:
    """实现 ModelCaller Protocol，调用 OpenAI-compatible (qwen vLLM) 模型。

    支持原生 tool calling；保留 tool_calls / tool_call_id 以维持多轮工具对话。
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        extra_body_mode: str = "qwen_vllm",
        timeout: float = _DEFAULT_TIMEOUT,
        enable_thinking: bool = False,
        client: Any | None = None,
    ) -> None:
        # 配置解析：参数 → 环境变量 → 默认值
        self._base_url = (
            base_url
            or os.getenv("ASSISTANT_LLM_BASE_URL")
            or _DEFAULT_BASE_URL
        )
        self._api_key = (
            api_key
            or os.getenv("ASSISTANT_LLM_API_KEY")
            or _DEFAULT_API_KEY
        )
        self._model = (
            model
            or os.getenv("ASSISTANT_LLM_MODEL")
            or _DEFAULT_MODEL
        )
        self._extra_body_mode = extra_body_mode.strip().lower()
        self._timeout = timeout
        self._enable_thinking = enable_thinking
        # 允许注入假 client（测试用）；None = 首次调用时惰性构建真实 client
        self._client: Any | None = client

    def _get_client(self) -> Any:
        """惰性构建 AsyncOpenAI client（真实网络；测试注入时不走这里）。"""
        if self._client is None:
            import openai  # 仅在真正需要时导入，避免测试依赖
            self._client = openai.AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
                timeout=self._timeout,
            )
        return self._client

    async def __call__(
        self,
        config: LoopConfig | None,
        messages: list[Message],
        tool_schemas: list[dict],
    ) -> ModelTurn:
        client = self._get_client()

        # ── 构建请求 ──────────────────────────────────────────────────────────
        request: dict[str, Any] = {
            "model": config.model if config else self._model,
            "messages": self._to_openai(messages),
            "temperature": config.temperature if config else 0.2,
        }
        if config:
            request["max_tokens"] = config.max_tokens

        if tool_schemas:
            request["tools"] = tool_schemas
            request["tool_choice"] = "auto"

        # qwen/vLLM 需要 extra_body 控制 thinking 模式
        if self._extra_body_mode in {"qwen_vllm", "qwen-vllm", "qwen", "vllm"}:
            request["extra_body"] = _qwen_extra_body(self._enable_thinking)

        # ── 调用模型 ──────────────────────────────────────────────────────────
        # asyncio.wait_for 兜底:httpx 超时管不到事件循环卡死(vLLM worker 挂死不关连接),
        # 与 assistant_core/models.py 一致。
        response = await asyncio.wait_for(
            client.chat.completions.create(**request),
            timeout=self._timeout,
        )

        # ── 解析响应 ──────────────────────────────────────────────────────────
        if not response.choices:
            return ModelTurn(content="")

        msg = response.choices[0].message
        content = str(msg.content or "")

        # 解析 tool_calls
        tool_calls: list[ToolCallReq] = []
        for tc in (msg.tool_calls or []):
            if getattr(tc, "function", None) is None:
                continue   # 防御:vLLM 偶发残缺 tool_call(function 为空)
            tool_calls.append(
                ToolCallReq(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=_safe_json(tc.function.arguments),
                )
            )

        reasoning = _reasoning_text(msg)
        usage_tokens = response.usage.total_tokens if response.usage else 0

        return ModelTurn(
            content=content,
            tool_calls=tool_calls,
            usage_tokens=usage_tokens,
            reasoning=reasoning,
        )

    # ── 消息格式转换 ──────────────────────────────────────────────────────────

    def _to_openai(self, messages: list[Message]) -> list[dict]:
        """把 agent_loop Message 转换为 OpenAI chat dicts，保留 tool calls/results。

        qwen/vLLM 模板限制：system 消息必须放在最前面，不允许出现在对话历史之后。
        S4 计划快照会作为 trailing system 消息追加到 volatile tail；此处将其内容
        折叠（append）到最近的 user 消息中，满足 qwen 模板约束的同时保留计划内容。
        若没有前置 user 消息，则并入 leading system 消息。
        参见 models.py:327 中的 qwen-template 注释。
        """
        raw: list[dict] = []
        for m in messages:
            content = m.content
            if m.role == "system":
                raw.append({"role": "system", "content": content})
            elif m.role == "user":
                raw.append({"role": "user", "content": content})
            elif m.role == "assistant":
                d: dict[str, Any] = {"role": "assistant", "content": content}
                if m.tool_calls:
                    d["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                            },
                        }
                        for tc in m.tool_calls
                    ]
                raw.append(d)
            elif m.role == "tool":
                d = {
                    "role": "tool",
                    "tool_call_id": m.tool_call_id,
                    "content": content,
                }
                if m.name:
                    d["name"] = m.name
                raw.append(d)
            else:
                # 未知 role 透传
                raw.append({"role": m.role, "content": content})

        # ── qwen 系统消息折叠 ─────────────────────────────────────────────────
        # 规则：提取最前面连续的 system 消息合并为一条 leading system；
        # 之后出现的 system 消息（S4 计划快照）折叠到最近的 user 消息 content 中。
        return _fold_trailing_system(raw)


def _fold_trailing_system(raw: list[dict]) -> list[dict]:
    """强制满足 qwen-template 的 system 消息规则。

    1. 收集开头连续 system → 合并为一条 leading system。
    2. 任何出现在非 system 消息之后的 system 消息 → 追加到最近 user 消息的 content
       （用 \\n\\n 分隔）；若没有 user 消息，则合并入 leading system。
    """
    # 第一步：分离前缀 system 块与后续消息
    leading_system_parts: list[str] = []
    i = 0
    while i < len(raw) and raw[i]["role"] == "system":
        leading_system_parts.append(raw[i]["content"])
        i += 1
    rest = raw[i:]  # i 之后（非 system 打头的部分）

    # 第二步：处理 rest 中出现的 system 消息（qwen 不允许）
    result: list[dict] = []
    for item in rest:
        if item["role"] != "system":
            result.append(item)
            continue
        # 找 result 中最后一个 user 消息
        plan_text = item["content"]
        last_user_idx = None
        for j in range(len(result) - 1, -1, -1):
            if result[j]["role"] == "user":
                last_user_idx = j
                break
        if last_user_idx is not None:
            # 折叠到最近 user 消息
            result[last_user_idx] = dict(result[last_user_idx])
            result[last_user_idx]["content"] = (
                result[last_user_idx]["content"] + "\n\n" + plan_text
            )
        else:
            # 没有 user 消息：合并入 leading system
            leading_system_parts.append(plan_text)

    # 第三步：拼装最终列表
    if leading_system_parts:
        leading = {"role": "system", "content": "\n\n".join(leading_system_parts)}
        return [leading, *result]
    return result
