# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-04 Impact / Scope Analysis Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-30：组2 Independent Concept Audit PASS AFTER REPAIR + 横向回归 20/20 VERIFIED；证据见组2 两份审计报告）  
> 单一职责：把 Change 放回真实 Current 中理解——识别它对工程事实、依赖、Consumer、Verification、Delivery 和 Runtime 的 Material Effect，并把结论转化为后续必须执行的 Engineering Obligation Profile。  
> 不是代码搜索，不是全图遍历，不做 Design 决策，不输出最终 File List。  
> 结构化镜像：`第五篇-SP04-ImpactScopeAnalysis-OperationContract.yaml`

---

# 1. Trigger

调用 SP-04：

```text
A. SP-03 完成，Impact Entry Condition 满足（正常入口）
B. Re-impact：Material Context Change 使既有 Impact 结论需要重评
C. Re-impact：新增 Consumer / Supported Version
D. Re-impact：Requirement Meaning 变化
E. Re-impact：Implementation Deviation 或 Candidate 新证据挑战原 Impact
```

Re-impact 不重做全量分析：只重评受影响部分，且**新版本不覆盖旧版本**（不覆盖：第四篇 Ch3 §170；部分重评：§123 / §244）。

---

# 2. 输入

至少：

```text
Change Record                  SP-03 产出（ID / Intent / Owner / State）
Starting Baseline Context      可解析的 Reference Set
Initial Scope Hypothesis       路由锚点（可修订，不得限制 Traversal）
Current Context                SP-01 产出（含 Truth Status / Finding）
```

---

# 3. 输出

核心输出：

```text
Impact Assessment Record
=
  Impact Claims                  逐条可验证的工程判断（见 §5.A3）
+ Trace Paths + Stop Reasons     为什么到这里、为什么停在这里
+ Impact Frontier                分析边界的可解释声明
+ Scope Expansion Events         范围扩大/缩小记录（若有）
+ Confirmed Affected Scope       带 Concern 的确认范围
+ Impact Concern Matrix          导航用矩阵，非固定必填清单
+ Unknown Classification         Impact-Blocking / Design / Verification / External
+ Risk Driver Set                风险驱动集合（不是 Risk Score）
+ Engineering Obligation Profile 后续各 Concern 的义务深度配置
+ Change Disposition Basis       供 Authority 做 Change Decision 的依据
```

SP-04 **不输出**：

```text
技术方案 / 技术选型（Ch3 不提前选方案 → SP-05）
最终 File List
Requirement Acceptance（Authority 决策，不是分析产物）
Implementation Plan
```

---

# 4. 核心语义

## 4.1 五个关键词

```text
baseline-scoped    每条 Claim 引用明确 Baseline Reference
traceable          每条结论有可解释 Trace Path
material           只追 Material Effect，不追求大而全
explainable        人能解释"为什么影响它、为什么不传播"
risk-aware         深度由 Risk Driver 驱动，不是统一模板
```

缺任何一项，Impact 就退化成：经验猜测 / 搜索结果 / 大而全清单 / 风险标签。

## 4.2 三个"不是"

```text
不是代码搜索    grep 能回答"谁引用这个 Symbol"，回答不了
               "哪些 Consumer 依赖 Contract、哪些 Runtime 写这份 Data、
                哪些 Supported Release 需要兼容"
不是全图遍历    depends-on 无限扩散没有终点
没有固定 Hop    传播深度由 Stop Reason 决定，不由跳数决定
```

## 4.3 Impact before Design

[MUST][BASELINE] 第二篇已冻结 Impact 先于 Design。不得"先有方案再补影响分析"——方案会反过来锁死 Impact 的视野。

---

# 5. Engineering Actions

## A1 — 确认分析起点

核验 SP-03 输出齐全、Baseline Reference 可解析。起点带病（health-affected Current）时，Impact 必须知道自己基于带病基线。

复核 SP-03 中使 Gate 归零的分类（如 Managed Unknown）的 Rationale / Evidence 指针可解析；发现伪装性分类（实为 Blocking 被标成 Managed）→ 回 SP-03 挑战，不得静默继承。

## A2 — 选择 Impact Seed

Seed 是分析的入口对象，不强制是 Module：

```text
Proposed Requirement
Module / Logical Component
Logical Data / Schema
Contract / Event
Runtime Unit / Deployment
Infrastructure / Shared Service
```

## A3 — 生成 Impact Claim

每条 Claim 最低信息：

```text
Concern            哪个工程关注点（Contract / Data / Runtime / ...）
Target             Object / Relationship / Baseline Scope / Concern
Impact Type        Direct / Indirect / Potential / No-impact
Basis              判断依据（Trace / Evidence / Semantics）
Baseline Ref       基于哪一版 Current
```

四种 Type 的规则：

```text
Direct        语义直接变化（改 Contract 字段、改表结构、改关系）
Indirect      通过依赖传导（Consumer 兼容性）——不等于低风险
Potential     语义未定，暂不能判定——必须有下一步（谁、什么时候收敛）
No-impact     针对具体 Concern 的"无影响"声明——必须有依据，
              "没看到 / grep 没结果"不算
```

[MUST][BASELINE] 旧 Claim 不得删除；重评产生新版本。

## A4 — 执行 Trace 传播

按 Concern 选择方向：

```text
Contract Reverse Trace    从 Contract 找 Consumer
Data Forward/Reverse      谁写 / 谁读这份 Data（Search / Cache 不得成为盲点）
Source / Build Trace      构建与依赖传导（不等于 Structure Change）
Runtime Impact            拆 Concern 看（部署拓扑 / 资源 / 失败域）
Constraint / Policy       可以影响后续义务，但不是 Current Direct Relationship
```

Propagation Judgment 是工程判断，不是 Graph Hop：每一步传播都要能说出语义理由。工具派生的 Trace Path 可以用，但不是第二份 Authority。

## A5 — 判定 Stop Reason，形成 Impact Frontier

合法停止：

```text
Stable Contract Boundary     契约边界稳定吸收变化
Logical Data Meaning 不变    数据语义不传播
Change Semantics 不传播      该变化语义到此处为止
Baseline Scope 不适用        该 Scope 不在约束内
```

非法停止：

```text
✗ 不在 Initial Scope（Initial Scope 不得限制 Traversal）
✗ 另一个 Team 负责（Cross-owner 必须显式协调，不是停止理由）
✗ grep 没结果
✗ 没有计划改代码（不改代码 ≠ 无影响）
```

Frontier 必须可解释；Stop Reason 应有 Evidence 支持。Tool Observation 可以挑战 Declared Trace，但不能自动成为 Authority。

## A6 — 处置 Scope Expansion

Impact 中发现范围外受影响对象是**正常成果**，不是 Change Drift：

```text
记录 Scope Expansion Event
必要时补充 Baseline Reference（新增 Concern 的 Current）
评估是否触发 Split（不是自动规则：规模 / 风险 / Owner 差异大时才考虑）
```

[MUST NOT][BASELINE] 不得改写 Starting Baseline 历史——补充的 Reference 作为 Working Baseline 更新留下 Reason。Working Baseline 更新的唯一追加点 = 该 Change Record 的 Working Baseline 段（append-only），不留分散副本。

## A7 — 形成 Confirmed Affected Scope 与 Concern Matrix

Confirmed Scope 带 Concern，不是最终 File List。Concern Matrix 是导航：

```text
Architecture / Contract / Data / Security / Verification / Release / Project Engineering
```

[MUST][BASELINE] **Verification Impact 与 Release Impact 必须在 Impact 阶段出现**——不能到测试或发布前才发现义务。

## A8 — 分类 Impact Unknown

```text
Impact-Blocking Unknown        不解决则 Decision 依赖猜测 → 必须先解决
Design-Resolvable Unknown      留给 SP-05，带 Owner 与收敛时点
Verification-Resolvable Unknown 留给验证阶段
External-Decision Unknown      需要外部 Authority 决定 → 显式协调
```

[MUST][BASELINE] 使 Gate 归零的分类（Design / Verification-Resolvable 的分流、No-impact 的依据）必须携带可解析的 Rationale / Evidence 指针——Guardrail 核验其存在与可解析性，分类内容本身仍是 Engineering Decision。

## A9 — 形成 Risk Driver Set

列出**具体驱动因素**，不打总分：

```text
Public Contract / External Consumer
Data Authority / Ownership
Migration / Backfill
Security / Trust Boundary
Runtime / Failure Domain
Concurrency / Consistency
Performance / Capacity
Reliability / Availability
Irreversibility
Recovery Difficulty / Blast Radius
Cross-owner / Cross-system
Multiple Supported Versions / Mixed-version
External Platform / Dependency
Regulatory / Audit
High Uncertainty / Weak Current Evidence
```

注：第四篇 Ch3 将 Recovery Difficulty 与 Blast Radius、Multiple Supported Versions 与 Mixed-version Compatibility 分节定义（§138 / §139、§141 / §142）；本清单按工程处置把它们各并为一项（共 15 项），语义全集与 Ch3 一致。

[MUST][BASELINE] 同时评估 **Risk of Change 与 Risk of No Change**——Hotfix 是典型双风险场景：不改的风险可能大于改的风险。

## A10 — 产出 Engineering Obligation Profile

第三章最关键的落地输出——把 Impact / Risk 变成"后面必须做什么"：

```text
Design Depth（D0 / D1 / D2——是其中一维，不等于 Change Risk Level）
Architecture / Specialist Review
Verification Concern / Depth
Contract Compatibility Work
Data Migration / Backfill Work
Security Analysis
Performance / Capacity Analysis
Delivery / Rollout Depth
Recovery / Rollforward
Observability / Operational Readiness
Cross-owner Coordination
```

Profile 可以很短；它**不是审批表**；后续可随新证据重新校准（重校准不覆盖旧版本）。

## A11 — 形成 Change Disposition Basis

把分析依据交给 Authority 做 Change Decision：

```text
Accept      → Requirement Current 更新走 Requirement Authority（Accept ≠ 软件已实现）
Clarify     → 返回 Trigger / Requirement 来源澄清
Split       → 拆分为多个 Change
Supersede   → 被替代，建 fence
Reject      → Current Requirement 不变
```

Corrective Change（修缺陷）不一定改变 Requirement。Disposition 是 Authority 的 Engineering Decision，SP-04 只提供 Basis，不自行批准。

## A12 — 判定 Impact Sufficiency

最低条件：

```text
[ ] Baseline Context 可解释
[ ] Confirmed Affected Scope 已形成
[ ] Critical Consumer / Contract / Data / Runtime Path 已处理
[ ] Material No-impact 有依据
[ ] Potential Impact 有 Disposition
[ ] Impact Frontier / Stop Reason 可解释
[ ] Impact-Blocking Unknown = 0
[ ] Risk Driver Set 已形成
[ ] Engineering Obligation Profile 已形成
[ ] Change Disposition Basis 足够
```

Sufficient ≠ Exhaustive，≠ Perfect。不使用全局 Impact 百分比（除非项目有稳定可解释的分母）。满足 → 形成 Progress Fact，handoff SP-05。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Trace 候选收集、引用搜索、依赖图提取 | Automation |
| Claim 字段完整性、Baseline Ref 可解析性检查 | Automation / Guardrail |
| Tool Observation 挑战 Declared Trace | Automation（产生挑战，不产生结论） |
| Propagation Judgment / Stop Reason | Engineering Decision |
| No-impact 依据的充分性 | Engineering Decision |
| Scope Expansion / Split 判定 | Engineering Decision |
| Risk Driver → Obligation Profile 映射 | Engineering Decision |
| Change Disposition | Engineering Decision（Authority） |
| Impact Sufficiency | Guardrail（最低条件核验）+ Engineering Decision |

Hard Gate：

```text
[MUST NOT][BASELINE] Impact-Blocking Unknown ≠ 0 不得判定 Sufficient。
[MUST NOT][BASELINE] 无依据的 No-impact Claim 不得计入 Sufficiency。
[MUST NOT][BASELINE] Impact 完成前不得开始 Design（SP-05）。
[MUST NOT][BASELINE] Tool Confidence 不得自动当作 Engineering Confidence。
[MUST NOT][BASELINE] 使 Gate 归零的分类不得无可解析 Rationale / Evidence（组2 审计 B1 防线）。
```

---

# 7. PASS Exit

Impact Sufficiency 满足 + Obligation Profile 已形成。

完成**不代表**：

```text
Design 已就绪 / 方案已选
所有 Unknown 已消除（Design/Verification-Resolvable 可携带）
Affected Scope 等于最终改动文件清单
Change 已被 Accept
```

---

# 8. Evidence

Evidence by Work：

```text
Impact Assessment Record（Change-local Navigation，不是 Current Authority）
Trace Snapshot（可作 Evidence，但 Snapshot ≠ Authority）
Claim 的 Baseline Reference
Stop Reason 的支持 Evidence
Scope Expansion / Re-evaluation 的历史版本
Disposition 决策记录（仅 Decision / Rationale 需额外记录）
```

Impact 结果必须成为 Change Record 的可导航内容。

---

# 9. Current Update Obligation

SP-04 自身**不更新 Current**。可能间接触发：

```text
Requirement Accept → Requirement Current 更新（Requirement Authority 执行）
Structure Health Finding → 按第三篇 Finding 处置
Stale / Drift 修复建议 → 修复 Change 或 SP-19
```

---

# 10. FAIL / Return Path

```text
Impact-Blocking Unknown 无法解决
→ 返回 Clarification（Trigger / Requirement 来源）
→ 或 Change BLOCKED（保留 Owner + Recheck Trigger）

Baseline  Reference 失效 / Current 发生 Material Change
→ Working Baseline Reconciliation（留 Reason，不改写历史）
→ 相关 Claim 重评

Scope 爆炸（远超初始假设）
→ 评估 Split / Supersede，不硬撑单 Change

Cross-owner 协调失败
→ 显式升级为 External-Decision Unknown，不静默停止传播

Gate-Relevant Structure Finding（带病基线影响本 Change 关键路径）
→ 先修复 Finding 再判定 Sufficiency
```

---

# 11. Exception / Alternative Path

## 11.1 Small Change

不需要大型 Impact 文档：一条带依据的 Claim + 简短 Obligation Profile 即可。语义项（Type / Basis / Baseline Ref）不可省。

## 11.2 Emergency / Hotfix

允许压缩 Trace 广度，但：

```text
Obligation Profile 仍必须存在
Risk of No Change 必须显式评估
事后必须补齐完整 Impact 记录（SP-19 Reconcile）
```

## 11.3 Re-impact

只重评受 Material Change 影响的部分；新 Claim 版本保留旧版本。

---

# 12. Theory Trace

```text
Part I:
GI-02 Truthful Context / GI-03 Controlled / GI-05 状态不合并 / GI-07 工具边界

Part II:
Ch2 Requirement（Impact before Design、Requirement Decision）
Ch4 Quality / Ch5 Architecture / Ch7 Contract / Ch8 Data（Concern 语义来源）

Part III:
Trace / Typed Relationship / Cross-dimension Mapping（Ch7）
Structure Health Finding（Ch8）

Part IV:
Ch1 §C Baseline Context
Ch3 全章：Impact Claim / Trace / Stop Reason / Scope Expansion /
     Unknown 分类 / Risk Driver / Obligation Profile / Disposition /
     Sufficiency / Re-impact
Ch3 §H 最低要求 Checklist（§223–§250）
```

---

# 13. Executable Asset References

```text
EA-01 Execution Navigation     Seed / Trace 入口
EA-08 Verification Harness     Verification-Resolvable Unknown 的落点
EA-17 Current Navigation Tooling  Trace / Baseline 解析与 Snapshot
```

工具适合：Trace 候选收集、引用搜索、依赖提取、Snapshot、Claim 完整性检查。
工具不适合：Propagation Judgment、Stop Reason、Sufficiency、Disposition。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Contract Trace = openapi diff + consumer 清单
  Data Trace     = alembic 版本链 + ORM 模型引用
  Runtime Trace  = compose / deployment 配置引用

RP-B / RP-C:
  Consumer Trace = 已发布 artifact 的下游依赖声明（包管理元数据）
  Runtime Concern = absent（显式声明）
```

---

# 15. Example

延续 CHG-WO-017（SP-03 已完成；Blocking Question 已澄清：transferReason 内部展示 + 进入公开 WorkOrderTransferred Event）。

```text
A2 Seeds: Proposed Requirement / WorkOrder Module / work_order Logical Data
A3 Claims:
   C1 Direct/Data:      work_order 表新增 transfer_reason 列 (baseline M041)
   C2 Direct/Contract:  WorkOrderTransferred Event 新增字段 (baseline openapi v2.3)
   C3 Indirect/Contract: Event Consumer 兼容性——新增 optional 字段，
                        依据 Contract Compatibility 规则判定非 breaking
   C4 Potential/Data:   reconciliation job 是否读取该字段——语义未定
                        → 下一步: team-data 在 Design 前确认
   C5 No-impact/Module: identity module 不参与 transfer 链路
                        → 依据: Module Responsibility R9 + 无 typed relationship
A4 Trace: Contract Reverse → 3 个已知 Consumer；Data Forward → search index
   （发现 search projection 也从 work_order 读数——非盲点遗漏）
A5 Stop: search projection 仅索引既有字段，Data Meaning 不传播 → 合法 Stop
A6 Scope Expansion: + search module（补充其 Current Baseline Ref，Working Baseline
   更新留 Reason）
A9 Risk Drivers: Public Contract / External Consumer、Data Migration/Backfill、
   Mixed-version Consumer
A10 Obligation Profile:
    Design Depth = D1
    Contract Compatibility Work = required（optional field 规则核验）
    Data Migration / Backfill Work = required（expand-only 方向；历史数据是否回填 =
    Managed Unknown Q2，携带至 Design 收敛——本阶段不锁定答案）
    Verification = contract compatibility test + migration smoke
    Delivery = standard rollout；Recovery = standard rollback
A11 Disposition Basis → Authority Accept → Requirement Current 更新（Authority 执行）
A12 Sufficiency: Impact-Blocking Unknown = 0（C4 已在 Design 前由 team-data 关闭）
   → PASS → handoff SP-05
```

---

# 16. 最终原则

> **Impact Analysis 的全部价值，在于把"我觉得影响不大"变成一组可验证、可解释、锚定真实 Baseline 的工程判断：每条影响有依据，每个"无影响"有证明，每次停止有理由，每个未知有分类。它的终点不是一份清单，而是一份 Obligation Profile——告诉后续所有环节必须做到多深。工具可以帮你找到候选，但"为什么影响、为什么停止、够不够"永远只能是工程判断。**
