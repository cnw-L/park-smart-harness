# harness 护栏安全子系统设计说明（生产级）

> 对象：park-smart-harness 智慧园区 AI 服务  
> 日期：2026-07-07  
> 版本：v3.0-production  
> 适用范围：可直接进入代码评审与上线运行  
> 核心约束：护栏为无状态治理层；规则层 mandatory；语义层 optional 且必须显式降级；所有不确定情况默认拒绝；所有决策可审计、可归因、可回滚。
>
> **文档联动**：本册定义五道护栏关卡；内圈循环如何调用护栏见 [`内圈循环-收敛定稿.md`](内圈循环-收敛定稿.md)；会话持久化与挂起状态见 [`会话持久化子系统设计说明.md`](会话持久化子系统设计说明.md)；上下文组装见 [`上下文管理子系统-设计.md`](上下文管理子系统-设计.md)。

---

## 一、生产级目标

### 1.1 业务风险

park-smart-harness 的核心特征是**服务任务 × 不可逆**：设备控制、工单创建、费用减免一旦执行无法简单回滚。护栏不是泛化的内容审核，而是精准防止四类事故：

1. **越权动作**：市民控制员工设备、A 租户用户操作 B 租户资源、跨园区调用。
2. **误操作放大**："开空调" 变成 "开所有空调"、隐式批量、冲突操作（先开后关同一设备）。
3. **自然语言绕过**：prompt 注入、角色扮演、隐式指令诱导确认流程。
4. **执行幻觉**：模型没执行却说执行了，或把计划/意图说成结果。

### 1.2 非功能性要求（SLO）

| 维度 | 目标 | 说明 |
|---|---|---|
| 可用性 | 护栏服务 99.99% | 无状态多副本，自身故障 fail-safe，不拖垮 harness |
| 延迟 | 规则层 P99 < 10 ms；语义层 P99 < 300 ms；执行层 P99 < 500 ms | 执行层含后端调用，依赖缓存与超时 |
| 吞吐 | 单实例 ≥ 2000 QPS | 规则层无 IO；执行层有本地缓存 |
| 正确性 | 误杀率 < 1%，漏杀率 < 0.1% | 基于人工抽样 + 红队测试 |
| 可审计 | 100% 决策进 trace；关键拦截事件保留 180 天 | 只读审计存储 |
| 可回滚 | 策略异常 30 s 内回滚 | 版本化 + 灰度发布 |
| 合规 | 支持租户隔离、数据脱敏、双人审批旁路 | 满足园区多租户场景 |

---

## 二、设计原则

1. **默认拒绝（Deny-by-default）**：任何异常、超时、字段缺失、策略未命中，一律按 `block` 处理，除非明确配置为 `challenge`。
2. **规则层 mandatory，语义层 optional + 显式降级**：规则层必须存在、优先执行、结果确定；语义层超时或异常必须返回降级标记，不能静默放行。
3. **五道关卡覆盖 Agent 全链条**：输入 → 意图 → 准备 → 执行 → 事实。
4. **护栏是只读治理层**：不修改会话状态，不直接执行工具，不写审计后端（只发事件）。
5. **后端权威最终校验**：执行护栏必须调用后端权限/状态服务，不能由模型或本地缓存自判。
6. **所有决策可审计、可归因、可回滚**：统一 `GuardDecision` 格式，进 OTel trace 和审计事件流。
7. **多租户隔离**：权限、 grounding、设备状态必须按 `tenant_id` / `park_id` 过滤。
8. **可旁路但强审计**：紧急情况下支持 break-glass 旁路，必须双人审批、限时、全链路审计。

---

## 三、五道护栏关卡

| 关卡 | 位置 | 核心职责 | 规则层 | 语义层 |
|---|---|---|---|---|
| **输入护栏** | 用户消息进入 run_loop 前 | 防注入、识别紧急词、标记不可信来源 | 关键词/正则黑名单、注入模式、长度限制 | `bert_cn_prompt_attack_detection`（中文注入）+ `Llama-Prompt-Guard-2-86M`（多语言越狱） |
| **意图护栏** | 意图识别后 | 控制类意图必须高置信度，否则澄清 | 用户类型 → 意图映射 | 置信度判断、歧义检测 |
| **准备护栏** | 模型输出 prepare 参数后 | 校验 prepare 参数合法、无歧义、在静态权限范围内 | schema 校验、scope 检查、危险模式拦截 | grounding 一致性、影响范围语义判断 |
| **执行护栏** | 真实执行前 | 后端权限/状态校验、确认分级、幂等、批量冲突检查 | 后端权限、状态、确认分级、缓存校验 | 影响评估、异常模式识别 |
| **事实护栏** | 最终返回用户前 | 输出中的执行类事实必须有 tool result 支撑 | 引用校验、免责声明模板 | 幻觉检测、上下文一致性 |

---

## 四、核心抽象

### 4.1 GuardPolicy

```python
class GuardPolicy(Protocol):
    async def check(
        self,
        payload: GuardPayload,
        context: GuardContext,
    ) -> GuardDecision:
        ...
```

**运行时约束**：
- `check` 必须设置整体超时，默认规则层 100 ms、语义层 300 ms、执行层 1000 ms。
- 超时、未捕获异常、字段缺失必须返回 `block`，`reason_code` 为 `guard_timeout` / `guard_exception` / `guard_malformed_payload`。
- 策略内部必须是纯函数或只读查询，禁止副作用、禁止修改 `context`、禁止直接调用工具。

### 4.2 GuardDecision（严格四值）

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True, slots=True)
class GuardDecision:
    verdict: Literal["allow", "block", "challenge", "clarify"]
    reason_code: str
    reason_message: str
    confidence: float = 1.0
    metadata: dict | None = None
```

| verdict | 含义 | 下游行为 |
|---|---|---|
| `allow` | 放行 | 继续流程，可附带 `disclaimer_injected` 等标记 |
| `block` | 拒绝 | 返回策略拒绝话术，记录审计，终止当前链路 |
| `challenge` | 需要确认 | 生成 challenge token + idempotency_key，进入确认流程 |
| `clarify` | 需要澄清 | 返回澄清问题，不修改状态，不生成 prepared_id |

**注意**：不存在 `review` verdict。`review` 是一种异步动作，不是决策值。紧急场景下护栏返回 `block` 或 `challenge`，同时异步发送 `review` 事件到人工复核队列。

### 4.3 GuardContext

```python
@dataclass(frozen=True, slots=True)
class GuardContext:
    tenant_id: str
    park_id: str | None
    user_id: str
    user_type: Literal["employee", "citizen", "guest", "admin"]
    session_id: str
    trace_id: str
    span_id: str
    permissions: tuple[Permission, ...]
    session_state: Mapping[str, Any]
    conversation_history: Sequence[Mapping[str, Any]]
    client_info: dict[str, Any] | None = None
    request_timestamp: datetime
```

### 4.4 Permission

```python
@dataclass(frozen=True, slots=True)
class Permission:
    scope: str                    # "park:device:prepare"
    resource_type: str            # "device"
    resource_id: str | None       # None 表示通配
    action: str                   # "query" | "prepare" | "execute"
    tenant_id: str
    conditions: tuple[Condition, ...] | None = None
```

`scope` 格式：`{domain}:{resource}:{action}`。便于快速前缀匹配、审计、配置化。

### 4.5 ToolCall / ToolManifest

```python
@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]

@dataclass(frozen=True, slots=True)
class ToolManifest:
    name: str
    version: str                 # semver
    schema: dict                 # JSON Schema
    risk_level: int              # 0=read, 1=write, 2=dangerous, 3=critical
    requires_confirmation: bool
    allowed_user_types: tuple[str, ...]
    resource_type: str
    idempotent: bool
    signature: str               # 工具定义签名，防篡改
    created_at: datetime
    deprecated: bool
```

`ToolManifest` 由 governance 模块统一发布，运行时只加载最新非 deprecated 版本。变更需审批和灰度。

---

## 五、按层拆分的 GuardPayload

```python
type GuardPayload = (
    InputGuardPayload |
    IntentGuardPayload |
    PrepareGuardPayload |
    ExecutionGuardPayload |
    BatchExecutionGuardPayload |
    FactGuardPayload
)

@dataclass(frozen=True, slots=True)
class InputGuardPayload:
    layer: Literal["input"]
    raw_input: str
    source: Literal["voice", "text", "api"]
    language: str = "zh"

@dataclass(frozen=True, slots=True)
class IntentGuardPayload:
    layer: Literal["intent"]
    intent: str
    confidence: float
    slots: dict[str, Any] | None = None

@dataclass(frozen=True, slots=True)
class PrepareGuardPayload:
    layer: Literal["prepare"]
    tool_call: ToolCall
    tool_manifest: ToolManifest
    grounding: GroundingResult | None = None

@dataclass(frozen=True, slots=True)
class ExecutionGuardPayload:
    layer: Literal["execution"]
    tool_call: ToolCall
    tool_manifest: ToolManifest
    prepared_id: str | None = None
    idempotency_key: str | None = None

@dataclass(frozen=True, slots=True)
class BatchExecutionGuardPayload:
    layer: Literal["batch_execution"]
    tool_calls: tuple[ToolCall, ...]
    tool_manifests: tuple[ToolManifest, ...]
    prepared_ids: tuple[str, ...] | None = None

@dataclass(frozen=True, slots=True)
class FactGuardPayload:
    layer: Literal["fact"]
    response: str
    tool_results: tuple[ToolResult, ...]
    referenced_tool_ids: tuple[str, ...] | None = None
```

---

## 六、策略执行引擎

### 6.1 单层执行规则

```python
class GuardLayer:
    def __init__(
        self,
        policies: list[GuardPolicy],
        timeout_ms: int,
        fail_verdict: Literal["allow", "block"] = "block",
    ):
        self.policies = policies
        self.timeout_ms = timeout_ms
        self.fail_verdict = fail_verdict

    async def check(self, payload: GuardPayload, context: GuardContext) -> GuardDecision:
        results = await asyncio.gather(
            *[self._safe_check(p, payload, context) for p in self.policies]
        )
        # 按严格程度返回
        for verdict in ["block", "challenge", "clarify"]:
            for r in results:
                if r.verdict == verdict:
                    return r
        return GuardDecision("allow", "layer_passed", "本层所有策略放行")

    async def _safe_check(
        self, policy: GuardPolicy, payload: GuardPayload, context: GuardContext
    ) -> GuardDecision:
        try:
            return await asyncio.wait_for(
                policy.check(payload, context),
                timeout=self.timeout_ms / 1000.0,
            )
        except asyncio.TimeoutError:
            return GuardDecision(
                "block" if policy.is_mandatory else "allow",
                "guard_timeout",
                f"策略 {policy.name} 超时",
                metadata={"policy": policy.name, "timeout_ms": self.timeout_ms, "degraded": not policy.is_mandatory},
            )
        except Exception as e:
            return GuardDecision(
                "block",
                "guard_exception",
                f"策略 {policy.name} 异常: {type(e).__name__}",
                metadata={"policy": policy.name, "exception": type(e).__name__},
            )
```

- 同层策略**并行执行**。
- 策略必须声明 `is_mandatory: bool`。规则层为 mandatory，语义层为 optional。
- mandatory 策略超时/异常 → `block`；optional 策略超时/异常 → `allow` 并带 `degraded=1` 标记。
- 任意策略返回 `block/challenge/clarify` 时，本层立即返回最严格结果。

### 6.2 跨层降级标记传递

```python
class GuardPipeline:
    async def check(self, payload, context) -> GuardDecision:
        degraded_flags: list[str] = []
        for layer in self.layers:
            decision = await layer.check(payload, context)
            if decision.metadata and decision.metadata.get("degraded"):
                degraded_flags.append(layer.name)
            if decision.verdict != "allow":
                decision.metadata = decision.metadata or {}
                decision.metadata["degraded_flags"] = degraded_flags
                return decision
        if degraded_flags:
            # 整体放行，但附加免责声明或收紧后续处理
            return GuardDecision(
                "allow", "pipeline_passed_with_degradation", "放行，但部分语义层降级",
                metadata={"degraded_flags": degraded_flags},
            )
        return GuardDecision("allow", "pipeline_passed", "全链路放行")
```

语义层降级不是静默放行，必须显式传递到最终输出（附加免责声明或提升后续层阈值）。

---

## 七、challenge 确认流程

### 7.1 Challenge 数据结构

```python
@dataclass(frozen=True, slots=True)
class Challenge:
    token: str                 # JWT，含签名
    idempotency_key: str       # 用于幂等执行
    prepared_id: str | None
    tool_call_hash: str        # 防止确认前后参数被篡改
    expires_at: datetime       # 默认 60s
    impact_level: int
    prompt: str
    created_at: datetime
    confirmed: bool | None = None
    confirmed_at: datetime | None = None
```

### 7.2 流程

```text
执行护栏返回 challenge
        │
        ▼
生成 challenge token + idempotency_key + tool_call_hash
        │
        ▼
返回给客户端：{token, prompt, impact_level, timeout_ms}
        │
        ▼
用户确认：POST /confirm {token, confirm: true/false}
        │
        ▼
服务端校验：
  - token 签名正确
  - 未过期
  - 未消费
  - tool_call 与 prepared_id 关联一致
        │
        ▼
确认通过 → 重新进入执行护栏（跳过 challenge，直接 allow）
        │
        ▼
执行 tool handler，使用 idempotency_key 保证幂等
        │
        ▼
确认拒绝 → 返回拒绝话术
        │
        ▼
超时未确认 → token 自动作废，返回"操作已取消"
```

### 7.3 幂等执行

- `idempotency_key` 在 challenge 生成时确定。
- 执行层用 `idempotency_key` 查询是否已执行过。
- 已执行 → 直接返回上次结果。
- 未执行 → 执行并记录 `idempotency_key` + 结果 + TTL（建议 24h）。

---

## 八、prepared_id 生命周期

### 8.1 生成与校验

```text
准备护栏通过
    │
    ▼
生成 prepared_id（UUID），存入短期缓存（Redis，TTL 60s）
    │
    ▼
执行护栏必须携带 prepared_id
    │
    ▼
校验项：
  - prepared_id 存在且未过期
  - tool_call.name + resource_id + action 与准备时哈希一致
  - tenant_id / user_id 未变更
  - 未被撤销
```

### 8.2 失效条件

- 超过 TTL（默认 60s）。
- 执行护栏使用过一次后标记为 consumed。
- 用户主动取消或会话结束。
- 权限/资源状态变更事件触发失效。

### 8.3 安全意义

防止攻击者绕过准备护栏直接构造执行请求。执行护栏不接受没有合法 `prepared_id` 的控制类 tool call。

---

## 九、外部依赖接口（生产级）

### 9.1 AuthorityClient

Phase 1 合并为一个核心接口，避免过度抽象：

```python
class AuthorityClient(Protocol):
    async def check_permission(
        self,
        user_id: str,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
    ) -> PermissionCheckResult:
        ...

    async def check_resource_state(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
    ) -> StateCheckResult:
        ...

    async def resolve_grounding(
        self,
        tenant_id: str,
        nl_reference: str,
        context: GuardContext,
    ) -> GroundingResult:
        ...

    async def log_audit_event(
        self,
        event: GuardAuditEvent,
    ) -> None:
        ...
```

### 9.2 缓存与保护

所有 AuthorityClient 调用必须：
- 设置超时（默认 1s）。
- 最多重试 1 次。
- 本地缓存热点数据（见第 12 章）。
- 异常/超时返回明确错误码，执行护栏据此 `block`。

### 9.3 返回结构

```python
@dataclass(frozen=True)
class PermissionCheckResult:
    allowed: bool
    reason: str
    reason_code: str
    cached: bool = False

@dataclass(frozen=True)
class StateCheckResult:
    allowed: bool
    reason: str
    reason_code: str
    state: dict | None = None
```

---

## 十、各关卡详细设计

### 10.1 输入护栏

**规则层（mandatory）**：
- 注入模式黑名单："ignore previous instructions"、"DAN"、"jailbreak"、"你是..." 角色扮演前缀。
- 紧急关键词："着火"、"漏水"、"停电"、"事故"。命中后返回 `block` 或 `challenge`，同时异步发送 `review` 事件。
- 来源标记：市民/访客输入默认加不可信标记。
- 输入长度限制：超过 4096 字符直接 `block`。
- 正则/关键词命中后必须记录触发的规则 ID。

**语义层（optional）**：
- `bert_cn_prompt_attack_detection`：中文 prompt injection 检测，覆盖指令覆盖、角色混淆、策略绕过等中文攻击模式。
- `Llama-Prompt-Guard-2-86M`：多语言 jailbreak / prompt injection 检测，覆盖英文及中英混合攻击。
- 两个模型并行运行，任一命中即按阈值处理。
- embedding 相似已知攻击样本库作为辅助召回，阈值 0.85。

**失败处理**：
- 规则层超时/异常 → `block`。
- 任一内容安全模型超时/异常 → 允许其他模型/规则层结果，记录 `content_safety_model_timeout=1` 和具体模型名。
- 两个模型同时不可用时，规则层必须独立放行才算放行；若规则层拦截，按规则层结果处理。

### 10.2 意图护栏

**规则层（mandatory）**：
- 用户类型 → 可用意图映射。
- 市民/访客直接 `block` 控制类意图。
- 控制类意图置信度缺失 → `clarify`。

**语义层（optional）**：
- 歧义检测：如"打开那个门"缺少设备指代 → `clarify`。

**失败处理**：
- 模型异常 → 规则层兜底。
- 语义层降级时，控制类意图置信度阈值自动提高 0.05。

### 10.3 准备护栏

**规则层（mandatory）**：
- 参数 JSON Schema 校验（Pydantic）。
- 资源 ID 在 `context.permissions` 静态快照内。
- 危险模式拦截：`*`、`all`、空 `resource_id`、批量通配。
- 工具 manifest 版本校验：签名正确、未 deprecated。

**语义层（optional）**：
- grounding 一致性：自然语言指代是否解析为唯一资源。
- 影响范围语义判断。

**输出**：通过时生成 `prepared_id`，写入 Redis TTL 60s。

### 10.4 执行护栏

**规则层（mandatory）**：
- 校验 `prepared_id` 合法性。
- 调用 `AuthorityClient.check_permission`（后端实时权威）。
- 调用 `AuthorityClient.check_resource_state`。
- 确认分级（见 10.5）。
- 生成 `idempotency_key`。

**语义层（optional）**：
- 影响评估模型。
- 异常模式识别（时段、频率、IP 变化等）。

**批量执行**：先整体检查冲突和跨租户，再逐个执行。

### 10.5 确认分级

| 等级 | 条件 | 行为 |
|---|---|---|
| L0 | 只读查询 | 自动执行 |
| L1 | 写操作但已授权 | 执行，异步记录日志 |
| L2 | 危险操作、跨资源、高影响 | 返回 `challenge`，弹窗/语音确认 |
| L3 | 关键基础设施、批量操作 | 返回 `block`，转人工工单 |

分级规则配置化，可按工具、用户类型、资源类型、时间段动态调整。

### 10.6 事实护栏

**规则层（mandatory）**：
- 提取执行类断言（"已打开"、"已创建"、"温度为 24 度"）。
- 断言必须有对应 `ToolResult` 支撑。
- 安全关键话题自动附加免责声明。

**语义层（optional）**：
- claim extraction + grounding 比对。

**不校验**：知识问答、建议、计划、推测性表述。

---

## 十一、内容安全模型部署

输入护栏语义层采用双模型并行策略，分别覆盖中文 prompt injection 和多语言 jailbreak。

### 11.1 模型选择

| 模型 | 基座 | 参数量 | 任务 | 覆盖场景 |
|---|---|---|---|---|
| `bixuechao/bert_cn_prompt_attack_detection` | 中文 BERT | ~110M | 中文 prompt injection 二分类 | 指令覆盖、角色混淆、策略绕过、"忽略之前限制" 等中文攻击 |
| `LLM-Research/Llama-Prompt-Guard-2-86M` | mDeBERTa-base | 86M | 多语言 jailbreak / prompt injection | 英文越狱模板、中英混合攻击、跨语言角色扮演 |

### 11.2 部署形态

两个模型以独立微服务或 sidecar 形式部署，输入护栏通过 HTTP/gRPC 调用：

```python
class ContentSafetyClient(Protocol):
    async def classify_cn_prompt_injection(
        self,
        text: str,
        timeout_ms: int = 150,
    ) -> ContentSafetyResult:
        ...

    async def classify_multilingual_jailbreak(
        self,
        text: str,
        timeout_ms: int = 150,
    ) -> ContentSafetyResult:
        ...

@dataclass(frozen=True)
class ContentSafetyResult:
    model: str
    label: Literal["safe", "suspicious", "injection", "jailbreak"]
    score: float
    latency_ms: int
    cached: bool = False
```

部署约束：
- 必须本地化部署，禁止调用外部 API。
- 推荐 ONNX Runtime 或 Transformers 推理，CPU 可跑。
- 模型服务需支持健康检查、自动重启、版本管理。
- 输入文本需做长度截断（512 tokens）。

### 11.3 阈值与决策映射

#### `bert_cn_prompt_attack_detection`

| score | verdict | reason_code |
|---|---|---|
| ≥ 0.90 | `block` | `cn_prompt_injection_high` |
| 0.75 - 0.90 | `challenge` | `cn_prompt_injection_suspicious` |
| 0.40 - 0.75 | `allow` | `cn_prompt_injection_low_risk` |
| < 0.40 | `allow` | `cn_prompt_safe` |

#### `Llama-Prompt-Guard-2-86M`

| score | verdict | reason_code |
|---|---|---|
| ≥ 0.90 | `block` | `jailbreak_high` |
| 0.75 - 0.90 | `challenge` | `jailbreak_suspicious` |
| 0.40 - 0.75 | `allow` | `jailbreak_low_risk` |
| < 0.40 | `allow` | `jailbreak_safe` |

**合并规则**：两个模型并行调用，取最严格 verdict。例如一个 `block` 一个 `allow`，最终 `block`。

### 11.4 多轮对话增强

两个模型均为单文本分类器，缺乏多轮上下文感知。对于多轮场景：

- 方案 A：将当前轮输入与最近 3 轮历史拼接后送入模型。
- 方案 B：单独维护一个轻量多轮上下文异常检测器，识别 "前面说 A，现在诱导说 B" 的渐进式攻击。
- 方案 C：对多轮注入样本做持续收集，用于模型微调。

生产初期推荐方案 A，简单可落地。

### 11.5 模型更新与校准

- 每周用新增 badcase 评估一次误杀/漏杀率。
- 每季度用红队样本重新校准阈值。
- 每半年评估是否需要微调或替换模型。
- 模型版本化，支持 A/B 测试和灰度。

### 11.6 示例策略实现

```python
class CnPromptInjectionPolicy(GuardPolicy):
    async def check(self, payload: InputGuardPayload, context: GuardContext):
        result = await content_safety_client.classify_cn_prompt_injection(
            text=payload.raw_input,
            timeout_ms=150,
        )
        if result.score >= 0.90:
            return GuardDecision(
                "block", "cn_prompt_injection_high",
                "检测到中文提示词注入攻击",
                confidence=result.score,
                metadata={"model": result.model, "score": result.score, "latency_ms": result.latency_ms}
            )
        if result.score >= 0.75:
            return GuardDecision(
                "challenge", "cn_prompt_injection_suspicious",
                "该请求存在异常，请确认",
                confidence=result.score,
                metadata={"model": result.model, "score": result.score}
            )
        return GuardDecision(
            "allow", "cn_prompt_safe", "中文注入检测通过",
            confidence=1.0 - result.score,
            metadata={"model": result.model, "score": result.score}
        )

class MultilingualJailbreakPolicy(GuardPolicy):
    async def check(self, payload: InputGuardPayload, context: GuardContext):
        result = await content_safety_client.classify_multilingual_jailbreak(
            text=payload.raw_input,
            timeout_ms=150,
        )
        if result.score >= 0.90:
            return GuardDecision(
                "block", "jailbreak_high",
                "检测到越狱攻击",
                confidence=result.score,
                metadata={"model": result.model, "score": result.score, "latency_ms": result.latency_ms}
            )
        if result.score >= 0.75:
            return GuardDecision(
                "challenge", "jailbreak_suspicious",
                "该请求存在异常，请确认",
                confidence=result.score,
                metadata={"model": result.model, "score": result.score}
            )
        return GuardDecision(
            "allow", "jailbreak_safe", "越狱检测通过",
            confidence=1.0 - result.score,
            metadata={"model": result.model, "score": result.score}
        )
```

---

## 十二、批量/复合工具调用

一次 LLM 输出多个 tool call 时：

```python
@dataclass(frozen=True)
class BatchExecutionGuardPayload:
    layer: Literal["batch_execution"]
    tool_calls: tuple[ToolCall, ...]
    tool_manifests: tuple[ToolManifest, ...]
    prepared_ids: tuple[str, ...] | None = None
```

处理规则：
1. 检查是否包含冲突操作（如对同一资源先开后关）。
2. 检查是否跨租户/跨园区。
3. 检查批量高危操作（如同时控制 > N 个设备）。
4. 逐个执行执行护栏。
5. 原子性策略：默认"最佳努力"，关键场景配置为"全成功或全失败"。

---

## 十三、缓存策略

### 13.1 缓存数据与 TTL

| 数据 | TTL | 失效方式 |
|---|---|---|
| 用户权限列表 | 30s | 权限变更事件、手动刷新 |
| 资源状态 | 5s | 状态变更事件 |
| grounding 结果 | 60s | 资源元数据变更 |
| 工具 manifest | 300s | 版本号变化 |
| prepared_id | 60s | TTL、使用后消费、权限变更 |
| challenge token | 60s | TTL、确认后消费 |
| idempotency_key 结果 | 24h | 成功后写入 |

### 13.2 缓存保护

- 本地缓存 + Redis 二级缓存。
- 缓存击穿保护：互斥锁，同一 key 只发一个后端请求。
- 缓存穿透：不存在权限也缓存短 TTL（5s），防止恶意请求打爆后端。

---

## 十四、审计事件流

### 14.1 GuardAuditEvent

```python
@dataclass(frozen=True)
class GuardAuditEvent:
    event_id: str
    trace_id: str
    span_id: str
    tenant_id: str
    user_id: str
    session_id: str
    timestamp: datetime
    layer: str
    policy: str
    verdict: str
    reason_code: str
    payload_hash: str
    context_hash: str
    latency_ms: int
    policy_version: str
    metadata: dict | None = None
```

### 14.2 事件流架构

- 护栏服务只发送事件到 Kafka / Pulsar / 内部 MQ。
- 消费者 1：实时告警（误杀突变、攻击模式）。
- 消费者 2：落库存储（只读审计存储，保留 180 天）。
- 消费者 3：badcase 回流（异步，不阻塞主链路）。

### 14.3 OTel Trace

每个护栏决策生成 `guard.decision` span event：

```json
{
  "name": "guard.decision",
  "attributes": {
    "guard.layer": "execution",
    "guard.policy": "authority_client_validator",
    "guard.verdict": "challenge",
    "guard.reason_code": "requires_confirmation",
    "guard.confidence": 1.0,
    "guard.latency_ms": 45,
    "guard.policy_version": "3.0.1",
    "guard.tenant_id": "tenant-001",
    "guard.degraded": false
  }
}
```

---

## 十五、Break-Glass 旁路机制

### 15.1 使用场景

- 护栏策略误杀导致业务中断。
- 紧急运维需要立即执行关键操作。
- 后端权限服务故障，但业务不能停。

### 15.2 申请与审批

```python
@dataclass(frozen=True)
class BreakGlassRequest:
    request_id: str
    user_id: str                 # 被旁路的用户/操作
    operator_id: str             # 申请人
    approver_id: str             # 审批人
    reason: str
    target_decision: GuardDecision
    approval_ticket: str
    expires_at: datetime         # 默认 1h
    created_at: datetime
```

- 必须双人审批（申请 + 审批）。
- 旁路只对单次请求生效，不修改策略。
- 每次旁路立即写入审计存储，15 分钟内通知安全负责人。
- 旁路请求必须携带 `approval_ticket`，可追溯。

---

## 十六、配置化策略组合

```yaml
version: "3.0"

layers:
  input:
    timeout_ms: 100
    policies:
      - name: injection_detector
        type: rule
        is_mandatory: true
        enabled: true
      - name: emergency_keyword_detector
        type: rule
        is_mandatory: true
        enabled: true
      - name: bert_cn_prompt_attack_detection
        type: semantic
        is_mandatory: false
        enabled: true
        timeout_ms: 150
        model: "bixuechao/bert_cn_prompt_attack_detection"
        thresholds:
          block: 0.90
          challenge: 0.75
          low_risk: 0.40
      - name: llama_prompt_guard_2_86m
        type: semantic
        is_mandatory: false
        enabled: true
        timeout_ms: 150
        model: "LLM-Research/Llama-Prompt-Guard-2-86M"
        thresholds:
          block: 0.90
          challenge: 0.75
          low_risk: 0.40
      - name: embedding_attack_detector
        type: semantic
        is_mandatory: false
        enabled: true
        timeout_ms: 300
        threshold: 0.85

  intent:
    timeout_ms: 100
    policies:
      - name: user_type_intent_map
        type: rule
        is_mandatory: true
        enabled: true
      - name: intent_confidence_checker
        type: rule
        is_mandatory: true
        enabled: true

  prepare:
    timeout_ms: 150
    policies:
      - name: schema_validator
        type: rule
        is_mandatory: true
        enabled: true
      - name: scope_checker
        type: rule
        is_mandatory: true
        enabled: true
      - name: grounding_coherence_checker
        type: semantic
        is_mandatory: false
        enabled: true
        timeout_ms: 300

  execution:
    timeout_ms: 1000
    policies:
      - name: prepared_id_validator
        type: rule
        is_mandatory: true
        enabled: true
      - name: authority_client_validator
        type: rule
        is_mandatory: true
        enabled: true
      - name: impact_assessor
        type: rule
        is_mandatory: true
        enabled: true
      - name: anomaly_detector
        type: semantic
        is_mandatory: false
        enabled: false
        timeout_ms: 500

  fact:
    timeout_ms: 150
    policies:
      - name: tool_result_grounding_checker
        type: rule
        is_mandatory: true
        enabled: true
      - name: disclaimer_injector
        type: rule
        is_mandatory: true
        enabled: true

impact_levels:
  L0:
    auto_execute: true
  L1:
    auto_execute: true
    log_async: true
  L2:
    challenge: true
    timeout_ms: 60000
  L3:
    block: true
    create_human_ticket: true

profiles:
  citizen:
    allowed_scopes:
      - "park:device:query"
      - "park:knowledge:query"
      - "park:ticket:create"
  employee:
    allowed_scopes:
      - "park:device:query"
      - "park:device:prepare"
      - "park:knowledge:query"
      - "park:ticket:create"
  admin:
    allowed_scopes:
      - "park:*:*"
```

### 16.1 热更新流程

1. 提交新配置到配置中心。
2. 生成新版本号。
3. 灰度 5% 流量，持续 10 分钟。
4. 观察误杀率、漏杀率、P99 延迟。
5. 异常自动回滚到上一版本（< 30s）。
6. 全量发布后写入审计日志。

---

## 十七、与 run_loop 的集成

```text
run_loop:
  1. 用户消息进入
       └─ 输入护栏 → GuardDecision
            └─ 若 block，返回拒绝话术，发审计事件
  2. 意图识别
       └─ 意图护栏 → GuardDecision
            └─ 若 clarify，返回澄清问题
  3. 模型输出 tool_call (prepare)
       └─ 准备护栏 → GuardDecision
            └─ 若 allow，生成 prepared_id 写入 Redis
  4. 执行前
       └─ 执行护栏 → GuardDecision
            └─ 若 challenge，生成 token/idempotency_key，进入确认流程
            └─ 若 allow，执行 tool handler
  5. tool handler 执行（带 idempotency_key）
  6. 最终输出
       └─ 事实护栏 → GuardDecision
            └─ 若 block，返回兜底话术
```

集成点代码：

```python
async def guard_check(layer_name: str, payload: GuardPayload, context: GuardContext):
    layer = guard_config.get_layer(layer_name)
    try:
        decision = await layer.check(payload, context)
    except Exception as e:
        decision = GuardDecision("block", "guard_exception", str(e))

    await emit_audit_event(decision, payload, context)

    if decision.verdict != "allow":
        return handle_decision(decision)
    return decision
```

---

## 十八、可观测性与指标

### 18.1 核心指标

| 指标 | 类型 | SLO |
|---|---|---|
| `guard_latency_p99_ms` | 延迟 | 规则层 < 50ms，语义层 < 300ms，执行层 < 500ms |
| `guard_blocked_rate` | 比率 | 监控突变 |
| `guard_false_positive_rate` | 比率 | < 1% |
| `guard_false_negative_rate` | 比率 | < 0.1% |
| `guard_authority_timeout_rate` | 比率 | < 0.5% |
| `guard_cache_hit_rate` | 比率 | > 80% |
| `guard_config_reload_duration_ms` | 延迟 | < 30s |
| `guard_break_glass_rate` | 比率 | < 0.01% |

### 18.2 告警规则

- 误杀率连续 10 min > 2% → 告警 + 建议回滚。
- 任意策略 P99 延迟 > 阈值 2 倍 → 告警。
- AuthorityClient 连续失败 > 5 次 → 告警 + 降级模式。
- break-glass 使用 → 立即告警 + 安全负责人通知。

---

## 十九、测试策略

### 19.1 单元测试

每个策略独立测试，覆盖 allow/block/challenge/clarify 各分支。

### 19.2 集成测试

- 完整 run_loop 五层串行行为。
- AuthorityClient 超时/异常 fail-safe。
- prepared_id 生命周期。
- challenge token 过期/篡改/重放。
- 配置热更新与回滚。

### 19.3 红队对抗测试

- 维护 `redteam_samples.jsonl`。
- 每次发布前跑红队测试，漏杀率 < 0.1%。
- 新 badcase 自动加入样本集。

### 19.4 混沌测试

- 随机注入 AuthorityClient 延迟/失败。
- 随机切换配置版本。
- 模拟缓存雪崩。

### 19.5 性能测试

- 压测单实例 2000 QPS。
- 验证规则层 P99 < 10ms。
- 验证缓存命中率 > 80%。

---

## 二十、关键不变量

1. **verdict 严格四值**：`allow`、`block`、`challenge`、`clarify`。
2. **默认拒绝**：任何异常、超时、字段缺失均按 `block` 处理。
3. **规则层 mandatory，语义层 optional + 显式降级**。
4. **控制类操作只能 prepare，不能 execute**。
5. **执行护栏必须走后端 AuthorityClient 实时权威校验**。
6. **执行必须携带合法 prepared_id**。
7. **challenge 必须 token 签名、未过期、未消费、参数一致**。
8. **市民/访客默认无控制权限**。
9. **最终回答中的执行类陈述必须有 tool result 支撑**。
10. **护栏是只读治理层，不修改会话状态，不直接执行工具**。
11. **所有决策可审计、可归因到 trace**。
12. **多租户隔离：权限/ grounding/ 设备状态必须按 tenant_id 过滤**。
13. **break-glass 必须双人审批、限时、全链路审计**。
14. **批量操作必须检查冲突、跨租户、高危放大**。

---

## 二十一、落地路线图

| 阶段 | 周期 | 目标 | 验收标准 |
|---|---|---|---|
| Phase 1 | 2 周 | 规则层五关 + AuthorityClient + prepared_id + challenge + 审计事件流 | 100% 单元覆盖，红队漏杀 < 1%，P99 达标 |
| Phase 2 | 1 周 | 多租户隔离 + 缓存策略 + 配置热更新/灰度 + 内容安全模型部署（`bert_cn_prompt_attack_detection` + `Llama-Prompt-Guard-2-86M`） | 缓存命中率 > 80%，回滚 < 30s，中文注入召回 > 90% |
| Phase 3 | 2 周 | 语义层可选接入（grounding、异常模式识别）+ 批量执行 + break-glass | grounding 歧义召回 > 95%，break-glass 审计闭环 |
| Phase 4 | 持续 | 红队常态化、badcase 回流、A/B 测试 | 误杀 < 1%，漏杀 < 0.1% |

---

## 二十二、诚实边界

1. 输入语义检测（`bert_cn_prompt_attack_detection` / `Llama-Prompt-Guard-2-86M`）存在误杀和漏杀，需持续用中文/多语言红队样本校准。
2. `Llama-Prompt-Guard-2-86M` 对中文原生攻击模式弱于英文，需配合中文模型使用。
3. 两个模型均为单文本分类器，多轮上下文注入召回率有限，需通过历史拼接或独立多轮检测器增强。
4. 执行护栏依赖后端权限系统实时准确性，后端故障会直接威胁安全。
5. 事实护栏只能校验明确声称的执行结果，无法覆盖隐性暗示和推测。
6. 缓存可能带来短暂权限不一致，TTL 和失效机制必须严格设计。
7. break-glass 是最后手段，滥用会抵消护栏价值，必须强审计。
8. LLM-as-Judge 不用于阻断决策，仅用于 badcase 标注和异步复核。

---

**文档联动**：本文档属于 `harness-park-design` 设计文档集。完整索引与阅读顺序见 [README.md](README.md)；关键术语一致性约定见 [术语表与文档联动约定.md](术语表与文档联动约定.md)。
9. 多租户隔离依赖调用方正确传递 tenant_id，网关层必须校验。
