"""智慧园区 · 三环 harness Web Demo(治理工具子系统串联演示)

真 qwen@6008 驱动 agent_loop 内圈 + agent_tools 治理子系统(`build_park_runtime` 一处串联)。
四条演示主线:① 子 agent ReAct 委派(设备管理 facility_agent) ② 控制确认红线(propose→execute→人工确认→deviceCtrl+读回)
③ 权限治理(deny-first ToolLoader:换身份→可见工具集随权限收缩) ④ 知识检索(harness_rag/Fake,带引用、证据不足不臆造)。

运行:
  python scripts/demo_server.py
  → 浏览器打开 http://192.168.2.36:8030 (绑定 0.0.0.0,局域网可访问)

架构:
  - FastAPI + uvicorn,单 demo session(asyncio.Lock 序列化请求)
  - 工具(治理子系统顶层 8):设备管理 facility_agent(子) / 运行查询 record_query(扁平) /
    生活服务 meeting·parking·restaurant_query / 知识检索 knowledge_query / 执行 propose_control·execute_proposal(+ 引擎 plan 元工具)
  - execute_proposal 调用 → gate 判 ask → status=awaiting_confirmation + pending → 前端确认卡 → /api/confirm
  - 身份(/api/identity)固定几个 persona(真实部署来自登录解析);rt.toolset_for 按权限过滤顶层(可见性=减选择)
  - 对外显式:plan 侧边栏(状态徽章) + done_what 进展行 + 控制确认卡 + 最终回答
  - 对内隐式:model 叙述 / tool_call / tool_result / plan-JSON → 折叠在"过程"展开器
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from dataclasses import replace
from pathlib import Path

# 让脚本能 import agent_loop
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 真机配置:加载仓库根 .env(prod-api base / milvus / embedding / reranker 等)。
# override=False → 不覆盖启动时已显式注入的变量(如 token——按 .env 注释不落盘,只在启动 shell 注入)。
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
except Exception:
    pass

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Boundary, InMemoryConversationStore
from agent_loop.loop import run_loop
from agent_loop.messages import Message
from agent_loop.plan import make_plan_tool
from agent_loop.providers import OpenAIModelCaller, _split_think
from agent_loop.tools import LoopToolRegistry
from agent_context.assembler import ParkContextAssembler
from agent_context.compactor import ConversationCompactor, ModelBackedSummarizer
from agent_context.principal import Principal
from agent_tools.backend import FakeBackendClient, ProdApiBackendClient
from agent_tools.catalog import ToolSpec
from agent_tools.runtime import ParkToolRuntime, build_park_runtime

# ── 全局 demo session ────────────────────────────────────────────────────────

_store = InMemoryConversationStore()
# demo 用较短超时:后端 qwen@6008 偶发卡死(实测单次 0.9s~60s+),
# 40s 给正常调用足够裕量,又能让卡死的调用快速失败/重试,不把页面冻 60s。
_model = OpenAIModelCaller(timeout=40.0)


def _build_backend():
    """配了 prod-api 就接真后端(真 device_status/grounding 读);否则假后端。
    真 deviceCtrl 只在人工确认后才发(execute_proposal→ask→/api/confirm),符合红线。"""
    if os.getenv("ASSISTANT_PROJECT_API_BASE_URL"):
        try:
            return ProdApiBackendClient.from_env()
        except Exception:
            pass
    return FakeBackendClient()


def _build_retriever():
    """知识检索器:**默认接真知识库**(vendored harness_rag → milvus@knowledge_chunks + embedding/reranker)。
    `HARNESS_RAG_LIVE=0` 显式退回 Fake(离线/无 milvus 跑 demo);构造失败(缺依赖)也优雅退 Fake。
    注:milvus 临时离线不退 Fake——HarnessRagRetriever 会 surface「检索器构造失败」真因,不掩成假数据。"""
    if os.getenv("HARNESS_RAG_LIVE") == "0":
        return None
    try:
        from agent_tools.rag_adapter import HarnessRagRetriever
        return HarnessRagRetriever()
    except Exception:
        return None                       # 缺 harness_rag 依赖 → Fake(离线 demo 仍可跑)


# 控制执行模式:**默认 real**——deviceCtrl 接口真实存在(/common/device/deviceCtrl),对齐生产
# (agent_runtime 设备控制即真下发),**已有接口不用 simulated 假数据**。真下发只经人工确认卡
# (execute_proposal→ask→/api/confirm,红线:绝不自动批准)+ 读回对账。
# HARNESS_CONTROL_EXECUTION=simulated 可显式退回模拟(无后端/纯演示时用)。
_CONTROL_MODE = "simulated" if os.getenv("HARNESS_CONTROL_EXECUTION") == "simulated" else "real"


def _build_runtime() -> ParkToolRuntime:
    """主串联:`build_park_runtime` 一处建好运行链(治理子系统:顶层工具 + CatalogGate +
    ProposalControlCapability + 共享 store 单例)+ 登录链组件。reset 时重建以清 store/幂等账本。"""
    return build_park_runtime(model_caller=_model, backend=_build_backend(),
                              retriever=_build_retriever(), execution_mode=_CONTROL_MODE)


_rt = _build_runtime()
_control = _rt.subsystem.control        # = ProposalControlCapability(共享 store 单例)
_thread_id = "demo"
_lock = asyncio.Lock()

# 引擎 plan 元工具能力码:plan 也是工具、必须进 catalog 受治(否则 deny-first 把它当未登记拒掉);
# 它是会话级基础设施,所有身份默认可用 → 每个身份都带上 _PLAN_CODE。
_PLAN_CODE = "task:plan"

# ── demo 身份(权限治理可见化)─────────────────────────────────────────────────
# 真实部署:登录 → GET /user/info → PermissionMapper → OrgPolicy → Principal(见 runtime.login)。
# 此 demo:AI token 够不到 RuoYi auth 端点(/user/info 当前 404),故固定几个身份直接构造,
# 用来演示 deny-first ToolLoader——换身份 → rt.toolset_for 重算 → 可见工具集随权限收缩。
_DEMO_TOKEN = os.getenv("ASSISTANT_PROJECT_API_TOKEN", "demo-token")


def _persona(pid, name, role, dept, koujing, caps):
    return Principal(id=pid, name=name, role=role, dept=dept, koujing=koujing,
                     token=_DEMO_TOKEN, permissions=(*caps, _PLAN_CODE))


# 权限分层:运维(全)→ 物业员工(无设备读/控)→ 访客(仅生活+知识)。换身份直观看工具集收缩。
_PERSONAS: dict[str, Principal] = {
    "ops": _persona("ops", "运维管理员", "园区运维·管理员", "设备运维部", "内部·可列技术细节",
                    ("device:read", "device:control", "record:read", "life:read", "knowledge:read")),
    "staff": _persona("staff", "物业员工", "物业·普通员工", "物业服务部", "内部",
                      ("record:read", "life:read", "knowledge:read")),
    "guest": _persona("guest", "访客", "访客·外部", "", "外部·仅公开信息",
                      ("life:read", "knowledge:read")),
}
_PERSONA_ORDER = ("ops", "staff", "guest")
_current_persona = "ops"

# 运行时数据令牌:页面可改(/api/token),透传后端做数据级查询。默认取启动 env(不落盘);
# 仅存内存、不写文件、不进日志、对外只回显掩码。改它只影响数据级 token,能力码仍由 persona 定。
_runtime_token = _DEMO_TOKEN


def _principal() -> Principal:
    # 数据级 token 用运行时令牌覆盖(页面可改);permissions(治理闸)仍由 persona 决定。
    return replace(_PERSONAS[_current_persona], token=_runtime_token)


def _token_hint(tok: str | None) -> str:
    """对外掩码:只回显尾 6 位用于辨识,绝不回显全量令牌。"""
    t = (tok or "").strip()
    if not t or t == "demo-token":
        return ""                              # 未设真令牌(默认占位)
    return "···" + t[-6:]


# 中圈真上下文组装器:控制工具改 execute_proposal(结果套"已执行"框,非"现状")。
_assembler = ParkContextAssembler(control_tools=frozenset({"execute_proposal"}))
# 压缩 v2:超硬阈(~70% 窗)用 aux 模型(此处复用 qwen)摘中段;保头 + token 预算保尾。
_compactor = ConversationCompactor(
    ModelBackedSummarizer(_model),
    hard_token_cap=int(0.7 * 32768), tail_token_budget=3000, keep_first=1)

# LoopConfig 基模板;toolset 按当前身份每轮重算(_make_cfg → rt.toolset_for)。
_CFG_BASE = LoopConfig(
    model="chat", max_tokens=512, temperature=0.2, role="main",
    toolset=[],
    budget=LoopBudget(max_iterations=30),   # 宽上限兜底;真正限速靠无进展看门狗,非死卡轮数
)


def _make_cfg(principal: Principal) -> LoopConfig:
    """ToolLoader:按身份有效能力集过滤顶层 toolset + 追加引擎 plan 元工具(可见性=减选择+第一道安全)。"""
    return replace(_CFG_BASE, toolset=[*_rt.toolset_for(principal), "plan"])


# 顶层工具中文标签(身份面板/确认卡用)
_TOOL_LABEL = {
    "facility_agent": "设备管理", "record_query": "运行查询",
    "meeting_query": "会议室查询", "parking_query": "车位查询",
    "restaurant_query": "餐厅查询", "knowledge_query": "知识检索",
    "propose_control": "控制提案", "execute_proposal": "执行工具·控制",
}


def _identity_view(persona_id: str) -> dict:
    """当前身份 + 其可见顶层工具(rt.toolset_for 实算)→ 前端身份面板(权限治理可见化)。"""
    p = _PERSONAS[persona_id]
    visible = _rt.toolset_for(p)                # 已按权限过滤(不含引擎 plan;plan 是会话基础设施)
    return {
        "persona": persona_id,
        "name": p.name,
        "role": p.role,
        "permissions": [c for c in p.permissions if c != _PLAN_CODE],
        "tools": [{"name": n, "label": _TOOL_LABEL.get(n, n)} for n in visible],
        "personas": [{"id": pid, "name": _PERSONAS[pid].name, "role": _PERSONAS[pid].role}
                     for pid in _PERSONA_ORDER],
        "token_hint": _token_hint(_runtime_token),
        "control_mode": _CONTROL_MODE,             # simulated(默认,不真下发)/ real
    }


# ── 工具注册 ─────────────────────────────────────────────────────────────────

def build_registry(conv_plan) -> LoopToolRegistry:
    """治理子系统的引擎 registry(7 顶层工具,带输出预算)+ 引擎 plan 元工具(随会话 plan 绑定)。
    工具实例来自 _sub.catalog(facility_agent / record_query / 生活×3 / knowledge_query /
    execute_proposal)——共享 _sub.store 单例,故子里 propose 的 handle 父侧 control 能还原。"""
    # plan 也是工具,必须进 catalog 受治——否则 deny-first 闸把它当"未登记"拒掉。
    # 按会话 plan 绑定 handler,但 name/能力码稳定;登记进 catalog(gate 据此查 _PLAN_CODE),
    # 同时进 registry(可执行)。在 to_registry 前登记,使其也带进引擎注册表。
    plan_tool = make_plan_tool(conv_plan)
    _rt.subsystem.catalog.register(ToolSpec(tool=plan_tool, capability_code=_PLAN_CODE))
    return _rt.subsystem.catalog.to_registry()


# ── 辅助:把模型的"对内叙述"清成"对外干净结论" ───────────────────────────────
# 设计:对外只呈现"本次做了什么"的结论,模型的过程叙述(第N步/计划复述/过程话)是对内隐式。
# 模型(qwen)行为不确定,呈现层做确定性兜底清洗,不依赖模型恰好听话。

# 行首"第N步"标号(中文数字 + 阿拉伯数字),只去标号、保留其后实质内容
_STEP_LABEL_RE = re.compile(
    r"^\s*(第\s*[一二三四五六七八九十百零两\d]+\s*步|Step\s*\d+)\s*[:：、.。\s]*",
    re.IGNORECASE,
)
# 整行就是"过程话/纯标签"(无实质结果) → 整行丢弃
_DROP_LINE_RE = re.compile(
    r"^\s*("
    r"计划已(更新|列出|制定|完成)"
    r"|现在?(开始|来|对|汇总|进行|执行)[^\n。！!]*"
    r"|(汇总|总结)(结果|如下)?"
    r"|结果(汇总|如下)"
    r"|以下是?汇总"
    r")\s*[:：。.，,]?\s*$"
)
# 行首的过程引导前缀(后面还跟着实质内容时,只去前缀)
_LEAD_PREFIX_RE = re.compile(
    r"^\s*(计划已(更新|列出|制定|完成)|现在?汇总结果?|现在?开始汇总)\s*[:：。.，,]?\s*"
)


def _clean_final_answer(text: str) -> str:
    """把模型最终消息清成对外干净结论:剥 <think> 思考块、逐行去"第N步"标号、丢过程话/纯标签行、去引导前缀。
    全是思考/过程话则返回空(不出气泡),不回吐未处理原文。"""
    raw = _split_think(text)[0].strip()   # 兜底剥 <think>(主流已在 provider 剥离)
    out: list[str] = []
    for ln in raw.split("\n"):
        s = ln.strip()
        if not s:
            out.append("")
            continue
        s = _STEP_LABEL_RE.sub("", s).strip()
        s = _LEAD_PREFIX_RE.sub("", s).strip()
        if not s or _DROP_LINE_RE.match(s):
            continue
        out.append(s)
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return cleaned   # 全是思考/过程话 -> 空(不出气泡),不回吐未处理原文


# 兼容旧引用名(内部测试 _make_response 用)
def _strip_step_prefixes(text: str) -> str:
    return _clean_final_answer(text)


# ── 辅助:从 tool_call args + tool_result 合成"本次做了什么"摘要行 ──────────

# 治理子系统顶层工具 → 对外进展行的友好前缀(子 agent 的内部 ReAct 由设计封装,主流只见委派+回吐摘要)
_DONE_WHAT_LABEL = {
    "facility_agent": "设备管理",
    "record_query": "运行查询",
    "meeting_query": "会议室",
    "parking_query": "车位",
    "restaurant_query": "餐厅",
    "knowledge_query": "知识检索",
}


def _shorten(text: str, n: int = 80) -> str:
    s = " ".join((text or "").split())          # 折叠换行/多空格,进展行只占一行
    return s[:n] + ("…" if len(s) > n else "")


def _synthesize_done_what(tool_name: str, args: dict, result_text: str, is_error: bool) -> str | None:
    """据工具名/参数/结果合成一行对外可见进展摘要。
    返回 None = 不产生进展行(plan 走侧边栏;pending/blocked 由确认卡或拦截行处理)。
    """
    if tool_name == "plan":
        return None                              # plan 走侧边栏,不在对话区出进展行
    if tool_name == "propose_control":
        return None                              # 控制提案=grounding 内部准备;对外只呈现**确认卡**,
                                                 # 不出"提案已登记"进展行(否则与卡片重复=用户感知的"重复确认")
    # 执行工具:经确认卡 → resolve 后写回的控制结果(content 带 [executed]/[rejected] 标记)
    if tool_name == "execute_proposal" or result_text.startswith(("[executed]", "[rejected]")):
        if is_error:
            return f"✗ 控制执行失败:{_shorten(result_text, 60)}"
        if result_text.startswith("[rejected]"):
            return "✗ 已取消该控制提案,未下发"
        if result_text.startswith("[executed]"):
            # 读回对账信号(accepted/effective)直接透出,呈现"已受理≠已生效"
            tail = result_text.split("readback=", 1)[-1].strip() if "readback=" in result_text else ""
            return f"✓ 控制已下发并读回对账{('('+_shorten(tail, 60)+')') if tail else ''}"
        return "✓ 控制已执行"
    # facility_agent=子助手(委派+回吐摘要);其余(record_query/生活/知识)=主直接查询
    label = _DONE_WHAT_LABEL.get(tool_name)
    if label:
        verb = "委派" if tool_name == "facility_agent" else "查询"
        if is_error:
            return f"✗ {label}{verb}未完成:{_shorten(result_text, 50)}"
        return f"✓ {label}:{_shorten(result_text)}"
    # 其他/未知工具:简短摘要兜底
    if is_error:
        return f"✗ {tool_name} 失败:{_shorten(result_text, 50)}"
    return f"✓ {tool_name} 返回:{_shorten(result_text)}"


# ── 辅助:plan items → 结构化事件负载 ────────────────────────────────────────

def _plan_items_payload(items) -> list[dict]:
    """将 PlanItem 列表序列化为前端可用的结构化列表(用模型自报状态)。"""
    return [
        {"id": item.id, "content": item.content, "status": item.status}
        for item in items
    ]


# ── plan 状态投影:用"循环现实"覆盖模型自报状态 ──────────────────────────────
# 模型(qwen)不可靠地推进 plan 状态(常把控制步提前标 done、或干脆不更新尾步)。
# 侧边栏应反映真实发生了什么,而非模型的声明:
#   已成功执行的实质动作数 = 已完成步数;有动作在飞行中/待确认 = 当前步 doing。
# 纯呈现层投影,不碰引擎、不依赖模型听话。

def _count_done_actions(messages) -> int:
    """已完成的实质动作数:非 plan、非占位、非 blocked、非错误的 tool 结果数。"""
    n = 0
    for m in messages:
        if m.role != "tool":
            continue
        c = m.content or ""
        if c == "[pending_confirmation]" or c.startswith("[blocked]"):
            continue
        if (m.name or "") == "plan" or m.is_error:
            continue
        n += 1
    return n


def _count_called_actions(messages) -> int:
    """已发起的实质动作数:assistant 里非 plan 的 tool_call 数。"""
    n = 0
    for m in messages:
        if m.role == "assistant":
            for tc in m.tool_calls:
                if (tc.name or "") != "plan":
                    n += 1
    return n


def _slice_after_last_plan(messages) -> list:
    """只取最近一次 plan 工具调用之后的消息,把动作计数限定在"当前计划"内。"""
    idx = 0
    for i, m in enumerate(messages):
        if m.role == "assistant" and any((tc.name or "") == "plan" for tc in m.tool_calls):
            idx = i + 1
    return messages[idx:]


def _project_plan(messages, items, completed: bool) -> tuple[list[dict], str]:
    """把真实进度投影到 plan 步骤上(覆盖模型自报状态)。返回 (payload, 签名)。
    线性指针:前 done 步=done;若有动作在飞行/待确认,则第 done 步=doing;其余=todo。
    completed=True(整轮完成)→ 全部 done。"""
    messages = _slice_after_last_plan(messages)
    done = _count_done_actions(messages)
    if completed:
        done = len(items)
        active = False
    else:
        active = _count_called_actions(messages) > done
    payload: list[dict] = []
    for k, it in enumerate(items):
        if k < done:
            st = "done"
        elif k == done and active:
            st = "doing"
        else:
            st = "todo"
        payload.append({"id": it.id, "content": it.content, "status": st})
    sig = f"{done}:{int(active)}:{len(items)}"
    return payload, sig


# ── 轨迹提取(单条消息) ───────────────────────────────────────────────────────

def _extract_internal_events(m, final_stripped: str) -> list[dict]:
    """将单条 Message 转换为对内隐式 process 事件列表。
    不含 done_what 外部进展(那由调用方合成)。
    """
    events: list[dict] = []
    if m.role == "assistant":
        if m.reasoning and m.reasoning.strip():
            events.append({"event": "process", "kind": "think", "text": m.reasoning.strip()})
        if m.content and m.content.strip():
            # 模型的叙述内容(第一步/第二步/汇总…)→ 对内隐式
            # 若内容就是最终回答,不再重复放入 process
            # ★控制挂起轮:模型常在文本里复述"已弹确认卡·请确认是否继续"——与**确认卡按钮**重复
            #   (用户感知的"重复确认")→ 该轮的 say 不出,卡片即唯一确认入口。
            calls_control = any(tc.name == "execute_proposal" for tc in m.tool_calls)
            if m.content.strip() != final_stripped and not calls_control:
                events.append({"event": "process", "kind": "say", "text": m.content.strip()})
        for tc in m.tool_calls:
            events.append({
                "event": "process",
                "kind": "tool_call",
                "name": tc.name,
                "args": tc.arguments,
            })
    elif m.role == "tool":
        content = m.content or ""
        if content == "[pending_confirmation]":
            pass  # pending 卡单独渲染
        elif content.startswith("[blocked]"):
            events.append({
                "event": "process",
                "kind": "blocked",
                "name": m.name or "",
                "text": content,
            })
        else:
            events.append({
                "event": "process",
                "kind": "tool_result",
                "name": m.name or "",
                "text": content,
                "is_error": m.is_error,
            })
    return events


def extract_process(messages: list, start_index: int, final_answer: str | None) -> list[dict]:
    """从 start_index 起提取内部过程条目(对内隐式)。供 _make_response 用。"""
    final_stripped = (final_answer or "").strip()
    items: list[dict] = []
    for m in messages[start_index:]:
        for ev in _extract_internal_events(m, final_stripped):
            payload = {k: v for k, v in ev.items() if k != "event"}
            items.append(payload)
    return items


# ── NDJSON 流式生成器 ─────────────────────────────────────────────────────────

def _ndjson(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"


async def _stream_run(
    *,
    conv,
    before: int,
    run_kwargs: dict,
):
    """
    在后台 task 中运行 run_loop,同时 poll store 吐出流式事件。

    D5 事件类型(NDJSON 每行一个 JSON):
      {"event":"process", "kind":"think"|"say"|"tool_call"|"tool_result"|"blocked", ...}
        → 对内隐式;前端折叠在"过程"展开器
      {"event":"plan", "items":[{"id","content","status"},...],"text":"<sidebar text>"}
        → 对外显式;前端侧边栏渲染带状态徽章的结构化计划
      {"event":"done_what", "text":"<友好过去时摘要>"}
        → 对外显式;前端在对话区显示进展行(工具执行摘要,非模型叙述)
      {"event":"pending", "items": [...]}
        → 对外显式;前端渲染控制确认卡
      {"event":"answer", "text": "<clean final answer>"}
        → 对外显式;干净结论气泡(已剥离 第N步 前缀)
      {"event":"done", "status": "...", "reason": "..."}
    """
    cfg = run_kwargs["cfg"]
    reg = run_kwargs["reg"]
    budget_tracker = run_kwargs["budget_tracker"]
    model = run_kwargs["model"]
    store = run_kwargs["store"]
    control = run_kwargs["control"]
    extra = {k: v for k, v in run_kwargs.items()
             if k not in ("cfg", "reg", "budget_tracker", "model", "store", "control")}

    task = asyncio.create_task(
        run_loop(cfg, conv, reg, budget_tracker, model, store=store, control=control, **extra)
    )

    seen = before  # 已经处理过的 message 下标
    last_plan_sig = ""  # 上一次 plan 的签名(用于去重)

    # pending_tool_calls: tool_call_id -> {name, args} 供合成 done_what
    pending_tool_calls: dict[str, dict] = {}

    # ── 运行计时:每个事件打上自本轮开始的累计毫秒(前端显示步耗时 + 总耗时) ──
    t0 = time.monotonic()

    def stamp(obj: dict) -> dict:
        obj["t_ms"] = int((time.monotonic() - t0) * 1000)
        return obj

    async def flush_new_messages(cur_messages, final_stripped: str):
        nonlocal seen, pending_tool_calls
        lines = []
        while seen < len(cur_messages):
            m = cur_messages[seen]

            if m.role == "assistant":
                # 记录本轮 tool_calls 供后续 tool_result 查找
                # ToolCallReq 使用 .id 而非 .tool_call_id
                for tc in m.tool_calls:
                    pending_tool_calls[tc.id] = {
                        "name": tc.name,
                        "args": tc.arguments or {},
                    }

            if m.role == "tool":
                content = m.content or ""
                # 跳过 pending_confirmation,不合成 done_what(确认卡处理)
                if content != "[pending_confirmation]" and not content.startswith("[blocked]"):
                    # 查找配对的 tool_call
                    tc_id = m.tool_call_id if hasattr(m, "tool_call_id") else None
                    tool_name = m.name or ""
                    args = {}
                    if tc_id and tc_id in pending_tool_calls:
                        args = pending_tool_calls[tc_id].get("args", {})
                        tool_name = pending_tool_calls.get(tc_id, {}).get("name", tool_name) or tool_name
                    elif tool_name and tool_name in {
                        v["name"] for v in pending_tool_calls.values()
                    }:
                        # 回退:按名字查找最近一次 tool_call
                        for v in reversed(list(pending_tool_calls.values())):
                            if v["name"] == tool_name:
                                args = v.get("args", {})
                                break

                    dw = _synthesize_done_what(tool_name, args, content, m.is_error)
                    if dw:
                        lines.append(_ndjson(stamp({"event": "done_what", "text": dw})))

            # 内部过程事件(对内隐式)
            for ev in _extract_internal_events(m, final_stripped):
                lines.append(_ndjson(stamp(ev)))

            seen += 1
        return lines

    # ── 轮询循环 ─────────────────────────────────────────────────────────────
    while not task.done():
        await asyncio.sleep(0.2)
        try:
            cur = await store.load(_thread_id)
        except Exception:
            continue

        # 新到的消息 → 处理并发送事件
        if len(cur.messages) > seen:
            lines = await flush_new_messages(cur.messages, "")
            for line in lines:
                yield line

        # plan 侧边栏变化 → 发送结构化 plan 事件(状态用现实投影,非模型自报)
        if cur.plan.items:
            payload, plan_sig = _project_plan(cur.messages, cur.plan.items, completed=False)
            if plan_sig != last_plan_sig:
                last_plan_sig = plan_sig
                yield _ndjson(stamp({"event": "plan", "items": payload}))

    # ── task 完成后处理尾部 ──────────────────────────────────────────────────
    res = await task  # 拿结果(task 已完成,不阻塞)

    # 计算 final answer
    completed_statuses = {"completed", "budget_exhausted"}
    answer: str = ""
    if res.status in completed_statuses and res.final and res.final.strip():
        candidate = res.final.strip()
        if candidate != "(等待确认)":
            answer = _strip_step_prefixes(candidate)

    # 兜底:终态但没产出有用答案(模型空转被看门狗/预算停 → status=failed/budget_exhausted)
    # → 给用户一句如实的话,而不是空白。(真机实测:最受限身份无对应工具时会 thrash 到 failed)
    if not answer and res.status in ("failed", "budget_exhausted", "error"):
        answer = "抱歉,我没能完成这个请求——它可能超出了我当前的能力或权限范围。可以换个说法,或让我先帮你查询相关信息。"

    final_stripped = answer.strip()

    # 尾部尚未发送的消息(task 完成时 poll 可能落后一拍)
    try:
        cur = await store.load(_thread_id)
    except Exception:
        cur = res.conversation

    if len(cur.messages) > seen:
        lines = await flush_new_messages(cur.messages, final_stripped)
        for line in lines:
            yield line

    # plan 最终状态:整轮 completed → 全部 done;挂起则停在控制步 doing
    if cur.plan.items:
        is_complete = res.status in ("completed", "budget_exhausted")
        payload, plan_sig = _project_plan(cur.messages, cur.plan.items, completed=is_complete)
        if plan_sig != last_plan_sig:
            last_plan_sig = plan_sig
            yield _ndjson({"event": "plan", "items": payload})

    # pending 控制确认卡(execute_proposal 走 gate ask → run_loop 挂起;模型自己调,不再 demo 层接力补发)
    if res.status == "awaiting_confirmation":
        pending_list = []
        for p in (res.pending or []):
            pending_list.append({
                "tool_call_id": p.tool_call_id,
                "name": p.frozen_action["name"],
                "args": p.frozen_action["arguments"],
            })
        if pending_list:
            yield _ndjson(stamp({"event": "pending", "items": pending_list}))
    _gc_abandoned_proposals(res)        # 终态清掉放弃的提案(awaiting 时自身跳过);防跨轮误取陈旧提案

    # 最终回答气泡(对外显式,干净)
    if answer:
        yield _ndjson(stamp({"event": "answer", "text": answer}))

    # done 信号(t_ms = 本轮总耗时)
    yield _ndjson(stamp({"event": "done",
                         "status": res.status,
                         "reason": res.reason or ""}))


# ── FastAPI 应用 ──────────────────────────────────────────────────────────────

_STATIC_DIR = Path(__file__).parent / "demo_static"

app = FastAPI(title="智慧园区内圈引擎 Demo")

# ── 访问口令(外网/内网分享时启用) ─────────────────────────────────────────────
# 设了 DEMO_ACCESS_USER + DEMO_ACCESS_PASS 就对全部路由(含 / 与 /static)强制
# HTTP Basic Auth;不设则保持开放(本机演示)。口令用你自己的,别用 .env 里的内部
# service token。分享时把 user/pass 一并给对方。
_ACCESS_USER = os.getenv("DEMO_ACCESS_USER")
_ACCESS_PASS = os.getenv("DEMO_ACCESS_PASS")

if _ACCESS_USER and _ACCESS_PASS:
    import base64
    import secrets

    def _basic_ok(header):
        if not header or not header.lower().startswith("basic "):
            return False
        try:
            raw = base64.b64decode(header[6:].strip()).decode("utf-8")
        except Exception:
            return False
        user, sep, pw = raw.partition(":")
        if not sep:
            return False
        return secrets.compare_digest(user, _ACCESS_USER) and secrets.compare_digest(pw, _ACCESS_PASS)

    @app.middleware("http")
    async def _access_gate(request, call_next):
        if _basic_ok(request.headers.get("authorization")):
            return await call_next(request)
        return PlainTextResponse(
            "401 unauthorized\n",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="smart-park-demo"'},
        )

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=(_STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.post("/api/chat")
async def api_chat(body: dict):
    msg = body.get("message", "").strip()
    if not msg:
        return JSONResponse({"error": "empty message"}, status_code=400)

    async with _lock:
        # 把入站 user 消息落库
        last = await _store.latest_boundary(_thread_id)
        seq = last.seq if last else 0
        await _store.commit(
            _thread_id,
            [Message(role="user", content=msg)],
            Boundary(status="user", turn_id=f"u{seq + 1}", seq=seq + 1),
        )
        conv = await _store.load(_thread_id)
        principal = _principal()             # 当前 persona(权限治理可见化)
        conv.principal = principal           # 身份脊柱:中圈记忆层/知识层透传共用
        before = len(conv.messages)
        reg = build_registry(conv.plan)
        cfg = _make_cfg(principal)           # ToolLoader:按当前身份权限过滤顶层

        run_kwargs = dict(
            cfg=cfg,
            reg=reg,
            budget_tracker=BudgetTracker(cfg.budget),
            model=_model,
            store=_store,
            control=_control,
            gate=_rt.subsystem.gate,         # 治理闸:权限 deny + 控制 ask(零引擎改,run_loop 已支持)
            assembler=_assembler,            # 中圈真组装器替桩
            compaction=_compactor,           # 压缩 v2:超硬阈摘中段
        )

        async def generate():
            async for chunk in _stream_run(conv=conv, before=before, run_kwargs=run_kwargs):
                yield chunk

        return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/api/confirm")
async def api_confirm(body: dict):
    cancel: bool = body.get("cancel", False)
    decisions: dict[str, str] = body.get("decisions", {})

    async with _lock:
        conv = await _store.load(_thread_id)
        principal = _principal()
        conv.principal = principal
        before = len(conv.messages)
        reg = build_registry(conv.plan)
        cfg = _make_cfg(principal)

        run_kwargs = dict(
            cfg=cfg,
            reg=reg,
            budget_tracker=BudgetTracker(cfg.budget),
            model=_model,
            store=_store,
            control=_control,
            gate=_rt.subsystem.gate,
            assembler=_assembler,
            compaction=_compactor,
        )
        if cancel:
            run_kwargs["cancel"] = True
        else:
            run_kwargs["resolution"] = decisions

        async def generate():
            async for chunk in _stream_run(conv=conv, before=before, run_kwargs=run_kwargs):
                yield chunk

        return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/api/reset")
async def api_reset():
    global _store, _control, _rt
    async with _lock:
        _store = InMemoryConversationStore()
        _rt = _build_runtime()                 # 重建 → 清提案 store + 幂等账本
        _control = _rt.subsystem.control
    return JSONResponse({"ok": True})


@app.get("/api/state")
async def api_state():
    """当前身份 + 可见工具(页面加载 / reset 后拉取)。"""
    return JSONResponse(_identity_view(_current_persona))


@app.post("/api/identity")
async def api_identity(body: dict):
    """切换 demo 身份 → 返回新身份的可见工具集(rt.toolset_for 实算,演示 deny-first 收缩)。"""
    global _current_persona
    pid = body.get("persona", "")
    if pid not in _PERSONAS:
        return JSONResponse({"error": "unknown persona"}, status_code=400)
    async with _lock:
        _current_persona = pid
    return JSONResponse(_identity_view(pid))


@app.post("/api/token")
async def api_token(body: dict):
    """页面设置数据令牌(透传后端做数据级查询)。仅存内存、不落盘、不进日志、只回显掩码。
    空 → 回落启动 env 默认。能力级治理不受影响(由 persona 权限码决定)。"""
    global _runtime_token
    tok = (body.get("token") or "").strip()
    async with _lock:
        _runtime_token = tok or _DEMO_TOKEN
    hint = _token_hint(_runtime_token)
    return JSONResponse({"token_hint": hint, "token_set": bool(hint)})


def _gc_abandoned_proposals(res) -> int:
    """每轮 run_loop 结束后清理"放弃的提案"。

    终态(completed/budget_exhausted/error)却仍有未消解提案 = 本轮模型 propose 了但没 execute
    →放弃。必须清掉:否则下一轮 `execute_proposal` 的"取最近一条"会误取这条陈旧提案(撤 auto-chain +
    execute-latest 后引入的跨轮陷阱)。`awaiting_confirmation` 时**不清**——那条提案正等用户确认,
    生命周期归 resolve/confirm。返回清理条数。"""
    if res.status == "awaiting_confirmation":
        return 0
    dangling = list(_rt.subsystem.store.items())
    for handle, _p in dangling:
        _rt.subsystem.store.pop(handle)
    return len(dangling)


def _make_response(res, before: int) -> dict:
    """保留供内部测试用(api 端点已改为流式)。"""
    completed_statuses = {"completed", "budget_exhausted"}
    answer: str = ""
    if res.status in completed_statuses and res.final and res.final.strip():
        candidate = res.final.strip()
        if candidate != "(等待确认)":
            answer = _strip_step_prefixes(candidate)

    process = extract_process(res.conversation.messages, before, answer)

    pending_list = []
    for p in (res.pending or []):
        pending_list.append({
            "tool_call_id": p.tool_call_id,
            "name": p.frozen_action["name"],
            "args": p.frozen_action["arguments"],
        })
    plan_text = res.conversation.plan.render() if res.conversation.plan.items else ""
    return {
        "status": res.status,
        "reason": res.reason,
        "answer": answer,
        "process": process,
        "pending": pending_list,
        "plan": plan_text,
    }




# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("DEMO_HOST", "0.0.0.0"), port=int(os.getenv("DEMO_PORT", "8030")))
