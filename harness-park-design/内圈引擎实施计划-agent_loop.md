# 内圈引擎 agent_loop 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development(推荐)或 superpowers:executing-plans 逐任务实现。步骤用 `- [ ]` 复选框跟踪。
> 上游 spec:`内圈引擎设计-agent_loop.md`。基于讨论 + Claude Code/Hermes 案例。

**Goal:** 建一个手写 async while 递归 ReAct 引擎(`agent_loop`),主/子同一个 `run_loop`,native tool-calling 驱动,带预算/grace/隔离子 agent,用桩工具验证。

**Architecture:** 纯引擎 + 桩件,完全解耦(不依赖 `capability_platform`/后端)。LLM 经可注入的 `ModelCaller` 协议接入,测试用 `FakeModelCaller` 脚本化驱动循环,确定性可测。状态=消息即状态(append-only),本轮 InMemory 持久化。

**Tech Stack:** Python 3.11+(dataclass/Protocol/asyncio)、pytest。无外部新依赖。

**前置:** 在仓库新建分支 `feat/agent-loop-inner-ring`(勿在 refactor 分支直接堆)。**新包独立开在 `src/agent_loop/`**(不进 `smart_park_assistant`,那里旧框架太多;pythonpath 含 `src`,直接 `import agent_loop`),测试落 `tests/`。
测试命令统一:`D:\miniconda\python.exe -m pytest <file> -v --timeout=60`(pythonpath 含 `src`)。

---

## 文件结构(职责)

| 文件 | 职责 |
|---|---|
| `agent_loop/__init__.py` | 包导出 |
| `agent_loop/config.py` | `LoopBudget`、`LoopConfig`(按层旋钮) |
| `agent_loop/budget.py` | `BudgetTracker`(轮数/token/deadline/grace/interrupt) |
| `agent_loop/messages.py` | `Message`、`ToolCallReq`(引擎自有,解耦) |
| `agent_loop/conversation.py` | `Conversation`、`ConversationStore`、`InMemoryConversationStore` |
| `agent_loop/tools.py` | `ToolResult`/`OutputBudget`/`ToolContext`/`LoopTool`/`LoopToolRegistry` |
| `agent_loop/stubs.py` | 桩工具 `echo`/`add` + 桩子 agent |
| `agent_loop/plan.py` | `PlanItem`/`PlanState`/`make_plan_tool` |
| `agent_loop/llm.py` | `ModelTurn`/`ModelCaller` 协议/`FakeModelCaller` |
| `agent_loop/loop.py` | `LoopResult`、`assemble`、`run_loop` 引擎 |
| `agent_loop/subagent.py` | `make_subagent_tool`(隔离回吐) |

---

## Task 1: 包骨架 + LoopConfig/LoopBudget

**Files:** Create `src/agent_loop/__init__.py`、`config.py`;Test `tests/test_agent_loop_config.py`

- [ ] **Step 1: 写失败测试**
```python
# tests/test_agent_loop_config.py
from agent_loop.config import LoopBudget, LoopConfig

def test_loop_config_holds_per_layer_knobs():
    budget = LoopBudget(max_iterations=5, token_budget=1000, deadline_s=10.0)
    cfg = LoopConfig(model="hy3-preview", max_tokens=800, temperature=0.0,
                     role="main", toolset=["echo"], budget=budget)
    assert cfg.role == "main"
    assert cfg.toolset == ["echo"]
    assert cfg.budget.max_iterations == 5
    assert cfg.max_depth == 2          # 默认深度上限
    assert budget.max_tool_failures == 3
```
- [ ] **Step 2: 跑测试确认失败** — `... tests/test_agent_loop_config.py -v` → FAIL(ModuleNotFound)
- [ ] **Step 3: 实现**
```python
# src/agent_loop/__init__.py
"""agent_loop: 递归 ReAct 内圈主控循环(手写 while 引擎)。"""
```
```python
# src/agent_loop/config.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class LoopBudget:
    max_iterations: int
    token_budget: int | None = None
    deadline_s: float | None = None   # ⚠ 已弃(G5 弃墙钟);实际 `LoopBudget` 无此字段、`BudgetTracker` 纯计数(`budget.py`)
    max_tool_failures: int = 3

@dataclass(frozen=True)
class LoopConfig:
    model: str
    max_tokens: int
    temperature: float
    role: Literal["main", "leaf"]
    toolset: list[str]
    budget: LoopBudget
    max_depth: int = 2
```
- [ ] **Step 4: 跑测试确认通过** — PASS
- [ ] **Step 5: 提交** — `git add ... && git commit -m "feat(agent_loop): LoopConfig/LoopBudget per-layer knobs"`

---

## Task 2: BudgetTracker(Hermes 模板)

**Files:** Create `agent_loop/budget.py`;Test `tests/test_agent_loop_budget.py`

- [ ] **Step 1: 写失败测试**
```python
# tests/test_agent_loop_budget.py
import time
from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget

def test_iteration_exhaustion_then_one_grace():
    t = BudgetTracker(LoopBudget(max_iterations=2))
    t.consume(iterations=1); assert not t.exhausted()
    t.consume(iterations=1); assert t.exhausted()
    assert t.grace_available is True          # 耗尽后允许一次 grace
    t.use_grace(); assert t.grace_available is False

def test_token_and_interrupt():
    t = BudgetTracker(LoopBudget(max_iterations=99, token_budget=100))
    t.consume(tokens=100); assert t.exhausted()
    t2 = BudgetTracker(LoopBudget(max_iterations=99))
    assert not t2.interrupted
    t2.request_interrupt(); assert t2.interrupted
```
- [ ] **Step 2: 跑测试确认失败** — FAIL
- [ ] **Step 3: 实现**
```python
# src/agent_loop/budget.py
from __future__ import annotations
import time
from .config import LoopBudget

class BudgetTracker:
    """主/子共享同一实例 = 共享预算池。"""
    def __init__(self, budget: LoopBudget) -> None:
        self._b = budget
        self._iters = 0
        self._tokens = 0
        self._start = time.monotonic()
        self._grace_used = False
        self._interrupted = False

    def consume(self, *, iterations: int = 0, tokens: int = 0) -> None:
        self._iters += iterations
        self._tokens += tokens

    def exhausted(self) -> bool:
        if self._iters >= self._b.max_iterations:
            return True
        if self._b.token_budget is not None and self._tokens >= self._b.token_budget:
            return True
        if self._b.deadline_s is not None and (time.monotonic() - self._start) >= self._b.deadline_s:
            return True
        return False

    @property
    def grace_available(self) -> bool:
        return self.exhausted() and not self._grace_used

    def use_grace(self) -> None:
        self._grace_used = True

    def request_interrupt(self) -> None:
        self._interrupted = True

    @property
    def interrupted(self) -> bool:
        return self._interrupted
```
- [ ] **Step 4: 跑测试确认通过** — PASS
- [ ] **Step 5: 提交** — `git commit -m "feat(agent_loop): BudgetTracker with shared pool + grace + interrupt"`

---

## Task 3: 消息 + 会话(消息即状态)

**Files:** Create `agent_loop/messages.py`、`conversation.py`;Test `tests/test_agent_loop_conversation.py`

- [ ] **Step 1: 写失败测试**
```python
# tests/test_agent_loop_conversation.py
import asyncio
from agent_loop.messages import Message, ToolCallReq
from agent_loop.conversation import (
    Conversation, InMemoryConversationStore)

def test_conversation_appends_messages():
    conv = Conversation(thread_id="t1")
    conv.append(Message(role="user", content="hi"))
    conv.append(Message(role="assistant", content="",
                        tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"x": "y"})]))
    assert len(conv.messages) == 2
    assert conv.messages[1].tool_calls[0].name == "echo"

def test_inmemory_store_roundtrip():
    store = InMemoryConversationStore()
    async def run():
        await store.append("t1", Message(role="user", content="hi"))
        conv = await store.load("t1")
        return conv
    conv = asyncio.run(run())
    assert conv.messages[0].content == "hi"
```
- [ ] **Step 2: 跑测试确认失败** — FAIL
- [ ] **Step 3: 实现**
```python
# src/agent_loop/messages.py
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class ToolCallReq:
    id: str
    name: str
    arguments: dict

@dataclass
class Message:
    role: str                       # system|user|assistant|tool
    content: str = ""
    tool_calls: list[ToolCallReq] = field(default_factory=list)
    tool_call_id: str | None = None # 当 role=tool 时,对应的 call id
    name: str | None = None         # 当 role=tool 时,工具名
```
```python
# src/agent_loop/conversation.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol
from .messages import Message
from .plan import PlanState

@dataclass
class Conversation:
    thread_id: str
    messages: list[Message] = field(default_factory=list)
    plan: PlanState = field(default_factory=PlanState)
    def append(self, msg: Message) -> None:
        self.messages.append(msg)

class ConversationStore(Protocol):
    async def load(self, thread_id: str) -> Conversation: ...
    async def append(self, thread_id: str, msg: Message) -> None: ...

class InMemoryConversationStore:
    def __init__(self) -> None:
        self._data: dict[str, Conversation] = {}
    async def load(self, thread_id: str) -> Conversation:
        return self._data.setdefault(thread_id, Conversation(thread_id=thread_id))
    async def append(self, thread_id: str, msg: Message) -> None:
        (await self.load(thread_id)).append(msg)
```
> 注:`conversation.py` 依赖 `plan.PlanState`(Task 5)。先在 Task 5 前不导入运行;按本计划顺序 Task 5 在 Task 3 之后则需调整——**实现时先建 `plan.py` 的 `PlanState` 空壳**(见 Task 5 Step 3 的 `PlanState`),或把 Task 5 提前到 Task 3 之前。推荐:**先做 Task 5 再做 Task 3**。
- [ ] **Step 4: 跑测试确认通过** — PASS
- [ ] **Step 5: 提交** — `git commit -m "feat(agent_loop): messages-as-state Conversation + InMemory store"`

---

## Task 4: 工具 + 注册表 + 桩工具

**Files:** Create `agent_loop/tools.py`、`stubs.py`;Test `tests/test_agent_loop_tools.py`

- [ ] **Step 1: 写失败测试**
```python
# tests/test_agent_loop_tools.py
import asyncio
from agent_loop.tools import (
    LoopTool, LoopToolRegistry, ToolContext, OutputBudget)
from agent_loop.stubs import echo_tool, add_tool
from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget

def _ctx():
    return ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=9)), depth=0)

def test_registry_only_exposes_toolset_schemas():
    reg = LoopToolRegistry()
    reg.register(echo_tool()); reg.register(add_tool())
    names = [s["function"]["name"] for s in reg.schemas(["echo"])]
    assert names == ["echo"]

def test_echo_and_add_handlers():
    reg = LoopToolRegistry(); reg.register(echo_tool()); reg.register(add_tool())
    r1 = asyncio.run(reg.get("echo").handler({"text": "hi"}, _ctx()))
    assert r1.ok and r1.content == "hi"
    r2 = asyncio.run(reg.get("add").handler({"a": 2, "b": 3}, _ctx()))
    assert r2.content == "5"

def test_output_budget_truncates():
    ob = OutputBudget(max_chars=4)
    assert ob.apply("123456") == "1234…"
```
- [ ] **Step 2: 跑测试确认失败** — FAIL
- [ ] **Step 3: 实现**
```python
# src/agent_loop/tools.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Awaitable, Callable
from .budget import BudgetTracker

@dataclass
class ToolResult:
    ok: bool
    content: str
    error: str | None = None

@dataclass(frozen=True)
class OutputBudget:
    max_chars: int
    def apply(self, text: str) -> str:
        return text if len(text) <= self.max_chars else text[: self.max_chars] + "…"

@dataclass
class ToolContext:
    budget: BudgetTracker
    depth: int

ToolHandler = Callable[[dict, ToolContext], Awaitable[ToolResult]]

@dataclass
class LoopTool:
    name: str
    description: str
    parameters: dict                       # JSON schema(properties)
    handler: ToolHandler
    output_budget: OutputBudget | None = None
    def schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.parameters}}

class LoopToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, LoopTool] = {}
    def register(self, tool: LoopTool) -> None:
        self._tools[tool.name] = tool
    def get(self, name: str) -> LoopTool:
        return self._tools[name]
    def schemas(self, toolset: list[str]) -> list[dict]:
        return [self._tools[n].schema() for n in toolset if n in self._tools]
```
```python
# src/agent_loop/stubs.py
from __future__ import annotations
from .tools import LoopTool, ToolContext, ToolResult

def echo_tool() -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(ok=True, content=str(args.get("text", "")))
    return LoopTool(name="echo", description="回显输入 text",
                    parameters={"type": "object", "properties": {"text": {"type": "string"}},
                                "required": ["text"]}, handler=handler)

def add_tool() -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(ok=True, content=str(int(args["a"]) + int(args["b"])))
    return LoopTool(name="add", description="返回 a+b",
                    parameters={"type": "object",
                                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                                "required": ["a", "b"]}, handler=handler)
```
- [ ] **Step 4: 跑测试确认通过** — PASS
- [ ] **Step 5: 提交** — `git commit -m "feat(agent_loop): LoopTool/registry + echo/add stubs + output budget"`

---

## Task 5: Plan 工具(TodoWrite 式)
> **执行顺序:本任务应在 Task 3 之前完成**(`conversation.py` 依赖 `PlanState`)。

**Files:** Create `agent_loop/plan.py`;Test `tests/test_agent_loop_plan.py`

- [ ] **Step 1: 写失败测试**
```python
# tests/test_agent_loop_plan.py
import asyncio
from agent_loop.plan import PlanState, make_plan_tool
from agent_loop.tools import ToolContext
from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget

def test_plan_tool_replaces_snapshot():
    state = PlanState()
    tool = make_plan_tool(state)
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=9)), depth=0)
    asyncio.run(tool.handler({"items": [
        {"id": "1", "content": "查状态", "status": "doing"},
        {"id": "2", "content": "汇总", "status": "todo"}]}, ctx))
    assert [i.status for i in state.items] == ["doing", "todo"]
    assert state.render().startswith("当前计划")
```
- [ ] **Step 2: 跑测试确认失败** — FAIL
- [ ] **Step 3: 实现**
```python
# src/agent_loop/plan.py
from __future__ import annotations
from dataclasses import dataclass, field
from .tools import LoopTool, ToolContext, ToolResult

@dataclass
class PlanItem:
    id: str
    content: str
    status: str          # todo|doing|done

@dataclass
class PlanState:
    items: list[PlanItem] = field(default_factory=list)
    def replace(self, raw_items: list[dict]) -> None:
        self.items = [PlanItem(id=i["id"], content=i["content"], status=i["status"]) for i in raw_items]
    def render(self) -> str:
        if not self.items:
            return ""
        lines = [f"- [{i.status}] {i.content}" for i in self.items]
        return "当前计划(plan):\n" + "\n".join(lines)

def make_plan_tool(state: PlanState) -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        state.replace(args["items"])            # 全量快照替换(TodoWrite 式)
        return ToolResult(ok=True, content="plan updated")
    return LoopTool(name="plan", description="提交一份全量计划快照(items: id/content/status)",
                    parameters={"type": "object", "properties": {"items": {"type": "array"}},
                                "required": ["items"]}, handler=handler)
```
- [ ] **Step 4: 跑测试确认通过** — PASS
- [ ] **Step 5: 提交** — `git commit -m "feat(agent_loop): TodoWrite-style plan tool + PlanState snapshot"`

---

## Task 6: LLM 适配契约 + FakeModelCaller

**Files:** Create `agent_loop/llm.py`;Test `tests/test_agent_loop_llm.py`

- [ ] **Step 1: 写失败测试**
```python
# tests/test_agent_loop_llm.py
import asyncio
from agent_loop.llm import ModelTurn, FakeModelCaller
from agent_loop.messages import ToolCallReq

def test_fake_model_caller_scripts_turns():
    turns = [
        ModelTurn(content="先查", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "hi"})], usage_tokens=10),
        ModelTurn(content="完成", tool_calls=[], usage_tokens=5),
    ]
    fake = FakeModelCaller(turns)
    out1 = asyncio.run(fake(None, [], []))
    out2 = asyncio.run(fake(None, [], []))
    assert out1.tool_calls[0].name == "echo"
    assert out2.tool_calls == [] and out2.content == "完成"
```
- [ ] **Step 2: 跑测试确认失败** — FAIL
- [ ] **Step 3: 实现**
```python
# src/agent_loop/llm.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Awaitable, Protocol
from .config import LoopConfig
from .messages import Message, ToolCallReq

@dataclass
class ModelTurn:
    content: str
    tool_calls: list[ToolCallReq] = field(default_factory=list)
    usage_tokens: int = 0

class ModelCaller(Protocol):
    async def __call__(self, config: LoopConfig | None,
                       messages: list[Message], tool_schemas: list[dict]) -> ModelTurn: ...

class FakeModelCaller:
    """测试用:按调用次序返回脚本化 ModelTurn。"""
    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = list(turns); self._i = 0
    async def __call__(self, config, messages, tool_schemas) -> ModelTurn:
        turn = self._turns[self._i]; self._i += 1
        return turn
```
> 真实 `call_model`(包 `providers.py` 走 langchain-openai native tool_calls)**留到与运行时接线时实现**,本轮不做(范围边界)。
- [ ] **Step 4: 跑测试确认通过** — PASS
- [ ] **Step 5: 提交** — `git commit -m "feat(agent_loop): ModelTurn + ModelCaller protocol + FakeModelCaller"`

---

## Task 7: run_loop 引擎(核心)

**Files:** Create `agent_loop/loop.py`;Test `tests/test_agent_loop_loop.py`

- [ ] **Step 1: 写失败测试**
```python
# tests/test_agent_loop_loop.py
import asyncio
from agent_loop.loop import run_loop
from agent_loop.config import LoopConfig, LoopBudget
from agent_loop.conversation import Conversation
from agent_loop.tools import LoopToolRegistry
from agent_loop.budget import BudgetTracker
from agent_loop.stubs import echo_tool
from agent_loop.llm import ModelTurn, FakeModelCaller
from agent_loop.messages import ToolCallReq

def _cfg(max_iter=5):
    return LoopConfig(model="m", max_tokens=100, temperature=0.0, role="main",
                      toolset=["echo"], budget=LoopBudget(max_iterations=max_iter))

def test_finishes_when_no_tool_calls():
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([ModelTurn(content="done", tool_calls=[])])
    conv = Conversation(thread_id="t")
    cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    res = asyncio.run(run_loop(cfg, conv, reg, budget, fake))
    assert res.final == "done" and res.status == "completed"

def test_executes_tool_then_continues():
    reg = LoopToolRegistry(); reg.register(echo_tool())
    fake = FakeModelCaller([
        ModelTurn(content="先查", tool_calls=[ToolCallReq(id="c1", name="echo", arguments={"text": "hi"})]),
        ModelTurn(content="完成", tool_calls=[])])
    conv = Conversation(thread_id="t"); cfg = _cfg(); budget = BudgetTracker(cfg.budget)
    res = asyncio.run(run_loop(cfg, conv, reg, budget, fake))
    assert res.final == "完成"
    roles = [m.role for m in conv.messages]
    assert "tool" in roles                      # 工具结果被 append
    assert any(m.role == "tool" and m.content == "hi" for m in conv.messages)

def test_budget_exhaustion_then_grace_stop():
    reg = LoopToolRegistry(); reg.register(echo_tool())
    # 模型每轮都调工具,永不结束 → 预算必须刹停
    looping = [ModelTurn(content="再来", tool_calls=[ToolCallReq(id=f"c{i}", name="echo", arguments={"text": "x"})]) for i in range(20)]
    fake = FakeModelCaller(looping)
    conv = Conversation(thread_id="t"); cfg = _cfg(max_iter=3); budget = BudgetTracker(cfg.budget)
    res = asyncio.run(run_loop(cfg, conv, reg, budget, fake))
    assert res.status == "budget_exhausted"
    assistant_turns = [m for m in conv.messages if m.role == "assistant"]
    assert len(assistant_turns) <= cfg.budget.max_iterations + 1   # 不死循环,至多 +1 grace
```
- [ ] **Step 2: 跑测试确认失败** — FAIL
- [ ] **Step 3: 实现**
```python
# src/agent_loop/loop.py
from __future__ import annotations
from dataclasses import dataclass
from .budget import BudgetTracker
from .config import LoopConfig
from .conversation import Conversation
from .llm import ModelCaller
from .messages import Message
from .tools import LoopToolRegistry, ToolContext, ToolResult

@dataclass
class LoopResult:
    final: str
    status: str            # completed|budget_exhausted|interrupted|failed
    conversation: Conversation

def assemble(config: LoopConfig, conversation: Conversation) -> list[Message]:
    """组装发给模型的消息。plan 渲染进 system(本轮简化;缓存序晚置见 spec §六,留作后续)。"""
    system = f"你是 role={config.role} 的 agent。逐步思考并调用工具完成任务;完成时不要再调工具、直接给最终回答。"
    plan_text = conversation.plan.render()
    if plan_text:
        system = system + "\n\n" + plan_text
    return [Message(role="system", content=system), *conversation.messages]

async def run_loop(config: LoopConfig, conversation: Conversation,
                   registry: LoopToolRegistry, budget: BudgetTracker,
                   model_caller: ModelCaller, depth: int = 0) -> LoopResult:
    failures = 0
    while True:
        if budget.interrupted:
            return LoopResult(final="(中断)", status="interrupted", conversation=conversation)
        is_grace = False
        if budget.exhausted():
            if budget.grace_available:
                budget.use_grace(); is_grace = True       # 给一次收尾
            else:
                return LoopResult(final="(预算耗尽,已尽力收尾)", status="budget_exhausted",
                                  conversation=conversation)

        prompt = assemble(config, conversation)
        schemas = registry.schemas(config.toolset)
        turn = await model_caller(config, prompt, schemas)
        budget.consume(iterations=1, tokens=turn.usage_tokens)

        conversation.append(Message(role="assistant", content=turn.content,
                                    tool_calls=list(turn.tool_calls)))

        if not turn.tool_calls or is_grace:
            status = "budget_exhausted" if is_grace else "completed"
            return LoopResult(final=turn.content, status=status, conversation=conversation)

        for call in turn.tool_calls:
            tool = registry.get(call.name)
            ctx = ToolContext(budget=budget, depth=depth)
            try:
                result: ToolResult = await tool.handler(call.arguments, ctx)
            except Exception as exc:                       # 工具异常→失败结果,模型决定
                result = ToolResult(ok=False, content="", error=str(exc))
            content = result.content if result.ok else f"[error] {result.error}"
            if tool.output_budget:
                content = tool.output_budget.apply(content)
            conversation.append(Message(role="tool", content=content,
                                        tool_call_id=call.id, name=call.name))
            if not result.ok:
                failures += 1
                if failures >= config.budget.max_tool_failures:
                    return LoopResult(final="(连续工具失败,停止)", status="failed",
                                      conversation=conversation)
```
- [ ] **Step 4: 跑测试确认通过** — 三个测试 PASS
- [ ] **Step 5: 提交** — `git commit -m "feat(agent_loop): run_loop engine (native tool-calling, budget+grace+failures)"`

---

## Task 8: 子 agent(agent-as-tool,隔离回吐)

**Files:** Create `agent_loop/subagent.py`;追加 `stubs.py`;Test `tests/test_agent_loop_subagent.py`

- [ ] **Step 1: 写失败测试**
```python
# tests/test_agent_loop_subagent.py
import asyncio
from agent_loop.subagent import make_subagent_tool
from agent_loop.config import LoopConfig, LoopBudget
from agent_loop.conversation import Conversation
from agent_loop.tools import LoopToolRegistry, ToolContext
from agent_loop.budget import BudgetTracker
from agent_loop.stubs import echo_tool
from agent_loop.llm import ModelTurn, FakeModelCaller
from agent_loop.messages import ToolCallReq

def test_subagent_isolated_returns_only_result():
    sub_reg = LoopToolRegistry(); sub_reg.register(echo_tool())
    sub_cfg = LoopConfig(model="light", max_tokens=50, temperature=0.0, role="leaf",
                         toolset=["echo"], budget=LoopBudget(max_iterations=4))
    # 子模型脚本:调一次 echo,再结束并给结果
    sub_fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="s1", name="echo", arguments={"text": "子结果"})]),
        ModelTurn(content="子完成:子结果", tool_calls=[])])
    sub_tool = make_subagent_tool(name="echo_agent", description="子agent",
                                  sub_config=sub_cfg, sub_registry=sub_reg, model_caller=sub_fake)
    shared = BudgetTracker(LoopBudget(max_iterations=10))
    ctx = ToolContext(budget=shared, depth=0)
    result = asyncio.run(sub_tool.handler({"task": "做点事"}, ctx))
    assert result.ok and "子完成" in result.content       # 只回吐归一化结果
    # 共享预算被子的轮数扣减(子跑了2轮)
    assert shared._iters >= 2

def test_depth_limit_blocks_recursion():
    sub_cfg = LoopConfig(model="light", max_tokens=50, temperature=0.0, role="leaf",
                         toolset=[], budget=LoopBudget(max_iterations=4), max_depth=1)
    sub_tool = make_subagent_tool(name="a", description="d", sub_config=sub_cfg,
                                  sub_registry=LoopToolRegistry(),
                                  model_caller=FakeModelCaller([ModelTurn(content="x", tool_calls=[])]))
    ctx = ToolContext(budget=BudgetTracker(LoopBudget(max_iterations=10)), depth=1)  # 已达上限
    result = asyncio.run(sub_tool.handler({"task": "t"}, ctx))
    assert not result.ok and "depth" in (result.error or "")
```
- [ ] **Step 2: 跑测试确认失败** — FAIL
- [ ] **Step 3: 实现**
```python
# src/agent_loop/subagent.py
from __future__ import annotations
from .config import LoopConfig
from .conversation import Conversation
from .llm import ModelCaller
from .loop import run_loop
from .messages import Message
from .tools import LoopTool, LoopToolRegistry, ToolContext, ToolResult

def make_subagent_tool(*, name: str, description: str, sub_config: LoopConfig,
                       sub_registry: LoopToolRegistry, model_caller: ModelCaller) -> LoopTool:
    """把一个隔离子循环包成父可调用的工具:隔离上下文、共享预算池、深度+1、只回吐归一化结果。"""
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        if ctx.depth + 1 > sub_config.max_depth:
            return ToolResult(ok=False, content="", error=f"max depth {sub_config.max_depth} exceeded")
        sub_conv = Conversation(thread_id=f"{name}:{id(args)}")     # 隔离会话
        sub_conv.append(Message(role="user", content=str(args.get("task", ""))))
        sub_res = await run_loop(sub_config, sub_conv, sub_registry,
                                 ctx.budget,            # 共享预算池
                                 model_caller, depth=ctx.depth + 1)
        ok = sub_res.status in {"completed", "budget_exhausted"}
        return ToolResult(ok=ok, content=sub_res.final, error=None if ok else sub_res.status)
    return LoopTool(name=name, description=description,
                    parameters={"type": "object", "properties": {"task": {"type": "string"}},
                                "required": ["task"]}, handler=handler)
```
- [ ] **Step 4: 跑测试确认通过** — PASS
- [ ] **Step 5: 提交** — `git commit -m "feat(agent_loop): agent-as-tool subagent (isolation, shared budget, depth cap)"`

---

## Task 9: 端到端集成测试(主+子+plan)

**Files:** Test `tests/test_agent_loop_integration.py`

- [ ] **Step 1: 写测试**
```python
# tests/test_agent_loop_integration.py
import asyncio
from agent_loop.loop import run_loop
from agent_loop.config import LoopConfig, LoopBudget
from agent_loop.conversation import Conversation
from agent_loop.tools import LoopToolRegistry
from agent_loop.budget import BudgetTracker
from agent_loop.stubs import echo_tool
from agent_loop.plan import PlanState, make_plan_tool
from agent_loop.subagent import make_subagent_tool
from agent_loop.llm import ModelTurn, FakeModelCaller
from agent_loop.messages import ToolCallReq

def test_main_plans_then_delegates_then_finishes():
    # 子 agent
    sub_reg = LoopToolRegistry(); sub_reg.register(echo_tool())
    sub_cfg = LoopConfig(model="light", max_tokens=50, temperature=0.0, role="leaf",
                         toolset=["echo"], budget=LoopBudget(max_iterations=4))
    sub_fake = FakeModelCaller([
        ModelTurn(content="", tool_calls=[ToolCallReq(id="s1", name="echo", arguments={"text": "OK"})]),
        ModelTurn(content="子完成", tool_calls=[])])
    sub_tool = make_subagent_tool(name="worker", description="干活子agent",
                                  sub_config=sub_cfg, sub_registry=sub_reg, model_caller=sub_fake)
    # 主 agent:先 plan,再委派子,再结束
    conv = Conversation(thread_id="main")
    main_reg = LoopToolRegistry(); main_reg.register(sub_tool); main_reg.register(make_plan_tool(conv.plan))
    main_fake = FakeModelCaller([
        ModelTurn(content="先规划", tool_calls=[ToolCallReq(id="p1", name="plan",
            arguments={"items": [{"id": "1", "content": "委派", "status": "doing"}]})]),
        ModelTurn(content="委派子agent", tool_calls=[ToolCallReq(id="d1", name="worker", arguments={"task": "干活"})]),
        ModelTurn(content="全部完成", tool_calls=[])])
    main_cfg = LoopConfig(model="big", max_tokens=200, temperature=0.0, role="main",
                          toolset=["plan", "worker"], budget=LoopBudget(max_iterations=8))
    budget = BudgetTracker(main_cfg.budget)
    res = asyncio.run(run_loop(main_cfg, conv, main_reg, budget, main_fake))
    assert res.final == "全部完成" and res.status == "completed"
    assert conv.plan.items[0].content == "委派"                  # plan 快照生效
    assert any(m.role == "tool" and "子完成" in m.content for m in conv.messages)  # 子结果回吐进主
    assert all("OK" != m.content for m in conv.messages if m.role == "tool" and m.name == "echo")  # 子内部步骤不在主
```
- [ ] **Step 2: 跑测试** — `... tests/test_agent_loop_integration.py -v` → PASS
- [ ] **Step 3: 跑全 agent_loop 测试** — `... tests/test_agent_loop_*.py -v --timeout=60` → 全绿
- [ ] **Step 4: compile 冒烟** — `D:\miniconda\python.exe -m compileall src/agent_loop`
- [ ] **Step 5: 提交** — `git commit -m "test(agent_loop): end-to-end main+plan+subagent integration"`

---

## 验证(端到端)

- `D:\miniconda\python.exe -m pytest tests/test_agent_loop_*.py -v --timeout=60` 全绿。
- 覆盖 spec §八 全部用例:无tool_call即结束、有tool_call续轮、预算耗尽→grace→停(不死循环)、子agent隔离回吐+共享预算+深度上限、plan快照下轮可见、工具失败处理。

## 已知延后(本轮不做,见 spec §九)

- 真实 `call_model`(包 providers.py native tool_calls)、Redis 持久化实现、与 8020 graph 接线、真实设备能力/grounding/语义路由。
- plan 的缓存序晚置(本轮渲染进 system,见 `loop.assemble` 注);后续按 spec §六 改为靠后 ephemeral 注入。

## 自查结论(spec 覆盖)

- §二 引擎形状 → Task 7;§三 各组件 → Task 1-8;§四 数据流(主+子)→ Task 7/8/9;§五 预算共享池+grace+深度 → Task 2/7/8;§六 消息即状态+隔离 → Task 3/8(持久化 InMemory,Redis 延后已标);§七 错误处理 → Task 7(工具失败/连续失败/中断)+ Task 8(子失败);§八 测试 → Task 1-9 全覆盖;§九 范围边界 → "已知延后"。无占位符;类型签名跨任务一致(LoopConfig/BudgetTracker/Message/ToolResult/ModelTurn 全程一致)。

---

**文档联动**：本文档属于 `harness-park-design` 设计文档集。完整索引与阅读顺序见 [README.md](README.md)；关键术语一致性约定见 [术语表与文档联动约定.md](术语表与文档联动约定.md)。
