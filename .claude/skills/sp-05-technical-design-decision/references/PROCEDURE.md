# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-05 Technical Design / Decision Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-30：组2 Independent Concept Audit PASS AFTER REPAIR + 横向回归 20/20 VERIFIED；证据见组2 两份审计报告）  
> 单一职责：把 Impact 结论转换成可执行且可演进的方案——明确 Target 必须成立的事实、设计安全到达 Target 的 Transition、形成 Accepted Design，并拆出 Execution-ready 的 Work Package。  
> Design 是 Change-local Authority；Accepted Design 不等于 Current Software Fact，不等于 Release 完成，也不是永久冻结。  
> 结构化镜像：`第五篇-SP05-TechnicalDesignDecision-OperationContract.yaml`

---

# 1. Trigger

```text
A. SP-04 Impact Sufficiency PASS 且 Change Disposition 允许继续（正常入口）
B. Design Re-evaluation Trigger 触发（Requirement 变化 / Scope 变化 / 技术选项变化 / 新证据）
C. Material Plan Change 需要升级回 Design 层
```

Re-evaluation 必须**回正确层**（第四篇 Ch4 §205-209）：

```text
Requirement Meaning 变化  → 回 Requirement / SP-04
Affected Scope 变化       → 回 SP-04
Technical Option 变化     → 留在本规程
Implementation Detail     → 留到 SP-06
```

不得全流程重走。

---

# 2. 输入

正式 Design Entry 最低输入（第四篇 Ch4 §5）：

```text
Change Record
Accepted / Applicable Requirement 或 Corrective Intent
Starting / Working Baseline Context
Confirmed Affected Scope
Impact Assessment Revision
Risk Driver Set
Engineering Obligation Profile
Change Disposition Decision（允许 proceed）
```

缺关键输入时可以继续探索（Spike / 草拟），但**不得宣称已具备正式实施依据**。[MUST][BASELINE] Impact 完成前的设计探索必须登记为 Spike（§11.2：一个具体问题 + Expected Evidence + Exit Condition）；不得以自由草拟形式先行完成设计、待 Impact 通过后追溯补认——这与 SP-03 的时机红线同构。

> Change Disposition Decision 的生产者不是任何 SP：它由 Change / Requirement Authority 作出并登记在 Change Record 上（GI-11 / GI-12；SP-04 只提供 Basis）。本规程消费的是该登记项。

Proposed Requirement Change 必须先 Accept 才成为正式 Design 输入；Corrective Change 不得伪造 Requirement Change。

---

# 3. 输出

```text
Accepted Change Design（绑定 Design Revision + Impact Revision）
=
  Target Design              成功后必须成立的目标事实（带 Baseline Scope）
+ Obligation Resolution      对 Ch3 Obligation Profile 的逐项处置
+ Transition Design          中间态 / Invariant / Proceed·Stop·Exit / Cleanup / Recovery（适用时）
+ Design Decisions           与 Assumption 严格分开
+ Critical Assumptions       带 Validation Plan
+ Design Open Items          分类 + Owner + Resolve Stage
+ Design Sufficiency Facts   按 Scope 的充分性判定
+ Execution Plan             Work Package 集 + Dependency + 并行安排
```

SP-05 **不输出**：

```text
Current Design 更新（Design Revision 不自动更新 Current——校准走 SP-19）
Candidate / Release 结论
Implementation 本身
```

---

# 4. 核心语义

```text
Accepted Design ≠ Current Software Fact    被接受的方案不是已实现的事实
Accepted Design ≠ Release Complete         方案接受不是交付完成
Accepted Design ≠ 永久冻结                  Material Design Change 走 Revision
Target 与 Current 同时存在是正常状态
Design 的任务是稳定关键边界，而不是冻结全部实现
Design 不把 Implementation 写成翻译题       实现细节留给 SP-06
```

Design Depth（D0/D1/D2）由 Obligation Profile 驱动，可升级也可有依据地下调：D1 + 深 Migration、D2 + 简单 Delivery 都是合法组合。

---

# 5. Engineering Actions

## A1 — 确认 Design Entry

核验 §2 输入齐全。Requirement 未 Accept 不得把候选 Idea 当 Current Requirement 用。

复核上游使 Gate 归零的分类（SP-04 的 Unknown 分流与 No-impact 依据）Rationale / Evidence 可解析；发现伪装 → 回 SP-04 挑战，不得静默继承。

## A2 — 写 Target Design

Target = **成功后必须成立的目标事实**，不是未来 Current 的完整 Snapshot：

```text
Target Behavior / Responsibility / Contract / Data / Runtime
Target Quality Response / Operations / Observability
```

规则：

```text
[MUST] 带 Baseline Scope
[MUST] 承接 Confirmed Affected Scope 与 Risk Driver Set
[MUST] 可被后续 Verification 理解、被 Calibration 比较
[MUST] 写 Target Non-goal——明确不做什么
[MUST NOT] 塞入无关 Future Wishlist
[MUST NOT] 因实现方便偷偷缩小 Target（缩小 = 回 SP-04）
小 Change 可用 Target Delta；复杂 Change 可用多个 Target View
```

## A3 — 逐项处置 Obligation Resolution

对 SP-04 Obligation Profile 的每一条给出（必须可追到 Ch3）：

```text
DESIGNED          本设计已覆盖，指明在哪里
N/A with reason   不适用 + 理由
DELEGATED         显式委托——带承接方与落点，不等于"以后再说"
BLOCKING          未解决且阻塞——不得带入实施
```

[MUST][BASELINE] 使 Gate 归零的处置（N/A with reason / DELEGATED）的 reason 与承接方必须**可解析、可挑战**：承接方必须真实存在且已被告知；空泛理由不得通过 Guardrail 的指针核验。

## A4 — 设计 Transition（适用时）

Transition 的核心判据：**中间态是否有工程意义**。典型 Trigger：

```text
Old / New Version Coexistence
Data Migration / Backfill
Dual Read / Dual Write
Consumer Migration（Contract Transition）
Runtime / Service Extraction
Feature Flag / Shadow Path
Irreversible Change
```

三个必须分开：

```text
Migration ≠ Transition ≠ Rollout
```

Transition Design 至少包含：

```text
Transition Scope / Phase / Owner
Entry Condition
Transition Invariant     每个中间态必须保持的工程不变量
Effective Behavior       中间态下系统如何工作
Compatibility Rule
Observation / Validation Signal
Proceed / Stop Condition 受 Invariant 约束
Exit Condition           不能只靠日期
Cleanup                  没有 Cleanup 的 Transition 会变成 Transition Leak
Recovery Direction       ≠ Rollback；服从 Data Semantics；
                         必须考虑 Risk of Recovery；Partial Failure 有设计语义
```

Expand / Migrate / Contract 只是 Pattern，不是固定流程；Contract 太早收缩是典型事故。Transition 不设全局天数，可跨多个 Release；**Transition 结束后 Target 才成为新 Current 候选**。

## A5 — 区分 Decision、Assumption 与 Alternative

```text
Design Decision     有据选择——不得伪装成事实
Design Assumption   未验证前提——不得伪装成 Decision
Critical Assumption 必须有 Validation Plan（验证可发生在多阶段）
```

只有存在真实 Material Alternative 时才做 Alternative Analysis（兼容性 / 复杂度 / 风险 / 演进性等 Trade-off）；没有时不要伪造方案凑数。ADR 可以承载 Decision，但 ADR ≠ Change Design 的全部。

## A6 — 分类 Design Open Item

```text
Blocking                            未决会锁死关键边界 → 未清零不得 Sufficient
Non-blocking Implementation Detail  留 SP-06
Verification-resolvable             留验证阶段
```

每条必须有 Owner + Resolve Stage。

## A7 — 判定 Scoped Design Sufficiency

核心问题：

> **现在开始这个 Scope 的实施，会不会因为关键设计仍未决定，而迫使 Developer 在代码里偷偷做重大 Decision？**

最低条件（按适用 Scope）：

```text
[ ] Current / Impact Ref valid
[ ] Target explicit enough
[ ] Affected Boundary explicit
[ ] Required Transition designed
[ ] Engineering Obligation dispositioned
[ ] Critical Failure / Recovery Direction clear
[ ] Verification Direction executable
[ ] Delivery Direction considered
[ ] Blocking Design Open Item = 0
[ ] Critical Assumption has Validation Plan
[ ] Owner / Authority coverage adequate
[ ] Re-evaluation Trigger known
[ ] Target 的每个 Slice 与每条 DESIGNED / DELEGATED Obligation 可追溯到至少一个已定义 Work Package（单个 WP 的 Ready 可滞后）
```

按 Scope 判定（Data Expand 可充分而 Consumer Migration 未充分）——不搞整个 Change 单次 Freeze，但**不得借 Scoped 绕过关键 Boundary**（会锁死 Data Authority / 不可逆 Contract 的 WP 不能称 Ready）。Shared Guardrail Revision 变化会使既有 Scoped Sufficiency 需要重评（Coherence，不是新的全局冻结 Gate）。

## A8 — 接受并锚定 Accepted Design

```text
绑定 Design Revision + 对应 Impact Revision
形成 Design Sufficient Progress Fact
Accepted Design 必须可发现、版本化
```

Sufficiency Decision 可以是自动核验确定性条件；但"explicit enough / adequate"这类判断仍是 Engineering Decision。Design Acceptance 可被撤回（带原因）。Design DRI ≠ Change Owner ≠ Architecture Authority；Review 深度由 Risk 决定，可异步。

## A9 — 形成 Execution Plan 与 Work Package

Execution Plan ≠ Project Schedule，≠ Task Dump。

Work Package 最低信息：

```text
Work Package ID
Purpose / Target Slice
Affected Scope
Accepted Design Revision
Dependencies
Owner
Expected Output
Verification Concern / Evidence Interface
Transition Phase（适用）
Re-evaluation Trigger
```

拆分方式：按 Target Slice、按 Transition Phase，或两者组合。Design ↔ Work Package 双向可追；WP 不得凭个人记忆产生。

Execution Dependency 不只来自源码：

```text
Schema Expand → New Writer
Search Mapping → Reindex
Consumer Compatibility → Mixed-version Rollout
跨 Team Coordination
```

允许并行，但不得为并行忽略 Shared Boundary。不强制 Workflow Engine。

Execution-ready 是 **Scoped Readiness**：不等于整个 Change Ready，不等于所有 Dependency 完成，但**不得锁死未解决的 Critical Decision**。Enabling Work 允许存在，仍须受 Change / Design Trace。Plan 随实施知识演进；Plan Change 不一定升级 Design——但影响 Target / Transition / 关键边界时必须升级（§199）。

SP-05 保留 Execution Plan 的语义所有权：实施期的 Plan Adjustment（SP-06 A9）以 Plan Revision 形式追加到 Change Record 并可被本规程的 Re-evaluation Trigger 消费；"不换层"的判断必须对照该 WP 注册的 Re-evaluation Trigger 清单，不得由实施方单方认定。

## A10 — 注册 Re-evaluation Trigger

为 Design 挂上触发器（Requirement 变化 / Scope 变化 / Material Context 变化 / Candidate 新证据 / Implementation Deviation），并约定各回哪一层。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| 输入完整性 / Open Item 字段 / WP 最低信息检查 | Automation |
| Sufficiency 最低条件核验 | Guardrail |
| Target 是否"explicit enough"、边界是否关键 | Engineering Decision |
| Obligation Resolution 定级 | Engineering Decision |
| Transition Invariant / Proceed·Stop·Exit 设计 | Engineering Decision |
| Design Acceptance / 撤回 | Engineering Decision（Authority） |
| Alternative Trade-off | Engineering Decision |

Hard Gate：

```text
[MUST NOT][BASELINE] Impact 未完成不得进入正式 Design（SP-04 G-SP04-03 的镜像）。
[MUST NOT][BASELINE] Blocking Design Open Item ≠ 0 不得判定 Design Sufficient。
[MUST NOT][BASELINE] Critical Assumption 无 Validation Plan 不得 Sufficient。
[MUST NOT][BASELINE] Obligation 存在未处置的 BLOCKING 项不得进入 Implementation。
[MUST NOT][BASELINE] Accepted Design 不得被当作 Current 写入任何 Current 面（GI-05）。
[MUST NOT][BASELINE] 使 Gate 归零的处置 / 分类不得无可解析理由（N/A 的 reason、DELEGATED 的承接方、Non-blocking 的判定依据）。
```

---

# 7. PASS Exit

```text
适用 Scope 的 Design Sufficiency 判定通过
Accepted Design 锚定 Revision 并可发现
Execution Plan 存在，且至少一个 Work Package 达到 Execution-ready
Re-evaluation Trigger 已注册
```

完成**不代表**：

```text
所有问题已回答（Open Item 可携带）
正式文档齐全（Sufficient ≠ Formal Document Complete）
开过评审会（会议不是充分性证据）
Implementation 已完成或 Candidate 已接受
```

---

# 8. Evidence

Evidence by Work：

```text
Accepted Design Revision（载体不限：设计文档 / Issue / PR 描述 / ADR 集）
Obligation Resolution 记录
Transition Design 与 Invariant
Critical Assumption + Validation Plan
Work Package 定义与 Dependency
Sufficiency 判定记录
```

只有 Decision / Rationale 必须显式记录；其余自然产生。Design / Execution Plan 应版本化，不强制固定文件名。

---

# 9. Current Update Obligation

SP-05 **不更新 Current**。Design Revision 不自动更新 Current Design（第四篇 Ch4 §216）；Target 成为新 Current 候选只能发生在 Transition 结束之后，经 SP-19 Calibration（SP-19 已随组3 落地为正式规程，正式承接此前的 Domain Authority 显式记录 Change 临时路径）。无 Transition 的 Change：Target 在 Implementation Outputs Ready 且 Candidate 被 Ch6 接受后成为新 Current 候选——校准路径不变。

---

# 10. FAIL / Return Path

```text
Design Entry 输入缺失
→ 可 Spike / 草拟，但不得宣称正式实施依据 → 回 SP-03 / SP-04 补齐

Blocking Open Item 无法收敛
→ Design Insufficient：记录缺口、Owner、下一步；
  可回 SP-04 重评 Impact 或回 Requirement 澄清

Critical Assumption 验证失败
→ Material Design Change → 新 Design Revision（保留历史）

Material Context Change / Hidden Consumer 发现
→ 按 A10 注册的 Trigger 回正确层

已实施 Work Package 遇到 Design Revision
→ 不自动重做；按 Revision 适用性评估（§213-214）
```

---

# 11. Exception / Alternative Path

## 11.1 Small Change

全部折叠到 Issue / PR；Target Delta + 简短 Obligation Resolution 即可。语义项不可省。

## 11.2 Technical Spike

用于回答**一个具体问题**；必须有 Expected Evidence 与 Exit Condition（不设固定天数）。Spike Code 不自动成为 Production Implementation——进入 Product Source 必须经正式实施。

## 11.3 无真实 Alternative

不伪造方案分析；记录"无 Material Alternative"本身即可。

---

# 12. Theory Trace

```text
Part I:
GI-02 / GI-03 / GI-05 / GI-07

Part II:
Ch3 技术方案要求 / Ch5 架构要求（Target 的 WHAT 来源）

Part III:
Target / Transition 的 WHERE 投影（Ch4 §87：可投影但不复制第二套 Graph）

Part IV:
Ch3（输入承接：Obligation / Risk Driver / Affected Scope）
Ch4 全章：Target Design / Obligation Resolution / Transition /
     Decision·Assumption / Design Sufficiency / Execution Plan /
     Work Package / Re-evaluation / Revision
Ch4 §H 最低要求 Checklist（§261–§292）
```

---

# 13. Executable Asset References

```text
EA-05 Change / Design Template    Target / Obligation / WP 字段载体
EA-09 Migration / Contract Template  Transition Pattern 的起步骨架
EA-01 Execution Navigation        Design 可发现性
```

模板帮助生成结构；Sufficiency 判定不接受"模板填完"作为证据（GI-06）。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Design 载体     = docs/changes/ 下设计记录或 PR 描述
  Transition 载体 = alembic expand/migrate/contract + feature flag 配置
  WP 载体         = Issue 子任务 / PR

RP-B / RP-C:
  Transition 通常 = 版本兼容窗口（旧版使用者并存）
  Runtime Target  = absent（显式声明）
```

---

# 15. Example

延续 CHG-WO-017（Obligation Profile 来自 SP-04：D1 + Contract Compatibility + expand-only Migration + 兼容性测试）。

```text
A2 Target:
   Behavior: 转移工单时必须可记录原因，可在工单详情查询
   Contract: WorkOrderTransferred Event 增加 optional transferReason 字段
   Data:     work_order 表增加 nullable transfer_reason 列
   Non-goal: 不回填历史数据（Managed Unknown Q2 在本规程收敛——Decision：
            转移原因是审计增量信息，历史空值语义可接受）；不改变既有事件字段语义
A3 Obligation Resolution:
   D1 Design            → DESIGNED（本记录）
   Contract Compat      → DESIGNED（§A5 Decision：optional 字段 + 兼容性测试）
   Migration expand-only → DESIGNED（alembic 单列新增）
   Observability        → N/A with reason（无新运行时行为）
A4 Transition:
   Trigger = Mixed-version Consumer 并存
   Invariant: 旧 Consumer 在任一中间态都能正确消费事件（忽略未知字段）
   Exit: 兼容性测试通过 + 一个完整 Release 周期观察无 Consumer 报错（不靠日期）
   Recovery Direction: 字段停止发布（forward fix），不回滚已发布事件
   Cleanup: 无临时态——无需 cleanup（显式声明）
A5 Critical Assumption: "所有现存 Consumer 容忍未知 optional 字段"
   Validation Plan: contract compatibility test（WP2 的 Verification Interface）
A6 Open Items: 无 Blocking；event 字段最大长度 = Non-blocking Implementation Detail
A7 Sufficiency(D1 scope): 12 项最低条件全过
A8 Accepted Design Revision D1-r1 绑定 Impact R2 → Progress Fact
A9 Execution Plan:
   WP1 data-expand（migration + entity）→ Execution-ready 立即
   WP2 event+api（contract + handler + 兼容性测试）→ depends on WP1
A10 Re-evaluation: 若发现未知 Consumer → 回 SP-04 §123
```

---

# 16. 最终原则

> **Design 的全部意义，是让实施者在写代码时不再需要偷做重大决定：Target 说清"成功后什么必须成立"，Transition 说清"中间态如何安全"，Obligation Resolution 说清"每条义务落在哪"，Sufficiency 只回答一个问题——现在开始写代码，关键边界是否已经稳定。方案被接受不等于事实已改变；Target 只有走完 Transition、经过 Calibration，才配成为新的 Current。**
