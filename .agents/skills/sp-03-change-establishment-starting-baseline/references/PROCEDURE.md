# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-03 Change Establishment / Starting Baseline Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-30：组2 Independent Concept Audit PASS AFTER REPAIR + 横向回归 20/20 VERIFIED；证据见组2 两份审计报告）  
> 单一职责：把一次有效 Engineering Trigger 接进工程控制——建立稳定 Change Identity 与最小 Change Record，并绑定真实的 Starting Baseline，使 Impact 有诚实起点。  
> 不是 Approval，不是 Requirement Acceptance，不产生 Design / Impact 结论，也不创建任何 Baseline Transition。  
> 结构化镜像：`第五篇-SP03-ChangeEstablishmentBaselineBinding-OperationContract.yaml`

---

# 1. Trigger

调用 SP-03：

```text
A. 有效 Engineering Trigger 已跨过 Engineering Control Boundary（GI-01）
B. JG-01 完成 Governance Cutover，需要建立第一条正常 Change
C. Incident / Emergency 需要受控修复（压缩但不省略，见 §11）
D. Maintenance / Debt / Deprecation 触发后续工程工作
E. 探索性 Spike 的结论要进入 Product Source 或影响 Decision
```

[时机红线][MUST][BASELINE] Change Record 的建立不得晚于**第一项实质 Engineering Impact / Feasibility / Controlled Modification** 开始之前。

禁止：

```text
Code changed → PR opened → 发现需要 Requirement / Design → 补 Change Record
```

因为此时 Original Intent、Starting Current、Initial Assumption、Impact Basis 已难以可靠恢复（第四篇 Ch2 §18–19）。

---

# 2. 输入

至少：

```text
Engineering Trigger Reference    触发来源（业务需求 / 缺陷 / Incident / 依赖演进 / ...）
Current Context                  SP-01 的输出（含 Truth Status 与 Finding）；
                                 [MUST] 已满足 SP-01 PASS Exit（每项 Truth Status 显式标注）；
                                 SP-03 在 A6 绑定时复核 G-SP01-01（不得基于未声明 Unknown 建 Baseline）
Task Intent                      希望改变什么结果（不是解决方案）
```

可选：

```text
Known Constraint                 已知硬约束（时间 / 合规 / 兼容性）
Related Incident / Release
Urgency
```

---

# 3. 输出

```text
Stable Change ID
Minimum Establishment Record     Change ID / Trigger·Intent Ref / Owner / Record State / Execution Condition / Established At
Initial Scope Hypothesis         路由假设，不是 Impact 结论
Starting Baseline Context        分 Scope 的 Reference Set（可解析到 Revision）
Open Question Disposition        Blocking Question / Managed Unknown 分类与处置
Impact Entry 判定                可进入 SP-04 / BLOCKED（带 Recheck Trigger）
```

SP-03 **不输出**：

```text
Approved for Implementation
Requirement Accepted
Design / Target 结论
Affected Scope（属于 SP-04 / 第四篇第三章）
Baseline Transition（Establishment 不自动创建任何 Current 变化）
```

---

# 4. 核心语义：建立与绑定是两个动作

```text
Establishment   让 Change 拥有身份、Owner、Intent → 进入工程控制
Binding         让 Change 锚定真实 Current Reference → Impact 有事实起点
```

简单 Change 可以在同一事件完成两者；排队 / 长周期 Change 应该**晚些绑定**——建立时 Current 是 R12，等真正开始 Impact 时可能已是 R15，绑定的意义是让 Impact 基于当时真实，而不是基于建单那一刻的快照。

[MUST][BASELINE] 一旦实质 Impact 开始，Starting Baseline 成为**历史锚点**，执行期间 Current 变化不得覆盖它（第四篇 Ch1 §38）。

---

# 5. Engineering Actions

## A1 — 确认 Trigger 有效且已跨过边界

确认该 Trigger 已被接受进入 software engineering responsibility（GI-01）。已在边界内：

```text
会影响受控基线的修改意图
会影响后续工程 Decision 的评估工作
```

尚未跨过边界（不需要 Change）：

```text
纯阅读 / 学习
不产生 Decision 影响的初步了解
Isolated Engineering Spike（产出仅作 Design Input 时）
```

## A2 — 检查 Duplicate / Related Change

搜索已有 Open Change：

```text
同一 Intent 已有 Open Change     → 合并 / 关联，不新建身份
旧 Change 已被 Superseded       → 引用其 fence，明确替代关系
```

Duplicate 判定是 Engineering Decision，不由标题相似度自动决定。

## A3 — 建立 Change Identity 与 Minimum Establishment Record

最低字段（第四篇 Ch2 §40）：

```text
Change ID                    稳定引用，不是 Display Title
Trigger / Intent Reference
Current Change Owner
Record State = OPEN
Execution Condition
Established At
```

推荐但可后补：

```text
Initial Scope Hypothesis
Known Constraint
Open Engineering Question
Urgency / Related Incident
```

小 Change 可以把整个 Record 折叠进 Issue / PR（GI-03、Ch1 §34），只要以上语义可发现、可追。**载体可以轻，语义不能少。**

## A4 — 绑定 Change Owner

[MUST][BASELINE] 建立时 Owner 必须存在——即使 Primary Module Owner 尚未知。

```text
Change Owner ≠ Implementer
Change Owner ≠ 所有 Decision Authority
Change Owner ≠ Requirement Author / Product Owner / Affected Owner
Owner 可以 Handoff（不改变 Change Identity）
不允许 Open Change 长期无 Owner
```

Owner 可以是 Team Identity。

## A5 — 形成 Initial Scope Hypothesis

用途只有三个：

```text
找到 Impact 入口
避免全项目盲扫
给 Baseline Selection 提供驱动
```

[MUST NOT][BASELINE] Initial Scope **不得限制 Impact Traversal**——Impact 中发现范围外受影响对象时，走 Scope Expansion（SP-04），不得装作没看见。

Initial Scope 可以粗到只有 System 级别，也可以从 Incident Runtime 或 Data Resource 开始；它随 Routing Knowledge 修订，且 ≠ Baseline Scope ≠ Implementation Task Scope。

## A6 — 执行 Baseline Binding

从 SP-01 的 Current Context 中，按 Change Intent / Initial Scope **选择**（不是全量绑定）Starting Baseline Reference：

```text
Feature Change        → Requirement / Design / Contract / Data / Source Current
Production Defect     → Release / Runtime / Deployment Record + 相关 Source
Backport              → 对应 Supported Release 的 Scope 内 Reference
Multi-environment     → 多个 Runtime Reference 分别带 Scope
```

[MUST][BASELINE] 每条 Reference 必须可解析到 Revision 粒度并带 Baseline Scope：

```text
✓ source = main @ a1b2c3 (development scope)
✗ source = main
✗ baseline_version = 42
```

`branch = main` 不是长期审计锚点；Runtime State 用 Observation / Deployment Record 绑定；Structure 用第三篇 Structure Revision；Requirement / Contract / Data 只保存 Authority Ref，不复制内容。

## A7 — 处理 Binding 期发现

SP-01 带来的 Finding / Unknown 在此处置：

```text
Authority Conflict        → STOP 争议语义，由 designated owner 按 Concern+Scope 裁决（GI-12）
                           不允许静默选择一边
Known Stale Current       → 显式标注并按 SP-19 / 相应 Change 安排校准；
                           本次 Impact 必须知道自己基于带病 Current
Relevant Drift Finding    → 评估对本 Change 的影响，必要时先修复
Irrelevant Finding        → 记录关联即可，不自动 Block
```

## A8 — 分类 Open Engineering Question

Unknown 存在 ≠ Change 有问题。必须分类：

```text
Blocking Question    不解决则 Impact 方向完全分叉
                     （例：transferReason 只内部展示 vs 进入公开 Event Contract）
                     → 先解决，再进 Impact

Managed Unknown      可以在执行中携带、按 Checkpoint 收敛
                     → 显式记录，带 Owner 与收敛时点
```

分类看 Materiality，不看 Unknown 数量。

[MUST][BASELINE] 使 Hard Gate 归零的分类（如把问题归为 Managed Unknown）必须携带可解析的 Rationale / Evidence 指针（为何不构成方向分叉的判断依据）；只填形式字段不得通过。下游环节（SP-04 A1）有权挑战该分类，发现伪装性分类时退回本规程重判。

[MUST][BASELINE] 信息不足时默认 **Block，不自动 Reject**（BLOCKED ≠ REJECTED）。Blocked Change 仍必须有 Owner 和 Recheck Trigger。

## A9 — 判定 Impact Entry Condition

至少满足（第四篇 Ch2 §111）：

```text
[ ] Stable Change ID exists
[ ] Change Record exists
[ ] Trigger / Intent is resolvable enough
[ ] Current Change Owner exists
[ ] Starting Baseline Context is sufficiently bound
[ ] Initial Scope / Routing Anchor exists
[ ] Blocking Questions resolved enough for meaningful Impact
[ ] Material constraints / urgency visible when applicable
```

"Resolvable enough" ≠ Requirement 完美：只要 Unknown 不会让 Impact 方向完全分叉，即可携带进入。

全部满足 → handoff SP-04；否则 → BLOCKED（带 Recheck Trigger）或回到相应 Return Path（§10）。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Change ID 分配、Record 模板生成、字段完整性检查 | Automation |
| Baseline Reference 可解析性检查（Revision / Scope） | Automation / Guardrail |
| Duplicate / Supersede 判定 | Engineering Decision |
| Owner 指定与 Handoff 接受 | Engineering Decision |
| Blocking vs Managed Unknown 分类 | Engineering Decision |
| Impact Entry 判定 | Guardrail（条件自动核验）+ Engineering Decision（"enough" 的判断） |
| Establishment 本身 | **不是 Gate**——它不是 Approval，不应被实现成审批卡点 |

Hard Gate：

```text
[MUST NOT][BASELINE] 无 Change Record 不得开始实质 Impact / Controlled Modification。
[MUST NOT][BASELINE] Baseline Reference 不可解析到 Revision 粒度不得判定 Binding 完成。
[MUST NOT][BASELINE] Blocking Question 未处理不得进入实质 Impact。
[MUST NOT][BASELINE] 使 Gate 归零的分类不得无可解析 Rationale / Evidence。
[MUST NOT][BASELINE] Current Context 未满足 SP-01 PASS Exit 不得执行 Baseline Binding。
```

---

# 7. PASS Exit

SP-03 完成 = Impact Entry Condition 满足。

完成**不代表**：

```text
Requirement 已 Accepted
Design 已就绪
Implementation 已授权
Affected Scope 已确认
```

---

# 8. Evidence

Evidence by Work：

```text
Change Record 本身（Issue / PR / 专用记录均可）
Pinned Baseline Reference（写进 Record 即成为 Evidence）
Owner 绑定 / Handoff 记录
Open Question 分类与 Disposition
Blocking Question 的澄清记录（仅 Decision / Rationale 需额外记录）
```

Starting Baseline 历史必须保留，不得覆盖（第四篇 Ch1 §38）。

---

# 9. Current Update Obligation

SP-03 **不产生任何 Current 变化**。Establishment 只创建 Change Record 与 Reference 绑定；Current 的修改只能经由后续 Change 执行与 SP-19 Calibration。

SP-03 可能触发（但不执行）：

```text
Stale Current / Drift 的修复建议 → 另行建立修复 Change 或转入 SP-19
```

---

# 10. FAIL / Return Path

```text
Trigger 无效 / 未跨过边界
→ 不建立 Change；退回 Trigger 来源或降级为 Spike / 调研

Duplicate / 应 Supersede
→ 合并、关联或走 Supersession，不新建身份

Baseline Binding Failure（Reference 悬空 / Scope 不明 / Authority 争议未决）
→ 不进入 Impact；按 SP-01 §10 的 Finding 路径先修复导航与 Authority

Blocking Question 未解决
→ Record State = OPEN, Execution Condition = BLOCKED
→ 保留 Owner + Recheck Trigger
→ 不得自动 Reject

Owner 无法指定
→ 不建立；升级给项目治理（同 SP-02 R0 的 Owner resolvable 要求）
```

---

# 11. Exception / Alternative Path

## 11.1 Emergency

Emergency 不豁免 Establishment，但可以**压缩**：

```text
允许最小 Establishment Record + 最小 Binding（Runtime / Release / affected Module）
允许事后补全字段
不允许永久缺失——事后必须补齐并 Reconcile（SP-19 / SP-21）
```

## 11.2 排队 Change 延迟绑定

建立时只完成 A1–A5；开始实质 Impact 前才执行 A6–A9，保证 Binding 反映当时真实 Current。

## 11.3 小 Change 轻量载体

允许 Issue / PR 承载全部语义（GI-03）；不允许借"小"跳过身份、Owner、Baseline 锚点。

## 11.4 Greenfield 第一条 Change

Starting Baseline 可以真实地写 `absent / none`（见 JG-01 Step 8）；前提是 SP-02 R0 已通过、Governance Cutover 已生效。

---

# 12. Theory Trace

```text
Part I:
GI-01 Valid Entry / GI-02 Truthful Context / GI-03 Any Change Controlled
9.2 载体合并 / 9.3 N/A·Deferred·Transferred

Part II:
Requirement / Project Engineering（Trigger 与 Intent 的来源约束）

Part III:
Current Reference 的 Scope / Revision / Authority 语义（Ch1 / Ch2 / Ch8）

Part IV:
Ch1 §B Change Identity / Record / Owner
Ch1 §C Starting / Working Baseline Context
Ch1 §D Record State / Execution Condition
Ch2 全章：Establishment Event、Minimum Record、Owner Binding、
     Baseline Binding、Initial Scope Hypothesis、Open Question、
     Impact Entry Condition
```

---

# 13. Executable Asset References

```text
EA-01 Execution Navigation       Duplicate 搜索与路由入口
EA-05 Issue / PR / Change Template  Minimum Establishment Record 的载体模板
EA-17 Current Navigation Tooling Baseline Reference 可解析性检查
```

模板可以提供默认字段与检查；不得把"模板填完"当作 Establishment 完成（GI-06：声明 ≠ 证据）。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Change Record  = GitHub Issue（或 PR for small change）
  Source Baseline = git SHA
  Data Baseline   = alembic revision
  Runtime Binding = GitHub Environment deployment record

RP-B / RP-C:
  Release Baseline = 已发布 artifact 版本 + channel
  Runtime Binding  = absent（无服务端运行时，显式声明）
```

---

# 15. Example

延续 SP-01 的例子：Current Context 已产出（含 Consumer list = Unknown/Gap 与 Finding SF-017）。

```text
A1 Trigger: 业务已接受"工单转移需记录原因"进入研发 → 边界内
A2 Duplicate: 无相关 Open Change
A3 Record: CHG-WO-017
   Intent = "转移工单时可记录并查询转移原因"（不是"加 transferReason 字段"）
   Owner = team-work-order / State = OPEN / Established At = ...
A5 Initial Scope Hypothesis: workorder module + public API（粗粒度，可扩大）
A6 Binding（由 Intent 驱动选择）:
   Contract Current = openapi v2.3 (public API)
   Data Current     = migration M041 (production DB)
   Source Current   = main @ a1b2c3 (development)
   Module Current   = module-registry R9
A7 Findings: SF-017（search 模块 drift）与本 Change 无关 → 记录关联，不 Block
A8 Open Questions:
   Q1 "v2.3 的完整 Consumer 列表" → 若 transferReason 进入公开 Event Contract
      则 Consumer Impact 方向完全分叉 → Blocking Question，先澄清
   Q2 "历史工单是否回填 transferReason" → Managed Unknown，Design 时收敛
A9 Q1 澄清后 Impact Entry PASS → handoff SP-04
```

注意 A3：Intent 写的是**结果**，不是解决方案——"加字段"是 Design 阶段的候选答案，写进 Intent 会锁死设计空间（第四篇 Ch2 §37）。

---

# 16. 最终原则

> **Change Establishment 的全部意义，是让工程责任有一个稳定、可接管、锚定真实 Current 的起点：身份先于行动，Owner 先于执行，真实基线先于影响分析。它不是审批关卡，不追求信息完美——但身份、Owner、可解析的 Baseline 和对 Unknown 的诚实分类，一样都不能少。晚建的 Change recover 不回起点；没有锚点的 Impact 只是猜测。**
