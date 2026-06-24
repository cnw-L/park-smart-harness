"""智慧园区 · 三环 harness Web Demo(治理工具子系统串联演示)

真 qwen@6008 驱动 agent_loop 内圈 + agent_tools 治理子系统(`build_park_runtime` 一处串联)。
四条演示主线:① 子 agent ReAct 委派(设备管理 facility_agent) ② 控制确认红线(propose→execute→人工确认→deviceCtrl+读回)
③ 权限治理(deny-first ToolLoader:换身份→可见工具集随权限收缩) ④ 知识检索(harness_rag/Fake,带引用、证据不足不臆造)。

运行:
  python scripts/demo_server.py
  → 浏览器打开 http://127.0.0.1:8030

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
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget, LoopConfig
from agent_loop.conversation import Boundary, InMemoryConversationStore
from agent_loop.loop import run_loop
from agent_loop.messages import Message
from agent_loop.plan import make_plan_tool
from agent_loop.providers import OpenAIModelCaller
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
    """把模型最终消息清成对外干净结论:逐行去"第N步"标号、丢过程话/纯标签行、去引导前缀。
    清空则回退原文(宁可多说也不给空气泡)。"""
    raw = text.strip()
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
    return cleaned if cleaned else raw


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

app = FastAPI(title="智慧园区内圈引擎 Demo")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=_HTML)


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


# ── 内联 HTML ─────────────────────────────────────────────────────────────────

_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>智慧园区 · 内圈引擎 Demo</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #22263a;
    --border: #2e3347;
    --accent: #4f7cf6;
    --accent2: #38bdf8;
    --text: #e2e8f0;
    --muted: #8892a4;
    --error: #f87171;
    --warn: #fbbf24;
    --green: #34d399;
    --red: #f87171;
    --amber: #fbbf24;
    --radius: 10px;
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 14px;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  /* Header */
  .header {
    padding: 12px 20px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .header h1 { font-size: 16px; font-weight: 700; color: var(--accent2); }
  .header p { font-size: 12px; color: var(--muted); }
  .header .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); flex-shrink: 0; }
  /* Layout */
  .main {
    flex: 1;
    display: flex;
    overflow: hidden;
  }
  /* Chat area */
  .chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  /* Bubbles */
  .bubble {
    max-width: 70%;
    padding: 10px 14px;
    border-radius: var(--radius);
    line-height: 1.5;
    word-break: break-word;
    white-space: pre-wrap;
  }
  .bubble.user {
    align-self: flex-end;
    background: var(--accent);
    color: #fff;
  }
  .bubble.assistant {
    align-self: flex-start;
    background: var(--surface2);
    border: 1px solid var(--accent);
  }
  /* done_what 进展行 — 对外显式 */
  .done-what-row {
    align-self: flex-start;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 13px;
    color: var(--text);
    padding: 7px 12px;
    background: var(--surface2);
    border: 1px solid #2a3d2a;
    border-radius: 8px;
    max-width: 80%;
    line-height: 1.45;
  }
  .done-what-row.error {
    border-color: #4a2020;
    color: var(--error);
  }
  /* 过程 (process) collapsible — 对内隐式 */
  .process-details {
    align-self: flex-start;
    max-width: 80%;
  }
  .process-details summary {
    font-size: 12px;
    color: var(--muted);
    cursor: pointer;
    user-select: none;
    list-style: none;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 0;
  }
  .process-details summary::-webkit-details-marker { display: none; }
  .process-details summary::before {
    content: '▸';
    font-size: 10px;
    transition: transform 0.15s;
  }
  .process-details[open] summary::before { content: '▾'; }
  .process-details summary:hover { color: var(--text); }
  .process-inner {
    margin-top: 6px;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  /* Process item styles */
  .trace-think {
    font-style: italic;
    color: var(--muted);
    font-size: 12px;
    padding: 6px 10px;
    border-left: 2px solid var(--border);
  }
  .trace-say {
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 8px 12px;
    border-radius: 6px;
    line-height: 1.5;
    font-size: 12px;
    white-space: pre-wrap;
  }
  .trace-tool-call {
    background: #1e2a3a;
    border: 1px solid #2d4060;
    padding: 6px 10px;
    border-radius: 6px;
    font-family: monospace;
    font-size: 12px;
    color: var(--accent2);
  }
  .trace-tool-result {
    background: #1a2518;
    border: 1px solid #2a3a20;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
    color: #86efac;
    font-family: monospace;
  }
  .trace-tool-result.error {
    background: #2a1818;
    border-color: #4a2020;
    color: var(--error);
  }
  .trace-blocked {
    background: #2a1818;
    border: 1px solid #5a2020;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
    color: var(--error);
  }
  /* Confirm card */
  .confirm-card {
    background: var(--surface);
    border: 2px solid var(--warn);
    border-radius: var(--radius);
    padding: 14px;
    max-width: 420px;
    align-self: flex-start;
  }
  .confirm-card h3 {
    font-size: 13px;
    color: var(--warn);
    margin-bottom: 8px;
  }
  .confirm-action {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 10px;
    font-family: monospace;
    font-size: 12px;
    margin-bottom: 12px;
    color: var(--text);
  }
  .confirm-btns { display: flex; gap: 8px; }
  .btn-approve {
    padding: 7px 18px;
    background: var(--green);
    color: #000;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 13px;
  }
  .btn-approve:hover { opacity: 0.85; }
  .btn-reject {
    padding: 7px 18px;
    background: var(--red);
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 13px;
  }
  .btn-reject:hover { opacity: 0.85; }
  /* Status badge */
  .status-badge {
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 99px;
    font-weight: 600;
    align-self: flex-start;
  }
  .status-badge.completed { background: #134e2a; color: var(--green); }
  .status-badge.awaiting { background: #3a2a00; color: var(--warn); }
  .status-badge.failed { background: #3a1010; color: var(--error); }
  .status-badge.budget { background: #2a2040; color: #a78bfa; }
  /* Sidebar */
  .sidebar {
    width: 240px;
    background: var(--surface);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .sidebar-title {
    padding: 10px 14px;
    font-size: 11px;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border);
  }
  /* Plan items with status badges — D5 */
  .plan-items {
    flex: 1;
    padding: 10px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .plan-empty {
    padding: 12px;
    font-size: 12px;
    color: var(--muted);
    text-align: center;
  }
  .plan-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 10px;
    border-radius: 6px;
    background: var(--surface2);
    border: 1px solid var(--border);
    font-size: 12px;
    line-height: 1.5;
    transition: border-color 0.2s;
  }
  .plan-item.status-todo { border-color: var(--border); }
  .plan-item.status-doing { border-color: var(--amber); background: #1e1a0a; }
  .plan-item.status-done { border-color: #1a3a20; background: #0d1e11; }
  .plan-item-icon {
    font-size: 14px;
    flex-shrink: 0;
    margin-top: 1px;
  }
  .plan-item-icon.todo { color: var(--muted); }
  .plan-item-icon.doing { color: var(--amber); }
  .plan-item-icon.done { color: var(--green); }
  .plan-item-text { flex: 1; color: var(--text); }
  .plan-item-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.3px;
    margin-top: 3px;
  }
  .plan-item-label.todo { color: var(--muted); }
  .plan-item-label.doing { color: var(--amber); }
  .plan-item-label.done { color: var(--green); }
  /* Example chips */
  .examples {
    padding: 8px 16px;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    border-top: 1px solid var(--border);
  }
  .chip {
    padding: 5px 10px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 99px;
    cursor: pointer;
    font-size: 12px;
    color: var(--muted);
    transition: all 0.15s;
  }
  .chip:hover { border-color: var(--accent); color: var(--text); }
  /* Input bar */
  .input-bar {
    padding: 12px 16px;
    background: var(--surface);
    border-top: 1px solid var(--border);
    display: flex;
    gap: 8px;
    align-items: flex-end;
  }
  .input-bar textarea {
    flex: 1;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    padding: 9px 12px;
    font-size: 14px;
    font-family: inherit;
    resize: none;
    outline: none;
    min-height: 38px;
    max-height: 120px;
    line-height: 1.4;
  }
  .input-bar textarea:focus { border-color: var(--accent); }
  .input-bar textarea:disabled { opacity: 0.5; }
  .btn-send {
    padding: 9px 18px;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    height: 38px;
    white-space: nowrap;
  }
  .btn-send:hover { opacity: 0.85; }
  .btn-send:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-reset {
    padding: 9px 14px;
    background: transparent;
    color: var(--muted);
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    height: 38px;
  }
  .btn-reset:hover { border-color: var(--error); color: var(--error); }
  /* Loading indicator */
  .loading-row {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--muted);
    font-size: 13px;
  }
  .spinner {
    width: 16px; height: 16px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  /* Empty state */
  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    gap: 8px;
  }
  .empty-state h2 { font-size: 20px; color: var(--text); }
  .empty-state p { font-size: 13px; text-align: center; max-width: 280px; line-height: 1.6; }
  .scrollable { scroll-behavior: smooth; }
  /* 流式运行中 indicator */
  .running-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--accent2);
    padding: 4px 0;
  }
  .run-timer {
    font-family: ui-monospace, monospace;
    font-variant-numeric: tabular-nums;
    color: var(--muted);
    background: var(--surface2);
    border-radius: 6px;
    padding: 1px 7px;
    font-size: 11px;
  }
  .trace-t {
    float: right;
    margin-left: 8px;
    font-family: ui-monospace, monospace;
    font-variant-numeric: tabular-nums;
    font-size: 10px;
    color: var(--muted);
    opacity: 0.75;
  }
  .run-total {
    font-size: 11px;
    color: var(--muted);
    font-family: ui-monospace, monospace;
    font-variant-numeric: tabular-nums;
    padding: 2px 0 6px;
  }
  /* 身份切换(header 右) */
  .identity-switch { display: flex; gap: 6px; align-items: center; }
  .identity-switch .persona-btn {
    padding: 5px 11px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 99px;
    cursor: pointer;
    font-size: 12px;
    color: var(--muted);
    transition: all 0.15s;
    white-space: nowrap;
  }
  .identity-switch .persona-btn:hover { border-color: var(--accent); color: var(--text); }
  .identity-switch .persona-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
    font-weight: 600;
  }
  .identity-switch .persona-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  /* 可见工具面板(sidebar 下) */
  .tools-panel { padding: 10px; display: flex; flex-direction: column; gap: 5px; overflow-y: auto; max-height: 38%; }
  .tools-panel .tool-row {
    display: flex; align-items: center; gap: 7px;
    padding: 6px 9px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 12px;
    color: var(--text);
  }
  .tools-panel .tool-row.control { border-color: #4a3a10; }
  .tools-panel .tool-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); flex-shrink: 0; }
  .tools-panel .tool-row.control .tool-dot { background: var(--amber); }
  .tools-panel .perms { font-size: 11px; color: var(--muted); padding: 2px 2px 4px; line-height: 1.5; word-break: break-word; }
  /* 数据令牌输入框 */
  .token-box { padding: 10px; display: flex; flex-direction: column; gap: 6px; }
  .token-box input {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    padding: 7px 9px;
    font-size: 12px;
    font-family: monospace;
    outline: none;
    width: 100%;
  }
  .token-box input:focus { border-color: var(--accent); }
  .token-box button {
    padding: 6px 10px;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
  }
  .token-box button:hover { opacity: 0.85; }
  .token-status { font-size: 11px; color: var(--muted); }
  .token-status.set { color: var(--green); }
</style>
</head>
<body>
<div class="header">
  <div class="dot"></div>
  <div style="flex:1;">
    <h1>智慧园区 · 治理工具子系统 Demo</h1>
    <p>真 qwen@6008 · 设备管理 / 运行查询 / 生活服务 / 知识检索 / 执行工具(控制·需确认) · deny-first 按身份过滤</p>
  </div>
  <div class="identity-switch" id="identitySwitch"></div>
</div>

<div class="main">
  <div class="chat-area">
    <div class="messages scrollable" id="messages">
      <div class="empty-state" id="emptyState">
        <h2>欢迎</h2>
        <p>选个示例或直接发消息。设备控制(执行工具)会触发人工确认红线;右上角可切换身份,看可见工具随权限收缩。</p>
      </div>
    </div>

    <div class="examples">
      <span class="chip" onclick="sendChip('查一下空调机组的运行状态和健康度')">设备管理·查空调状态+健康度</span>
      <span class="chip" onclick="sendChip('今天的工单和告警帮我理一下')">运行查询·工单+告警</span>
      <span class="chip" onclick="sendChip('园区消防应急预案是怎么规定的?')">知识检索·消防应急预案</span>
      <span class="chip" onclick="sendChip('附近有什么餐厅?')">生活服务·餐厅</span>
      <span class="chip" onclick="sendChip('把空调机组的温度调到24度')">执行工具·调温(需确认)</span>
      <span class="chip" onclick="sendChip('制定并执行三步计划:先查3号楼空调温度,偏高就提案调到24度(需确认),最后汇总;请先用 plan 工具列出这三步再逐步执行')">三步计划(查→提案→汇总)</span>
    </div>

    <div class="input-bar">
      <textarea id="input" placeholder="输入消息,Enter 发送,Shift+Enter 换行..." rows="1"></textarea>
      <button class="btn-send" id="sendBtn" onclick="sendMessage()">发送</button>
      <button class="btn-reset" onclick="resetSession()">重置</button>
    </div>
  </div>

  <div class="sidebar">
    <div class="sidebar-title">当前计划</div>
    <div class="plan-items" id="planItems">
      <div class="plan-empty" id="planEmpty">暂无</div>
    </div>
    <div class="sidebar-title" style="border-top:1px solid var(--border);">当前身份 · 可见工具</div>
    <div class="tools-panel" id="toolsPanel">
      <div class="plan-empty">加载中…</div>
    </div>
    <div class="sidebar-title" style="border-top:1px solid var(--border);">数据令牌(传后端)</div>
    <div class="token-box">
      <input id="tokenInput" type="password" placeholder="粘贴 Bearer token…" autocomplete="off" />
      <button id="tokenBtn" onclick="applyToken()">应用</button>
      <div class="token-status" id="tokenStatus">未设置 · 用默认</div>
    </div>
  </div>
</div>

<script>
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const planItemsEl = document.getElementById('planItems');
const emptyState = document.getElementById('emptyState');
const identitySwitchEl = document.getElementById('identitySwitch');
const toolsPanelEl = document.getElementById('toolsPanel');
const tokenInputEl = document.getElementById('tokenInput');
const tokenStatusEl = document.getElementById('tokenStatus');

let loading = false;
let currentPersona = null;
let controlMode = 'simulated';                 // 控制执行模式(/api/state 注入);默认不真下发
let runTimerHandle = null;                     // 运行计时器 interval 句柄
let lastEventMs = 0;                           // 上一个事件的 t_ms(算步间隔)

function fmtMs(ms) {                            // 毫秒 → 人话(320ms / 2.3s)
  if (ms == null || isNaN(ms)) return '';
  return ms < 1000 ? ms + 'ms' : (ms / 1000).toFixed(1) + 's';
}

// ── 身份治理面板:persona 切换 + 可见工具(rt.toolset_for 实算) ─────────────────
const CONTROL_TOOLS = new Set(['execute_proposal']);

function renderIdentity(view) {
  currentPersona = view.persona;
  if (view.control_mode) controlMode = view.control_mode;   // simulated(默认)/ real → 确认卡措辞
  // header 身份按钮
  identitySwitchEl.innerHTML = '';
  for (const p of (view.personas || [])) {
    const btn = document.createElement('button');
    btn.className = 'persona-btn' + (p.id === view.persona ? ' active' : '');
    btn.textContent = p.name;
    btn.title = p.role;
    btn.disabled = loading;
    btn.onclick = () => switchPersona(p.id);
    identitySwitchEl.appendChild(btn);
  }
  // sidebar 可见工具 + 权限码
  toolsPanelEl.innerHTML = '';
  const perms = document.createElement('div');
  perms.className = 'perms';
  perms.textContent = '权限码: ' + ((view.permissions || []).join(' · ') || '(无)');
  toolsPanelEl.appendChild(perms);
  if (!view.tools || view.tools.length === 0) {
    const e = document.createElement('div');
    e.className = 'plan-empty';
    e.textContent = '无可见工具';
    toolsPanelEl.appendChild(e);
  }
  for (const t of (view.tools || [])) {
    const row = document.createElement('div');
    const isControl = CONTROL_TOOLS.has(t.name);
    row.className = 'tool-row' + (isControl ? ' control' : '');
    const dot = document.createElement('span');
    dot.className = 'tool-dot';
    const txt = document.createElement('span');
    txt.textContent = t.label;
    row.appendChild(dot);
    row.appendChild(txt);
    toolsPanelEl.appendChild(row);
  }
  if ('token_hint' in view) renderTokenStatus(view.token_hint);
}

function renderTokenStatus(hint) {
  if (hint) {
    tokenStatusEl.textContent = '已设置 · ' + hint;
    tokenStatusEl.className = 'token-status set';
  } else {
    tokenStatusEl.textContent = '未设置 · 用默认';
    tokenStatusEl.className = 'token-status';
  }
}

async function applyToken() {
  const tok = tokenInputEl.value.trim();
  try {
    const resp = await fetch('/api/token', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token: tok}),
    });
    if (resp.ok) {
      const v = await resp.json();
      renderTokenStatus(v.token_hint);
      tokenInputEl.value = '';   // 不在 DOM 里留存令牌
    }
  } catch (e) { /* demo:静默 */ }
}

async function loadState() {
  try {
    const resp = await fetch('/api/state');
    if (resp.ok) renderIdentity(await resp.json());
  } catch (e) { /* demo:静默 */ }
}

async function switchPersona(pid) {
  if (loading || pid === currentPersona) return;
  try {
    const resp = await fetch('/api/identity', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({persona: pid}),
    });
    if (resp.ok) renderIdentity(await resp.json());
  } catch (e) { /* demo:静默 */ }
}

// Auto-resize textarea
inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!loading) sendMessage();
  }
});

function setLoading(val) {
  loading = val;
  sendBtn.disabled = val;
  inputEl.disabled = val;
  // 运行中禁用身份切换(避免半途换身份导致 toolset/权限错位)
  identitySwitchEl.querySelectorAll('.persona-btn').forEach(b => { b.disabled = val; });
}

function hideEmpty() {
  if (emptyState) emptyState.style.display = 'none';
}

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function sendChip(text) {
  if (loading) return;
  inputEl.value = text;
  sendMessage();
}

// ── plan 侧边栏渲染(结构化 items with live status badges) ────────────────────
const STATUS_ICON = { todo: '○', doing: '◐', done: '●' };
const STATUS_LABEL = { todo: '待办', doing: '进行中', done: '已完成' };

function renderPlanItems(items) {
  // 清空旧内容
  planItemsEl.innerHTML = '';
  if (!items || items.length === 0) {
    const emp = document.createElement('div');
    emp.className = 'plan-empty';
    emp.textContent = '暂无';
    planItemsEl.appendChild(emp);
    return;
  }
  for (const item of items) {
    const st = item.status || 'todo'; // todo|doing|done
    const div = document.createElement('div');
    div.className = 'plan-item status-' + st;
    div.dataset.id = item.id;

    const icon = document.createElement('span');
    icon.className = 'plan-item-icon ' + st;
    icon.textContent = STATUS_ICON[st] || '○';

    const body = document.createElement('div');
    body.className = 'plan-item-text';
    const txt = document.createElement('div');
    txt.textContent = item.content;
    const lbl = document.createElement('div');
    lbl.className = 'plan-item-label ' + st;
    lbl.textContent = STATUS_LABEL[st] || st;
    body.appendChild(txt);
    body.appendChild(lbl);

    div.appendChild(icon);
    div.appendChild(body);
    planItemsEl.appendChild(div);
  }
}

// ── done_what 进展行渲染(外部可见) ──────────────────────────────────────────
function appendDoneWhat(text) {
  const isError = text.startsWith('✗');
  const row = document.createElement('div');
  row.className = 'done-what-row' + (isError ? ' error' : '');
  row.textContent = text;
  messagesEl.appendChild(row);
  scrollBottom();
}

// ── 流式 fetch 核心 ───────────────────────────────────────────────────────────
function createTurnProcessBlock() {
  const details = document.createElement('details');
  details.className = 'process-details';
  const summary = document.createElement('summary');
  summary.textContent = '过程 (0 步)';
  details.appendChild(summary);
  const inner = document.createElement('div');
  inner.className = 'process-inner';
  details.appendChild(inner);
  messagesEl.appendChild(details);
  return { details, summary, inner, count: 0 };
}

async function streamRequest(url, bodyObj, block) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(bodyObj),
  });
  if (!resp.ok) {
    throw new Error('HTTP ' + resp.status);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buf = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\\n');
    buf = lines.pop();
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      let ev;
      try { ev = JSON.parse(trimmed); } catch { continue; }
      handleStreamEvent(ev, block);
    }
  }
  if (buf.trim()) {
    try {
      const ev = JSON.parse(buf.trim());
      handleStreamEvent(ev, block);
    } catch {}
  }
}

function handleStreamEvent(ev, block) {
  switch (ev.event) {
    case 'process': {
      // 对内隐式:追加到过程折叠器
      const el = buildProcessItem(ev);
      if (el) {
        block.inner.appendChild(el);
        block.count++;
        block.summary.textContent = '过程 (' + block.count + ' 步)';
      }
      scrollBottom();
      break;
    }
    case 'done_what': {
      // 对外显式:在对话区显示进展行(NOT 在过程折叠器内)
      if (ev.text && ev.text.trim()) {
        appendDoneWhat(ev.text.trim());
      }
      break;
    }
    case 'plan': {
      // 对外显式:渲染结构化 plan 侧边栏(带状态徽章)
      if (ev.items && ev.items.length > 0) {
        renderPlanItems(ev.items);
      } else if (ev.text) {
        // 回退:纯文本渲染
        planItemsEl.innerHTML = '<div style="padding:8px;font-size:12px;color:var(--muted);white-space:pre-wrap;font-family:monospace;">' + escHtml(ev.text) + '</div>';
      }
      break;
    }
    case 'pending': {
      for (const p of (ev.items || [])) {
        const card = buildConfirmCard(p);
        messagesEl.appendChild(card);
      }
      scrollBottom();
      break;
    }
    case 'answer': {
      if (ev.text && ev.text.trim()) {
        typewriterBubble(ev.text.trim());     // 逐字显现(流式感)
      }
      break;
    }
    case 'done': {
      stopRunTimer();
      const ind = document.getElementById('runningIndicator');
      if (ind) ind.remove();
      if (ev.t_ms != null) {                  // 本次总耗时(对外显式)
        const tt = document.createElement('div');
        tt.className = 'run-total';
        tt.textContent = '⏱ 本次耗时 ' + fmtMs(ev.t_ms);
        messagesEl.appendChild(tt);
      }
      if (ev.status && ev.status !== 'completed') {
        const badge = document.createElement('span');
        badge.className = 'status-badge ' + statusClass(ev.status);
        badge.textContent = statusLabel(ev.status, ev.reason);
        messagesEl.appendChild(badge);
      }
      scrollBottom();
      break;
    }
  }
}

async function sendMessage() {
  const msg = inputEl.value.trim();
  if (!msg || loading) return;
  inputEl.value = '';
  inputEl.style.height = 'auto';
  hideEmpty();
  appendUserBubble(msg);
  setLoading(true);

  const indicator = appendRunningIndicator();
  const block = createTurnProcessBlock();

  try {
    await streamRequest('/api/chat', {message: msg}, block);
  } catch(err) {
    appendError('请求失败:' + err.message);
  } finally {
    stopRunTimer();
    indicator.remove();
    setLoading(false);
    scrollBottom();
  }
}

async function resetSession() {
  if (loading) return;
  await fetch('/api/reset', {method: 'POST'});
  messagesEl.innerHTML = '';
  messagesEl.appendChild(buildEmptyState());
  renderPlanItems([]);
  loadState();   // reset 重建运行时(清提案/账本),刷新身份面板
}

function buildEmptyState() {
  const d = document.createElement('div');
  d.className = 'empty-state';
  d.id = 'emptyState';
  d.innerHTML = '<h2>欢迎</h2><p>选个示例或直接发消息。设备控制(执行工具)会触发人工确认红线;右上角可切换身份,看可见工具随权限收缩。</p>';
  return d;
}

function appendUserBubble(text) {
  const d = document.createElement('div');
  d.className = 'bubble user';
  d.textContent = text;
  messagesEl.appendChild(d);
  scrollBottom();
}

function appendRunningIndicator() {
  const d = document.createElement('div');
  d.className = 'running-indicator';
  d.id = 'runningIndicator';
  d.innerHTML = '<div class="spinner"></div><span>运行中</span><span class="run-timer" id="runTimer">0.0s</span>';
  messagesEl.appendChild(d);
  // 实时秒表:每 100ms 刷新累计耗时(qwen 单步可达数十秒,让用户看见在跑、跑了多久)
  const start = performance.now();
  lastEventMs = 0;
  if (runTimerHandle) clearInterval(runTimerHandle);
  runTimerHandle = setInterval(() => {
    const t = document.getElementById('runTimer');
    if (t) t.textContent = ((performance.now() - start) / 1000).toFixed(1) + 's';
  }, 100);
  scrollBottom();
  return d;
}

function stopRunTimer() {
  if (runTimerHandle) { clearInterval(runTimerHandle); runTimerHandle = null; }
}

function typewriterBubble(text) {
  // 最终答案逐字显现:模型调用本身不流式(qwen 整段返回),前端做打字机效果给"流式输出"观感。
  const bubble = document.createElement('div');
  bubble.className = 'bubble assistant';
  messagesEl.appendChild(bubble);
  const step = Math.max(1, Math.round(text.length / 100));   // ~100 帧内显现完
  let i = 0;
  const iv = setInterval(() => {
    i += step;
    bubble.textContent = text.slice(0, i);
    scrollBottom();
    if (i >= text.length) { clearInterval(iv); bubble.textContent = text; }
  }, 16);
}

function appendError(msg) {
  const d = document.createElement('div');
  d.className = 'trace-blocked';
  d.textContent = '⛔ ' + msg;
  messagesEl.appendChild(d);
}

function buildProcessItem(item) {
  const el = document.createElement('div');
  if (item.kind === 'think') {
    el.className = 'trace-think';
    el.textContent = '思考: ' + item.text;
  } else if (item.kind === 'say') {
    el.className = 'trace-say';
    el.textContent = item.text;
  } else if (item.kind === 'tool_call') {
    el.className = 'trace-tool-call';
    const argsStr = typeof item.args === 'object' ? JSON.stringify(item.args, null, 0) : String(item.args || '');
    el.textContent = '调用 ' + item.name + '(' + argsStr + ')';
  } else if (item.kind === 'tool_result') {
    el.className = 'trace-tool-result' + (item.is_error ? ' error' : '');
    const prefix = item.is_error ? '警告' : '返回';
    el.textContent = prefix + ' ' + item.name + ': ' + item.text;
  } else if (item.kind === 'blocked') {
    el.className = 'trace-blocked';
    el.textContent = '拦截 ' + item.text;
  } else {
    return null;
  }
  // 步耗时徽章(右侧):本步累计耗时 @X.Xs + 距上一步的增量(+Y.Ys),让慢在哪一步一目了然
  if (item.t_ms != null) {
    const delta = item.t_ms - lastEventMs;
    lastEventMs = item.t_ms;
    const t = document.createElement('span');
    t.className = 'trace-t';
    t.textContent = '@' + fmtMs(item.t_ms) + (delta > 50 ? ' +' + fmtMs(delta) : '');
    el.appendChild(t);
  }
  return el;
}

function buildConfirmCard(pending) {
  const card = document.createElement('div');
  card.className = 'confirm-card';
  // 无效/过期提案(模型编造 handle 或未先登记提案)→ 治理拦截:展示警示、不给"批准"
  if (pending.name === '__invalid_proposal__') {
    card.style.borderColor = 'var(--error)';
    card.innerHTML = `
      <h3 style="color:var(--error)">⛔ 提案无效 · 已被治理拦截</h3>
      <div class="confirm-action">模型给出的提案编号无效或已过期(未走「先登记提案、再执行」的流程)。系统**未下发任何控制**。</div>
      <div class="confirm-btns"><button class="btn-reject" onclick="cancelAction(this)">知道了</button></div>
    `;
    return card;
  }
  // 真实控制提案:把 grounded 参数渲染成人话 + 折叠原始 payload
  const a = pending.args || {};
  const human = (a.paramTypeName || a.paramTypeNo)
    ? `${a.paramTypeName || a.paramTypeNo} → ${a.paramValue || a.paramStatus || ''}` : '';
  const target = a.deviceId ? `设备 ${a.deviceId}` : '';
  const argsStr = typeof pending.args === 'object' ? JSON.stringify(pending.args, null, 2) : String(pending.args);
  const sim = controlMode !== 'real';
  const h3 = sim
    ? '🧪 控制操作 · 需要确认(模拟模式 · 确认后<b>不真实下发</b>)'
    : '⚠️ 控制操作 · 需要确认(不可逆,确认后<b>真实下发</b>)';
  card.innerHTML = `
    <h3>${h3}</h3>
    <div class="confirm-action"><b>${escHtml(pending.name)}</b>${human ? ' · ' + escHtml(human) : ''}${target ? '<br>' + escHtml(target) : ''}
      <br><span style="color:var(--muted);font-size:11px;">${escHtml(argsStr)}</span></div>
    <div class="confirm-btns">
      <button class="btn-approve" onclick="approveAction('${escAttr(pending.tool_call_id)}', this)">${sim ? '批准(模拟)' : '批准下发'}</button>
      <button class="btn-reject" onclick="cancelAction(this)">拒绝并取消</button>
    </div>
  `;
  return card;
}

async function approveAction(toolCallId, btn) {
  if (loading) return;
  const card = btn.closest('.confirm-card');
  card.querySelector('.confirm-btns').innerHTML = '<span style="color:var(--muted);font-size:13px;">处理中…</span>';
  setLoading(true);
  const indicator = appendRunningIndicator();
  const block = createTurnProcessBlock();
  try {
    await streamRequest('/api/confirm', {decisions: {[toolCallId]: 'approve'}}, block);
    card.remove();
  } catch(err) {
    appendError('确认请求失败:' + err.message);
    card.remove();
  } finally {
    indicator.remove();
    setLoading(false);
    scrollBottom();
  }
}

async function cancelAction(btn) {
  if (loading) return;
  const card = btn.closest('.confirm-card');
  card.querySelector('.confirm-btns').innerHTML = '<span style="color:var(--muted);font-size:13px;">处理中…</span>';
  setLoading(true);
  const indicator = appendRunningIndicator();
  const block = createTurnProcessBlock();
  try {
    await streamRequest('/api/confirm', {cancel: true}, block);
    card.remove();
  } catch(err) {
    appendError('取消请求失败:' + err.message);
    card.remove();
  } finally {
    indicator.remove();
    setLoading(false);
    scrollBottom();
  }
}

function statusClass(status) {
  if (status === 'completed') return 'completed';
  if (status === 'awaiting_confirmation') return 'awaiting';
  if (status === 'budget_exhausted') return 'budget';
  return 'failed';
}

// 失败/停止原因 → 人话(对齐引擎 reason:看门狗如实停,不伪装完成)
const REASON_LABEL = {
  no_progress: '连续多轮无有效进展,已停止',
  stall: '检测到原地踏步,已停止',
  tool_failures: '工具连续失败,已停止',
  model_error: '模型调用失败',
  empty_response: '模型空响应',
  persist_error: '持久化失败',
  interrupted: '已中断',
};

function statusLabel(status, reason) {
  if (status === 'budget_exhausted') return '步数用尽(已尽力收尾)';
  if (status === 'failed') return REASON_LABEL[reason] || ('失败' + (reason ? ':' + reason : ''));
  const map = {
    completed: '完成',
    awaiting_confirmation: '等待确认',
    interrupted: '已中断',
  };
  return map[status] || status;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escAttr(s) {
  return String(s).replace(/'/g, "\\'");
}

// 页面加载:拉取当前身份 + 可见工具(渲染身份面板)
loadState();
</script>
</body>
</html>
"""


# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("DEMO_PORT", "8030")))
