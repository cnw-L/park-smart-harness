# 内圈引擎设计 · agent_loop(递归 ReAct 主控循环)

> harness 内圈("主控循环 + 思考驱动")的设计 spec。
> 上游:`harness落地设计-讨论总结.md`(§一 编排核)、`实施计划.md`(Phase 4)。
> 本 spec 只覆盖**引擎本体**(纯引擎 + 桩工具),不含真实设备能力/grounding/后端/语义路由。

---

## 一、Context(为什么 + 范围)

harness 内圈是一个**递归 ReAct 主控循环**:一个 while 循环,主会话与子会话(子 agent)**共用同一循环**,仅按层调整模型与 token。主会话负责思考+决策,子会话(agent-as-tool)是中间步骤——自动用轻量模型、限定 token 输出、产出**归一化结果**回主会话汇总,主模型再进一步思考。

现有 `capability_platform.ControlledToolLoop` 是**单能力 bounded loop**,在本引擎之下;本引擎是它**之上**的顶层递归循环。本轮交付**纯引擎 + 桩工具**,验证循环骨架,真实能力后续 Phase 接入。

### 已定基石(讨论拍板)
1. **手写 async while 引擎**,主/子同一个 `run_loop(config)`;状态=消息即状态,持久化复用现有 Redis 资源(本轮先 memory 实现)。
2. **Native tool-calling**:thought=消息正文,plan=TodoWrite 式工具,结束=无 tool_call,子 agent=handler 跑子循环的工具。(依赖支持 tool-calling 的模型,如 hy3。)
3. **范围=纯引擎 + 桩工具**:1-2 桩工具 + 1 桩子 agent 验证递归;不接真实设备/grounding/后端/语义路由。

---

## 二、架构(形状)

```
run_loop(config, conversation, registry)  ← 主/子同一函数,递归自相似
  每轮(while 未结束 且 预算未耗尽):
    1. 组装上下文(缓存序: system → … → plan快照(靠后) → 历史)
    2. 调模型(config.model, max_tokens, tools=registry.schemas(config.toolset))
    3. append assistant 消息(content=thought)→ conversation   # append-only 状态
    4. 无 tool_calls → 结束,返回 LoopResult(final=content)
    5. 有 tool_calls → 逐个 dispatch(工具 or 子agent)→ append tool-result
    6. 回到 1(主模型带结果进一步思考)
```

- **主**:config = 主模型 / 大 token / 主工具集 / role=main。
- **子(agent-as-tool)**:某工具 handler 内部再调 `run_loop(子config:轻模型 / 紧 token / 子工具集 / role=leaf / 隔离会话)`,**只回吐归一化结果**;子内部步骤不污染父。

---

## 三、组件与接口(新包 `assistant_core/agent_loop/`)

> 单元小而聚焦,各有单一职责、清晰接口、可独立测试。复用现有 `providers.py`/`models.py`(LLM 调用、消息类型)。

### config.py
```python
@dataclass(frozen=True)
class LoopBudget:
    max_iterations: int          # 轮数上限
    token_budget: int | None     # 总 token 池(主子共享,见 §五)
    deadline_s: float | None     # 墙钟硬超时  ⚠ 已弃(G5 弃墙钟;实际 `LoopBudget`/`BudgetTracker` 无此字段,`budget.py` 纯计数)
    max_tool_failures: int = 3   # 连续失败上限

@dataclass(frozen=True)
class LoopConfig:
    model: str                   # 该层模型(主=大,子=轻)
    max_tokens: int              # 单次输出上限
    temperature: float
    role: Literal["main", "leaf"]
    toolset: list[str]           # 该层可见工具名(候选集)
    budget: LoopBudget
    max_depth: int = 2           # 递归深度上限
```
`LoopConfig` 是"按层"的**唯一旋钮**:主/子差异全在此。

### budget.py
```python
class BudgetTracker:           # Hermes 模板
    def consume(self, *, iterations=0, tokens=0) -> None
    def remaining(self) -> Remaining
    def exhausted(self) -> bool          # 轮数/ token / deadline 任一耗尽
    @property
    def grace_available(self) -> bool    # 耗尽后允许"一次 grace call"收尾
    def request_interrupt(self) -> None  # interrupt → break
```
主子**共享同一 BudgetTracker 实例**(共享预算池);递归深度由 config.max_depth 卡。

### conversation.py
```python
class Conversation:                      # 消息即状态(append-only)
    thread_id: str
    messages: list[Message]              # 复用 models.Message(role/content/tool_calls/tool_call_id)
    plan: PlanState                      # 当前 plan 快照(投影自最近一次 plan 工具调用)
    def append(self, msg: Message) -> None

class ConversationStore(Protocol):
    async def load(self, thread_id: str) -> Conversation
    async def append(self, thread_id: str, msg: Message) -> None

class InMemoryConversationStore(ConversationStore): ...   # 本轮实现 + 测试
# RedisConversationStore: 留接口,复用现有 Redis 资源(后续)
```

### tools.py
```python
@dataclass(frozen=True)
class LoopTool:
    name: str
    schema: dict                         # JSON schema(传给模型 tools 参数)
    handler: Callable[[dict, ToolContext], Awaitable[ToolResult]]
    output_budget: OutputBudget | None   # 结果 token/行 上限(读可截断,见 §六)

class LoopToolRegistry:
    def register(self, tool: LoopTool) -> None
    def schemas(self, toolset: list[str]) -> list[dict]   # 只暴露该层候选
    def get(self, name: str) -> LoopTool
```

### plan.py
```python
class PlanState:                         # done/doing/todo + spec,结构化、保真
    items: list[PlanItem]
PLAN_TOOL: LoopTool                       # TodoWrite 式:模型调它=提交一份全量 plan 快照
                                          # handler 更新 conversation.plan;快照下轮拼回上下文(靠后/缓存序)
```

### llm.py
```python
async def call_model(config: LoopConfig, prompt_messages: list[Message],
                     tool_schemas: list[dict]) -> ModelTurn:
    # 复用 providers.py,走 langchain-openai native tool_calls
    # 返回 ModelTurn(content=thought, tool_calls=[...], usage=tokens)
```

### loop.py
```python
async def run_loop(config: LoopConfig, conversation: Conversation,
                   registry: LoopToolRegistry, budget: BudgetTracker,
                   depth: int = 0) -> LoopResult:
    # §二 的 while 引擎
```

### subagent.py
```python
def make_subagent_tool(*, name: str, description: str,
                       sub_config: LoopConfig,
                       sub_registry: LoopToolRegistry) -> LoopTool:
    # handler: 新建隔离 Conversation(seed=args.task)→ run_loop(sub_config, …, 共享 budget, depth+1)
    #          → 返回归一化结果(LoopResult.final + 结构化摘要),不回传子的内部消息
```

### stubs.py(验证)
- 桩工具:`echo`(回显)、`add`(相加)——无副作用,验证 dispatch + 续轮。
- 桩子 agent:一个 leaf agent(轻 config + 只含 `echo`),验证递归隔离 + 回吐。

---

## 四、数据流(一轮 + 子 agent)

**主一轮**:assemble → call_model → append(assistant, content=thought) → 无 tool_calls?返回 final : 逐 tool_call → dispatch → append(tool-result) → 续。

**子 agent 调用**:主 call `设备agent` 工具 → `make_subagent_tool` 的 handler → 新建隔离 conversation(seed=任务)→ `run_loop(sub_config, 共享budget, depth+1)` 跑到子 final → 归一化 → 作为 **tool-result** append 进**主** conversation → 主续轮汇总。子的内部 messages **不进**主。

---

## 五、配置 & 预算(按层调 + 共享池)

- **按层**:主 config 大模型/大 token;子 config 轻模型/小 token(写在子 agent 定义里,调用时自动套用,主模型不操心)。
- **共享预算池**:主子共用一个 `BudgetTracker`(总 token/轮数池),递归不绕过总闸;`max_depth` 卡深度。
- **耗尽行为**(Hermes 模板):轮数/token/deadline 任一耗尽 → **一次 grace call** 收尾(如实降级)→ 停;**绝不死循环**;interrupt → break。

---

## 六、状态 & 持久化 & 隔离

- **消息即状态**:append-only。plan 是 conversation 上的结构化快照(投影自最近一次 plan 工具调用),组装时**排在靠后/缓存序**(变更频繁的不进缓存前缀)。
- **隔离**:子有独立 conversation,父只拿归一化 tool-result。
- **持久化**:`ConversationStore` 接口;**本轮 InMemory 实现**(跑通+测试);Redis 实现留接口。
  - 〔判断点〕Redis 走"自建 append-only store(按 thread_id append,贴消息即状态 + Hermes 文件=真相)"vs 硬接 langgraph checkpointer——**倾向前者**,本轮不实现。

---

## 七、错误处理

| 情况 | 处理 |
|---|---|
| 工具失败 | append 错误 tool-result,模型自行决定(后续接重规划);连续失败计数 ≥ max_tool_failures → 停 |
| 模型调用失败 | 重试 N 次 → 失败返回 |
| 预算耗尽 | grace call 收尾 → 停(不死循环) |
| interrupt | break,返回当前态 |
| 子 agent 失败 | 归一化为失败 tool-result 回父,父决定 |

---

## 八、测试(TDD)

- 无 tool_call → 立即结束,返回 final。
- 有 tool_call → 执行桩工具 + append result + 续轮。
- 预算耗尽 → grace call → 停(断言不超过 max_iterations+1)。
- 子 agent → 子 messages **不泄漏**到父;父只拿归一化结果;共享 budget 被正确扣减;depth 超限被拒。
- plan 工具 → 更新快照;快照出现在下一轮组装的上下文里。
- 错误 → 工具失败 append 错误 result;连续失败达上限停。

---

## 九、范围边界(本轮)

**建**:`agent_loop/` 引擎(config/budget/conversation/tools/plan/llm/loop/subagent)+ 桩件 + 测试。
**不建**:真实设备能力、grounding、后端调用、语义检索路由、Redis 持久化实现(留接口)、与 8020 graph 的接线。
**命名**:新包 `agent_loop/`(区别于将清理的旧 `harness/` 和按域的 `capability_platform/`)。

---

**文档联动**：本文档属于 `harness-park-design` 设计文档集。完整索引与阅读顺序见 [README.md](README.md)；关键术语一致性约定见 [术语表与文档联动约定.md](术语表与文档联动约定.md)。
