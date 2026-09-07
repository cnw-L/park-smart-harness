# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-06 Work Package Implementation Control Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-30：组2 Independent Concept Audit PASS AFTER REPAIR + 横向回归 20/20 VERIFIED；证据见组2 两份审计报告）  
> 单一职责：把一个 Execution-ready Work Package 受控地转成真实软件输出——明确执行上下文与适用护栏，持续获取绑定 Revision 的 Feedback，正确分类失败与偏差，最终对明确 Scope / Revision 声明 Implementation Outputs Ready。  
> Implementation 不是"写完代码"；Feedback Green ≠ Required Verification Complete；Outputs Ready ≠ Candidate Accepted ≠ Change Done。  
> 结构化镜像：`第五篇-SP06-WorkPackageImplementationControl-OperationContract.yaml`

---

# 1. Trigger

```text
A. Work Package 达到 Execution-ready（SP-05 A9，正常入口）
B. Feedback Finding / Review Finding 需要 Rework（新 Revision）
C. Base Context 发生 Material Change（需重新判断 Feedback 适用性）
D. Execution Plan Adjustment（不换层的执行组织调整）
```

本规程**不重新决定 Requirement**（Ch2），**不重新写 Design**（Ch4）——发现那两层的问题就回那两层，不在代码里偷改。

---

# 2. 输入

Implementation Entry 最低前提（第四篇 Ch5 §19）：

```text
Execution-ready Work Package
Accepted Design Revision
Owner
Working Source / Base Context
Target Slice
Expected Output
Verification Concern Interface
```

进入时建立 **Implementation Execution Context**（§20-21，最小字段）：

```text
Change ID / Work Package ID / Accepted Design Revision
Working Source / Base Revision / Owner / Target Slice
Expected Output / Verification Concern / Transition Phase（适用）
```

---

# 3. 输出

```text
Implementation Output Set
=
  Application Code
+ Contract Artifact（Contract Change 必须同步）
+ Migration / Schema Output（Data Change 必须同步）
+ Dependency / Config（真实实现的一部分）
+ Observability Hook（适用时）
+ Documentation Update（行为契约变化时）
+ Temporary Compatibility Code（有身份、有退出语义）
+ Feature Flag（受控语义，服从 Ch4 Transition / Cleanup）

+ Implementation Revision Set    唯一解析实际内容的 Revision 绑定
+ Feedback Run 记录              绑定 Revision / Context 的反馈
+ Feedback Finding 处置          分类 + 返回层 + 结果
+ Outputs Ready Progress Fact    带 Subject + Revision Set + Design Revision
```

SP-06 **不输出**：

```text
Candidate Baseline / Candidate 选择（Ch6）
Required Verification Satisfied 结论（Ch6）
Release / Production Delivery（Ch7-8）
Current 任何更新（Merge ≠ Current Design Update，§190）
```

---

# 4. 核心语义

```text
Feedback Green ≠ Required Verification Complete
Deviation ≠ Drift                    Deviation 可受控处理；Drift 是无声越界
Outputs Ready ≠ Candidate Accepted ≠ Change Done
Rework 是正常路径，不是失败           目标不是把 Rework 降到 0
Local Workspace 可以暂时不 Green     但 Local Failure 不应长期进入共享基线
Feedback 的价值取决于绑定上下文       脱离 Revision 的 Green 没有意义
Incomplete Feature ≠ Broken Software 未完成特性有安全集成机制
```

---

# 5. Engineering Actions

## A1 — 确认 Entry 并建立 Execution Context

核验 §2 输入齐全，写出 Execution Context 最小字段。没有它，后续所有 Feedback 都无法绑定。

复核上游使 Gate 归零的处置（SP-05 的 N/A、DELEGATED、Non-blocking 分类）Rationale / Evidence 可解析；发现伪装 → 回 SP-05 挑战，不得静默继承。

## A2 — 解析 Applicable Implementation Guardrail Set

本 WP 真正适用的权威约束集合：

```text
Requirement
Accepted Change Design（本 Change 授权改变什么）
Current Architecture / Module / Contract / Data Authority（未被授权改变的约束）
Constraint / Policy / Security / Quality Rule
```

[MUST][BASELINE] 按 **Current / Target / Transition Applicability** 解析，不得机械并集后要求全部同时不变。合法路径（Current optional → Accepted Target required）本身不是 Deviation；只有偏离被接受的 Current→Transition→Target 路径、或突破未授权改变的 Authority，才进入 Deviation 判断。

## A3 — 定 Source / Build WHERE

从第三篇 `Logical Module → implemented-by → Source Location` 找真实 Source，**不凭目录猜**；Build Unit 不凭 Repository 层级猜。Generated Source 改 Authoritative Input / Generator，不直接改生成物（Generated Output 例外按 §27）。

## A4 — 组成 Implementation Unit 与 Small Batch

```text
Implementation Unit ≠ Work Package（一个 WP 可多个 Unit）
Implementation Unit ≠ PR ≠ Commit（PR 也不一定严格等于一个 Unit）
Small Batch 的真正含义 = 可反馈、可回退、可审查的完整语义切片
Small ≠ 固定 LOC；也不等于越小越好
Behavior Change 与大 Refactor 应尽量分开，但不机械拆 PR
```

## A5 — 产出完整 Output Set

按 §3 清单逐项核对。硬规则：

```text
[MUST] Contract Change 同步 Contract Artifact
[MUST] Data Change 同步 Migration / Schema Output
[MUST] Temporary Compatibility Code 有身份（标记 + 退出语义 + Owner）
[MUST] Feature Flag 服从 Transition / Cleanup 设计
[MUST NOT] Secret 进入普通 Output Set 内容
```

## A6 — 跑 Feedback Loop

Edit ↔ Build ↔ Static Check ↔ Change-local Test 是持续循环，不是 Implementation 完成后第一次发生。四个 Feedback Scope **不是四个强制 Stage**：

```text
Local / Pre-submit / Integration-context / Shared-baseline
```

每类 Feedback 的够用标准：Fast enough / Repeatable enough / Diagnostic enough（都是项目上下文判断，不是固定分钟数）。Behavior Change 应尽量带最直接的 Regression Protection；Static Check ≠ Dynamic Test；Change-local Test ≠ Required Verification 全集。Feedback Build 仍是 Build，但 ≠ Candidate Build ≠ Release Build。

## A7 — 绑定 Feedback 并判断失效

每个 Feedback Run 最小绑定（Ch5 §81 六字段；与 SP-11 的 Feedback Binding 同源）：

```text
Subject Revision / Implementation Revision Set
Base / Integration Context（适用）
Check / Test Identity
Result
Relevant Dependency / Build Context（按风险）
Observed At
```

Green Result 不是永久事实。以下任一变化都必须重新判断旧结果的适用性：

```text
Head Revision 改变 / Base Revision 改变 / Dependency Context 改变 / Test Definition 改变
```

Review Feedback 同样绑定 Revision（与 SP-12 G-SP12-02 同旨）。

## A8 — 分类每一次失败（Failure Classification）

Failure ≠ Implementation Defect。九类：

```text
Implementation Defect              → 本层修（Rework）
Test / Check Defect                → 修测试/检查，不动产品代码
Design Assumption Invalidated      → 回 SP-05（Ch4）
New Impact Discovery               → 回 SP-04（Ch3）
Requirement Semantic Gap           → 回 Requirement（Ch2）
Integration Conflict / Context Change → Integration 处置 + 必要时重评
Tool / Infrastructure Failure      → 修工具链，不 Revert 产品
External Environment / Dependency  → 隔离外部原因
Unknown Failure                    → 先定位再分类
```

[MUST NOT][BASELINE] **不允许默认 rerun-until-green**：先判断失败类型。Flaky Test 走 Quarantine 必须带 Owner / Reason / Follow-up（Ch5 §92；与 SP-11 §11.4 受控 Quarantine 路径同源）——**Quarantine / Skip 不能静默把 Required Evidence 变成 Green**；由此产生的 Required Feedback Evidence Gap 必须显式记录并带处置。

## A9 — 区分 Detail Choice / Plan Adjustment / Deviation / Drift

```text
Detail Choice      Design 明确留给实现、且不动 Target/Boundary/Contract/
                   Data Meaning/Transition/Risk Obligation/Recovery 的选择
                   → 自由，不叫偏差；但仍必须落在 Guardrail Set 内
Plan Adjustment    不动 Accepted Target/Transition/Guardrail 的执行组织调整
                   → 只更新 Plan / Trace；动 Target/Contract/Data/Transition/
                   Recovery/Risk 就升级为 Design Change（回 SP-05）
                   "不换层"判断必须对照该 WP 注册的 Re-evaluation Trigger 清单；
                   调整以 Plan Revision 追加到 Change Record（SP-05 保留语义所有权）
Deviation          偏离 Applicable Guardrail Set 中某项受控边界
                   → 可在代码落地前发现；发现 Deviation 是好事
Drift              无声越界（跨 Data Boundary / 改 Contract 语义 /
                   Temporary Transition 泄漏）→ 禁止，不是流程状态
```

[MUST NOT][BASELINE] **Developer 不能通过代码自行"批准" Deviation**——Design-Relevant Deviation 回 SP-05，扩大 Affected Scope 回 SP-04，来自 Requirement Gap 回 Requirement。

## A10 — Review 与 Integration 受控

```text
Review 是 Feedback，不是"所有行为正确"的证明；Review ≠ Test
Review-ready ≠ Review 是编译错误第一发现者；Reviewer 数量不固定
Review Approval 绑定 Revision；Minor Revision 是否重审由 Policy / Materiality 定
Integration ≠ Deployment ≠ Release；不强制 Trunk-only / 每 PR latest-main
Material Base Change 必须重新判断
Shared Baseline Breakage：先分类（产品缺陷可 Revert / Infra 失败不该 Revert 产品 /
Broken Test 修 Test），有 Owner，优先 Restore；Breakage 不是 Change State
Incomplete Feature 可用 Feature Flag 等机制安全集成
[MUST NOT][BASELINE] Merge ≠ Current Design Update——任何 Current 更新都显式走 SP-19
```

## A11 — 判定 Implementation Outputs Ready

Ready 必须带 **Subject**（如 WP-1@R7）+ **Implementation Revision Set** + 关联 **Design Revision**。最低候选条件：

```text
[ ] Expected Output Set 已存在（§3 清单）
[ ] 输出之间 Coherent（如 Code 依赖 new field，Migration 提供 new field）
[ ] Change-local Feedback（Build / Static / Direct Test）无 Known Blocker
[ ] Known Material Defect = 0（"Known" 必须基于已执行且绑定 Revision 的 Feedback 记录，不接受未检查状态下的自我声明）
[ ] Design-Relevant Deviation 已处理（修了，或新 Design Revision 已接受）
[ ] Temporary Compatibility 有退出语义
[ ] Trace 完整（Change / Work Package / Design / Revision 可找到）
```

Ready 是 **scoped Progress Fact**：多 WP 可分片 Ready，不要求整个 Change 一次性 Implementation Complete。Ready Claim 会失效（新 Revision / Base Context 变化），但**不删除历史**。

Ready **不等于**：All Review Complete / All Integration Complete / Required Verification Complete / Performance Verified / Security Verification Complete / Candidate Baseline / Candidate Accepted / Change Done。

## A12 — Rework 与 Process Signal

```text
Rework 回正确层（Ch5 内修 / SP-05 / SP-04 / Requirement），产生 New Revision
Rework 不要求所有 Check 全量重跑，但不能无依据复用 Green
Repeated Rework、Repeated Ch5→Ch3 返回是 Process Signal——
  用于改进过程，不直接作为人员 KPI
Failed Attempt 不必全部长期保留；有诊断价值的失败（新类别 / 边界案例）值得留
```

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Execution Context 字段完整性 / Output Set 清单核对 | Automation / Guardrail |
| Feedback Run 执行与绑定记录 | Automation |
| Feedback 失效判断（Revision/Context 变化检测） | Automation（产生挑战，结论归人） |
| Guardrail Set 解析 / Deviation vs Detail Choice 判定 | Engineering Decision |
| Failure Classification 与返回层选择 | Engineering Decision |
| Review Approval | Engineering Decision（Authority） |
| Shared Baseline Breakage 处置 | Engineering Decision（Owner） |
| Outputs Ready 判定 | Guardrail（最低条件核验）+ Engineering Decision |

Hard Gate：

```text
[MUST NOT][BASELINE] 无 Execution Context 不得开始实施。
[MUST NOT][BASELINE] 不得 rerun-until-green；失败必须先分类。
[MUST NOT][BASELINE] Quarantine / Skip 不得静默消化 Required Evidence。
[MUST NOT][BASELINE] 不得无声改变 Guardrail（Drift 禁止；Deviation 必须显式处置）。
[MUST NOT][BASELINE] Known Material Defect ≠ 0 或未处理的 Design-Relevant Deviation 存在，不得声明 Outputs Ready。
[MUST NOT][BASELINE] Merge / Push 不更新任何 Current（GI-05；Current 更新走 SP-19——已随组3 落地为正式规程，正式承接此前的 Domain Authority 显式记录 Change 临时路径）。
[MUST NOT][BASELINE] 使 Gate 归零的判定（无 Known Material Defect、无悬挂 Deviation）不得无可解析的 Feedback / 处置证据。
```

---

# 7. PASS Exit

```text
Implementation Outputs Ready（scoped）Progress Fact 形成：
  Subject + Revision Set + Design Revision 绑定，§A11 七项最低条件满足
```

完成**不代表**：Verification 已通过 / Candidate 已选或已接受 / Change 已完成 / Current 已更新。

---

# 8. Evidence

Evidence by Work：

```text
Output Set 本身（代码 / Artifact / Migration / Config）
Feedback Run 记录（绑定 Revision）
Finding 分类与处置记录
Review Approval（绑 Revision）
Ready Claim（Progress Fact 字段：Type / Subject / Revision / Evidence / At）
```

只有 Deviation Proposal、Classification Rationale、Quarantine 决策必须显式记录；Feedback Retention 按诊断价值取舍，不强制全留。

---

# 9. Current Update Obligation

SP-06 **不更新 Current**。Shared Integration Baseline 的演进是 Integration 事实，不等于 Accepted Current Release（§192）；一切 Current 更新显式走 SP-19 Calibration（已随组3 落地为正式规程，正式承接此前的 Domain Authority 显式记录 Change 临时路径；本规程规则不变）。

---

# 10. FAIL / Return Path

```text
Implementation Defect            → 本层 Rework，New Revision
Test / Check Defect              → 修测试；不得改产品代码凑 Green
Design Assumption Invalidated / Design-Relevant Deviation → SP-05
New Impact Discovery / Scope 扩大 → SP-04
Requirement Semantic Gap         → Requirement Authority
Material Base Context Change     → Context Reconciliation（Rebase / Merge-result
                                   Build / Contract Recheck），必要时重评 SP-04/05；
                                   结论追加到 Change Record 的 Working Baseline 段
                                   （append-only，唯一追加点）
Shared Baseline Breakage         → Owner 处置，Restore 优先，分类后选择修/退
WP 无法继续（外部依赖 / 决策缺失）  → Work Package Blocker；
                                   ≠ Change BLOCKED（仍沿用第一章非终态语义）
```

---

# 11. Exception / Alternative Path

## 11.1 Small Change

Unit = PR 通常成立；Execution Context 与 Ready 条件折叠进 PR 描述；语义项不可省。

## 11.2 Emergency

Feedback 可压缩（第四篇 Ch5 §79：Emergency 可以压缩 + 事后补齐验证），压缩范围必须显式记录；Failure Classification、Deviation 处置、Ready 最低条件不豁免；事后补齐并 Reconcile（SP-19 已随组3 落地；SP-21 仍 pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5）。

## 11.3 Generated Output 例外

工具链明确要求改生成物时（§27），记录例外理由与再生成风险。

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05 / GI-06 / GI-07

Part II:
Ch3 实现要求（Implementation Complete = Outputs Ready 的正式解释来源）

Part III:
Source / Build WHERE（implemented-by 导航）、Structure Health（Breakage 语义基础）

Part IV:
Ch1 Progress Fact / BLOCKED 非终态
Ch3 / Ch4（返回层目标）
Ch5 全章：Execution Context / Guardrail Set / Unit·Output Set / Feedback·Binding /
     Failure Classification / Detail·Deviation·Drift / Review·Integration /
     Outputs Ready / Rework
Ch5 §H 最低要求 Checklist（§267–§309）
```

---

# 13. Executable Asset References

```text
EA-08 Verification Harness    Change-local Test / Static Check 的执行载体
EA-01 Execution Navigation    Execution Context 与 Trace 可发现性
EA-11 Review Workflow Assets  Review-ready / Approval 绑定（适用 RP 时）
```

工具适合：跑 Feedback、绑定记录、失效检测挑战、清单核对。
工具不适合：Deviation 判定、Failure Classification、Ready 结论、Review Approval。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Feedback Scopes = local pytest / pre-submit PR checks / compose integration / main CI
  Shared Baseline = main branch（protected）；Breakage Owner = 当周 maintainer
  Unit 载体       = PR；Revision Set = commit SHA（单仓）

RP-B / RP-C:
  Integration = 下游兼容矩阵 CI；Shared Baseline = release 分支
  Runtime Feedback = absent（显式声明）
```

---

# 15. Example

延续 CHG-WO-017 / WP1（data-expand，SP-05 判定 Execution-ready）。

```text
A1 Execution Context: CHG-WO-017 / WP1 / Design D1-r1 / main@a3f9c / Owner=dev-li /
   Target Slice=data expand / Expected=migration+entity / Verification=migration smoke
A2 Guardrail Set: Requirement(可记录转移原因) + Accepted Design D1-r1
   + Current Data Authority(work_order 归 workorder 模块) + expand-only Migration Policy
A5 Output Set: alembic migration（nullable transfer_reason）+ ORM entity 更新
A6 第一轮 Feedback: migration smoke FAIL —— 列被写成 NOT NULL
A8 Classification: Implementation Defect（Guardrail 仍正确：Design 写明 nullable）
   → 本层 Rework，不回 SP-05
A9 期间同事提议"顺手把 status 枚举重构进来"：
   判定 = 超出 Guardrail Set 授权 → 拒绝（若坚持则是 Deviation Proposal → SP-05）
A7 Revision R2 后重跑：Green，绑定 R2 / base a3f9c / dep ctx lock@v8
A10 Review: 1 名 Reviewer，Approval 绑 R2；Integration 进 main 无冲突
A11 Ready 判定: Output Set 齐 / Coherent（entity 与 migration 一致）/ 无 Known
   Material Defect / 无 Deviation 悬挂 / 无临时代码 / Trace 完整
   → Progress Fact: OutputsReady(WP1@R2, design D1-r1)
   不代表：WP2 已 Ready，更不代表 CHG-WO-017 Change Done
```

---

# 16. 最终原则

> **Implementation 的全部纪律，是让"写代码"这件最自由的事发生在明确的护栏之内：执行前先知道自己在实现哪版设计、受哪些权威约束；每次反馈都绑定到能唯一解析的 Revision；每次失败先分类再动手；偏差可以提，但不能在代码里偷批。Green 只是绑定上下文下的局部事实，Ready 只是交卷的声明——验证、候选、发布、Current 更新，各有各的门，Implementation 一扇也不替它们开。**
