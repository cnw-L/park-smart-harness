# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-15 Release / Deployment Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-31：组3 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1050 处引用核验 PASS AFTER REPAIR（备注级）；证据见组3 审计报告与横向回归报告）  
> 单一职责：把 Accepted Candidate 形成为**身份真实、范围显式的 Release Baseline**，作出 Release Decision，对每个 Delivery Target 作出可追、可再验证的 Delivery Authorization，执行受控 Deployment Attempt 与 Rollout，维护真实及时的 Environment Current Runtime State，并按 Delivery Finding 分类把问题路由回正确的层。  
> 边界：Release Formation 引用已验证 Candidate 的实际 Artifact Identity，不得重新 Build"差不多的"产物（Ch7 §9）；Release Decision ≠ Delivery Authorization（§19）；Delivery Authorization 不是永久通行证（§29-30）；Deployment Result ≠ Target Validation Result（§37）；Environment Current Runtime State ≠ Accepted Current Release（§63）；旧 Intent 的异步 Action 不得覆盖被新 Intent 接管的 Target（§114-116）。  
> 与 SP-13 / SP-14 / SP-16 / SP-17 / SP-18 的分工：SP-14 **生产** Artifact Identity 与 Materialization Delta 事实；SP-13 判定 Candidate Acceptance 与 Evidence Applicability 重评；本规程**引用**身份形成 Release 并控制交付执行；Target Validation 语义、Validation Maturity、Target Release Completion 与 Accepted Current Release 归 **SP-17**；Feature Exposure / Launch 细节归 **SP-16**（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5）；Recovery 执行细节归 **SP-18**（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5；本规程负责 Recovery 触发识别、Decision 输入与 Anchor 真实性核验；SP-18 落地前，Recovery 执行按 Ch7 §89-102 正文直接执行，本规程代行其执行记录义务）。  
> 结构化镜像：`第五篇-SP15-ReleaseDeployment-OperationContract.yaml`

---

# 1. Trigger

```text
A. Accepted Candidate 需要进入交付准备——Release Formation
B. 需要对某个明确 Delivery Target 作出 Release Decision / Delivery Authorization
C. Delivery Authorization Revalidation Trigger 触发——既有授权适用性需要重判（§30）
D. 执行 / 重试 Deployment Attempt，或执行 Rollout Slice 推进 / 暂停
E. Deployment / Rollout / Validation / Recovery 中发现 Delivery Finding
F. 怀疑 Outcome Unknown、Stale / Superseded Intent 或并发交付冲突
G. SP-17 Target Validation Assessment 到达（FAILED / NOT_READY）→ Proceed 控制、
   Finding 分类与 Recovery 评估
```

红线：**Release Formation 不得重新 Build 任意内容**（§9）——引用 SP-14 已验证身份，或把新产物退回 SP-13 / SP-14 走新 Candidate。

不触发本规程的情形：

```text
Candidate 形成 / 绑定 / Acceptance          → SP-13
Build / Artifact Identity / Provenance      → SP-14
Target Validation 判定 / Release Completion → SP-17（本规程提供 Deployment 事实与 Observation）
Feature Flag / Launch 暴露面变化的设计与执行 → SP-16（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5；§86-87；本规程把它当 Target-changing Action 管）
Recovery 动作的执行与演练                    → SP-18（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5；本规程提供 Trigger / Decision / Anchor）
项目级 Current 更新                          → SP-19（Runtime State 事实由本规程维护，见 §9）
```

---

# 2. 输入

```text
Accepted Candidate            SP-13 输出：Candidate Revision + Acceptance Scope +
                              Verification Basis Revision + Evidence Set（§143 接口）
Artifact Identity 清单         SP-14 输出：可引用的 Digest 级身份 + Promotion 记录 +
                              Materialization Delta 处置状态
Deployment Definition          EA-12：target-scoped deploy workflow / IaC / script 的明确 Revision
Delivery Target 定义           明确 Target Scope（§20-22）；Target Readiness 输入（§25-26）
Ch4 设计约束                   Transition Invariant、Rollout / Recovery Direction、
                              Feature Exposure 设计（§87、§143 接口）
Risk / Policy                  授权自动化程度（§24 同旨）、并发策略（§117）、
                               Rollout 必要性（§47）、Representativeness 要求（§55）
Recovery Anchor 候选           previous accepted release / verified old artifact digest /
                               data restore point / stable traffic pool（§93）
既有 Delivery Authorization    Trigger C 时的授权记录 + Basis（§28）
Target Validation Assessment（条件）  SP-17 输出：Slice / Attempt / Target Scope 级
                              SATISFIED / FAILED / NOT_READY 判定——FAILED 到达时
                              Proceed = STOP，进入 Finding 分类（A11）/ Recovery 评估（A12）
```

入口再挑战义务（B1 系统性规则）：上游移交中的门禁归零归类——SP-14 的"same artifact / 可继承"声明、SP-13 的 ACCEPT_WITH_EXCEPTION 例外记录、Target Readiness 各项的 N-A / 已就绪声明——必须携带可解析的依据或证据指针；无依据的归零归类退回来源规程，不得在本规程内被当作既成事实消费。

---

# 3. 输出

```text
Release Baseline              Release Identity（不可变）+ 成员引用（Artifact Identity /
                              Migration / Contract / Config / Deployment Definition Revision）
                              + Candidate Evidence Set 引用（§12-16）
Release Decision Record       复用 Ch1 Decision 机制；绑定 Release Revision（§18）
Delivery Authorization        按 Target Scope：Authorization + Basis（可追集合）+
                              Applicability 边界 + Revalidation 条件（§23-31）
Deployment Attempt Record     Attempt Identity 8 字段 + 逐步执行事实（§33-36）
Environment Deployment Record Target 级部署事实（§36）
Rollout Record                Slice 序列 + Observation + Proceed / Pause 决策 + 依据（§46-59）
Environment Current Runtime State
                              真实运行事实（含 Mixed State），及时更新（§60-64）
Deployment Observation Record 部署观察事实，供 SP-17 做 Target Validation（§65）
Delivery Finding 记录          分类 + Return Path + Owner（§103-110）
Recovery Decision 输入         Trigger + Actual State + Recovery Anchor 核验结果 +
                              路径建议（§91-97）→ SP-18
```

**不输出**：

```text
Target Validation 结论 / Target Release Completion   → SP-17
Accepted Current Release 更新                         → SP-17（Completion 后经 Ledger，§82-83）
Candidate Acceptance / Evidence Applicability 结论    → SP-13
新 Artifact Identity                                 → SP-14
Feature Exposure 策略细节                             → SP-16
Recovery 执行与 Recovery Validation 结论              → SP-18 / SP-17
项目级 Current 更新（Design / Structure / Calibration / Closure）
                                                    → SP-19（Environment Current
                                                      Runtime State 由本规程维护，见 §9）
```

---

# 4. 核心语义

**Release Formation（§8-11）**：Release Baseline 引用 Ch6 已验证 Candidate 的实际 Artifact / Member Identity——Same Artifact Promotion（§139 [SHOULD]）。**禁止**"Release 前重新 Build 一个差不多的产物并声称其已验证"（§9）。Signing / Packaging / Wrapping 产生的 Materialization Delta 按 SP-14 A7 评估：内容身份未变 → 记录继承依据；产生新 executable / package identity → 必须回 SP-13 重评 Evidence Applicability，"只是打包"不是免检理由（§10-11 [BASELINE]）。

**Release Baseline（§12-17）**：≠ Candidate Baseline（§13）≠ Deployment Record（§14）。Release Identity 不可变，不得无痕改指（§15）；成员间 Coherence 必须核验（§16）；Formation Scope 由交付需要决定，不存在全局固定环境链（§17）。

**Release Decision ≠ Delivery Authorization（§18-19）**：Release Decision 回答"这个 Release Baseline 是否成立"；Delivery Authorization 回答"这个 Release 现在可以进这个 Target 吗"。后者是 Decision Point，**不等于人工审批**（§24）——可按风险自动化；但自动化不改变语义要求。

**Delivery Authorization Basis / Applicability / Revalidation（§28-31）**：授权依据必须是一个可追的集合（Candidate Accepted 状态、Target Readiness、风险与策略前提等，§28 [BASELINE]）。授权**适用性独立于授权存在**（§29 [BASELINE]）：Basis 中任一前提失效即触发重判——§30 八个 Revalidation Trigger：Release Baseline / Candidate 变化、Target Current Runtime / Migration State 材料变化、Target Readiness 条件变化、Freeze / Policy / Change Window 变化、Known Exception 过期 / 变化、Critical Dependency / Capacity 变化、**Recovery Anchor 不可用**、同边界另一 Target-changing Change。本规程增补一项：相关 Delivery Finding 到达同样触发重判（规程级扩展，登记于组基线索引）。重判可以是自动化的，不必然等于重新人工审批（§31）。

**Deployment Attempt 与步骤控制（§33-45）**：Attempt ≠ Release（§34）；每次 Attempt 有独立身份（§35），同一 Release 可多次 Attempt，不得覆盖旧失败记录（§111）。Deployment Step 应尽量 Idempotent（§39）；非幂等步骤必须可 Reconcile（§40 [BASELINE]）。Outcome Unknown 时**必须先确认实际 Target State**，不得对非幂等步骤盲目 Retry（§42-43 [BASELINE]）；Retry 形成可追事实（§45）。Deployment Result ≠ Target Validation Result（§37）——部署工具 SUCCESS 不证明目标达成。

**Rollout（§46-59）**：不是每个 Deployment 都需要 Rollout（§47）。Rollout Slice ≠ Candidate Scope（§49-50 [BASELINE]）；Slice 需要独立 Observation 与 Signal Attribution（§51-53 [BASELINE]）——**聚合指标可能掩盖 Canary 失败**（§54），必须按 version / cohort 分解；Representativeness 不足时结论降级（§55）；不规定固定百分比 / 时间（§56）。Proceed 决策基于 Ch4 Invariant + 该 Slice 的 Target 证据，而不是计时器（§57）；Pause 是正常状态（§58）；并发 Rollout 的信号污染必须显式归因或降级（§59、§120-121）。

**Environment Current Runtime State（§60-65）**：是 Target 的**实际运行事实**，随 Deployment 及时更新（§61）；Mixed State（如 5% 1.9 / 95% 1.8）是合法 Current Fact（§62）；它**不等于** Accepted Current Release（§63），Runtime Fact ≠ Release Completion（§64）。Deployment Observation Record（§65）是 SP-17 Target Validation 的事实来源。

**Ordering / Generation / Authority（§112-118）**：旧 Attempt 不得在新 Release 部署后因延迟完成把 Target 无声覆盖回旧版本（§112）。Target Deployment Generation（§113 [BASELINE]）表达 Intent 的 Supersession 关系；Target Change Authority Token（§114 [BASELINE]）约束**一切 Target-changing Action**——包括 delayed rollback、automated recovery、traffic revert、feature disable——执行前必须确认未被更新的 Intent supersede；被 supersede 的 Outdated Attempt 即使晚完成也不能成为 Desired State（§116）。同一边界内的并发交付按风险明确 Ordering / Isolation / Coherence（§117），但不强制全局 Single Deployment（§118）。

**Delivery Finding（§103-110）**：交付各阶段发现的问题按 Return Path 分十类（§104）：Release Baseline / Packaging、Candidate Defect Discovered in Target、Deployment Process Defect、Target Environment / Infrastructure、Migration / Data、Rollout / Transition、Validation Evidence Gap、External Dependency、Requirement / Design / Impact Gap、Unknown。**Candidate Defect Discovered in Target 必须重新评估 Candidate disposition**（§105）；Target 环境失败不自动意味着 Candidate Reject（§106）；Validation Evidence Gap = Target Validation NOT_READY，高风险场景不得因"看起来没事"推进（§110）。

**Recovery 入口（§89-97）**：Recovery ≠ Rollback（§90，候选路径八类）；Recovery Decision 基于当前 Actual State + Failure / Unknown Evidence + Ch4 Recovery Direction + Data / Contract Compatibility + 可用 Safe State（§92 [BASELINE]）。Recovery Anchor **必须真实存在**（§94 [BASELINE]）——事故发生时才发现旧 Artifact 已删 / Schema 不兼容 / 没备份是不可接受的；Binary Rollback 必须检查 Data / Contract Compatibility（§95：Artifact rollback ≠ System rollback）；Rollback / Rollforward 无全局固定选择（§96）；Forward Fix 产生新软件内容原则上回 Ch5 → Ch6 再 Delivery，Emergency 走 Ch8 压缩路径 + 强制后补对账（§97）。Recovery Attempt 可追（§98 九字段中，本规程开立除 Validation 外的八字段——Validation 归 SP-17）；**Recovery Command SUCCESS ≠ Recovery Complete**（§99）；失败 Attempt / Partial State / Recovery 都是历史工程事实，不得删除（§102）。

---

# 5. Engineering Actions

## A1 — Release Formation 入口核验

确认 Trigger A 成立：Candidate 已 ACCEPT / ACCEPT_WITH_EXCEPTION（SP-13，例外记录可见）；Acceptance Scope 覆盖本次 Release 意图；SP-14 移交的 Artifact Identity 清单可解析。Formation Scope 显式声明（§17：进哪些 Target 由交付需要决定，无固定环境链）。不满足任一条件，退回来源规程。

## A2 — 组成 Release Baseline

引用（而非重建）SP-14 身份组成 Release Baseline：Artifact Identity、Migration（如 V203）、Contract 版本、Config Schema / Profile、Deployment Definition Revision、Candidate Evidence Set 引用（§123 形态）。核验成员间 Coherence（§16）；签发不可变 Release Identity（§15）。消耗 SP-14 的 Materialization Delta 处置：凡"产生新身份"项，确认 SP-13 重评结论已回录，否则 Formation 不得完成（§11）。

## A3 — 作出 Release Decision

复用 Ch1 Decision Point / Record / Authority 机制，对 Release Baseline 作出成立 / 不成立决策，绑定 Release Revision（§18-19）。Release Decision 通过 ≠ 任何 Target 可交付。

## A4 — 作出 / 重判 Delivery Authorization

对每个目标 Delivery Target：

```text
1. 收集 Target Readiness 事实（§25-26 候选 Concern，按适用性，无全局固定 Checklist §27）
2. 组成 Authorization Basis：Candidate Accepted 状态 + Release Baseline Coherence +
   Target Readiness + 容量 / 依赖 / 数据兼容前提 + 无冻结窗口等（§28）
3. 作出 Authorization Decision（§23-24；自动化程度由 Risk / Policy 定）
4. 登记 Applicability 边界与 Revalidation 条件（§29-30）
```

Trigger C（§30 八类触发之一发生）时：重判既有授权适用性——依据仍成立则显式延续（记录判断），否则授权失效回到决策点。重判可自动化（§31）。

## A5 — 核验 Release Entry Condition

部署前核对 §32 八项入口条件下限：Release Baseline、Delivery Target、Delivery Authorization、Target Readiness、Deployment Definition、Rollout Strategy / Direction、Target Validation Requirement、Recovery Direction。本规程在此基础上增补四项核验：并发 / 冲突已判定（§117-118）、Known Exception 受控、人员 / 自动化责任明确、Observation 可用（规程级增补，登记于组基线索引）。**Recovery 前提可用 = Recovery Anchor 真实性已核验**（§94）。

## A6 — 执行 Deployment Attempt

签发 Attempt Identity（§35 八字段：Attempt ID / Release Baseline / Delivery Target / Deployment Definition Revision / Target Config Reference / Migration·Transition Phase / Started At / Executor·Actor；示例中的 Strategy / Starting Accepted Release 为 WorkOrder 场景扩展，§125）。按 Deployment Definition 执行；每步记录结果（§38、§41）；产出 Environment Deployment Record（§36）。重试同一 Release 时签发新 Attempt，旧记录保留（§111）。

## A7 — 控制 Deployment Step 与 Unknown 结局

步骤设计优先幂等（§39）；非幂等步骤登记 Reconcile 路径（§40）。任何步骤结局 Unknown（timeout / controller crash / partial migration）：**禁止直接 Retry**——先 inspect 实际 Target State，Reconcile 后再决定 resume / retry / recovery（§42-44、§119、§134 反例）。Retry 形成可追事实（§45）。Deployment Result 记录与 Target Validation 结论分离移交（§37）。

## A8 — 执行 Rollout

按 Risk / Policy 判定是否需要 Rollout（§47）。需要时：定义 Rollout Scope 与 Slice 序列（§48-50，Slice 构成独立记录）；每 Slice 配 Observation 计划（§51）与 Canary / Control 对比（§52）；指标按 version / cohort 分解，拒绝只看全局平均（§53-54）；Representativeness 不足的 Slice 结论降级或延长观察（§55-56）。每个 Proceed 决策记录依据：Ch4 Invariant 保持 + 该 Slice Target 证据（§57）；Pause 正常化记录原因（§58）。发现信号归因冲突（并发 Rollout / 配置变更污染）→ 隔离、分解、暂停其一或降级为 NOT_READY（§59、§120-121）。

## A9 — 维护 Environment Current Runtime State

每次 Target-changing Action 后及时更新 Target 的 Current Runtime State（§60-61）：Mixed State 如实记录（§62）；明确它不是 Accepted Current Release（§63）、不是 Release Completion（§64）。产出 Deployment Observation Record 移交 SP-17（§65）。

## A10 — 执行 Ordering / Generation / Authority 控制

为每个 Material Delivery Target 维护 Target Deployment Generation（§113：单调号 / GitOps commit / lease / lock 均可）。**任何 Target-changing Action（含 delayed rollback、automated recovery、traffic revert、feature disable）执行前确认 Authority Token 未被 supersede**（§114-115）；发现 Outdated Attempt / Action，阻止其生效并记录（§116）。同一边界并发交付按 §117-118 判定 Ordering / Isolation。

## A11 — 分类 Delivery Finding 并路由

交付链路各环节发现的问题按 §104 十类归类，携带证据与 Owner，按类路由：

```text
Release Baseline / Packaging        → 回 Release Formation（A2）或 SP-13（§108）
Candidate Defect Discovered in Target → 重新评估 Candidate disposition → SP-13 / SP-06 /
                                      SP-05 / SP-04（§105，禁止只记 "Deployment Failed"）
Deployment Process Defect           → 修 Deployment Definition（EA-12），并判断是否
                                      改变 Release / Candidate Evidence Applicability（§107）
Target Environment / Infrastructure → 修 Target → 可 redeploy same Release（§106、§133）
Migration / Data Failure            → 先判 Implementation / Design / Data Assumption /
                                      Target-only / Unknown，再路由（§109）
Rollout / Transition Failure        → Rollout 控制（A8）/ Ch4 Transition 设计
Validation Evidence Gap             → SP-17：Target Validation NOT_READY（§110）
External Dependency                 → 隔离 / 降级，按 SP-09 域处理（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，
                                      组4；落地前按 Ch3 / Ch5 依赖治理正文执行）
Requirement / Design / Impact Gap   → SP-05 / SP-04 / 需求权威
Unknown                             → 保留待查，禁止编造分类
```

## A12 — Recovery 触发识别与 Decision 输入

识别 §91 Recovery Trigger（部署步骤失败 / Target Validation FAIL / Invariant 破 / Canary 坏 / 数据不符 / 安全问题 / 关键依赖 / SLO 风险 / Operator 决策）。组织 Recovery Decision 输入（§92）：当前 Actual State（A9 的运行时事实）+ Failure / Unknown Evidence + Ch4 Recovery Direction + Data / Contract Compatibility 核验（§95）+ Recovery Anchor 真实性核验结果（§94）。路径选择无全局固定（§96）；Forward Fix 产生新软件内容的，标记回 SP-06 / SP-13 链或 Ch8 压缩路径（§97）。Recovery Attempt 事实框架（§98 九字段中除 Validation 外的八字段）由本规程开立，**执行细节归 SP-18**；Recovery Command SUCCESS 不视为完成（§99），Recovery Validation 与恢复后 Accepted Current Release 判定归 SP-17 / SP-18（§100-101）。失败历史一律保留（§102）。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| A1 Formation 入口核验 | Guardrail（Acceptance / Scope / Identity 机械核对）+ B1 再挑战 |
| A2 组成 Release Baseline | Automation + Guardrail（引用而非重建机械强制） |
| A3 Release Decision | Decision Point（复用 Ch1 机制；自动化程度按 Risk） |
| A4 Delivery Authorization | Decision Point + Policy（≠人工审批；重判可自动化） |
| A5 Entry Condition | Guardrail（八项核对；Anchor 真实性留证据） |
| A6 执行 Attempt | Automation（EA-12 执行）+ Guardrail（Attempt 身份签发） |
| A7 Step / Unknown 控制 | Guardrail（Unknown 禁止盲重试机械）+ Engineering Decision（Reconcile） |
| A8 Rollout | Engineering Decision + Guardrail（Slice 观察 / 归因红线机械） |
| A9 Runtime State | Automation + Guardrail（及时性与 Mixed State 诚实） |
| A10 Authority / Generation | Automation + Guardrail（supersede 检查机械） |
| A11 Finding 分类路由 | Engineering Decision（工具可建议分类） |
| A12 Recovery 入口 | Engineering Decision + Guardrail（Anchor 核验 / 兼容性检查红线） |

Hard Gates：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST NOT][BASELINE] G-SP15-01 Release Formation 重新 Build"差不多的"产物并声称其已验证
                     （§9）；身份引用只能来自 SP-14，新产物回 SP-13 / SP-14
[MUST][BASELINE]    G-SP15-02 Materialization 产生新 executable / package identity 的，
                     SP-13 重评结论未回录前 Release Formation 不得完成（§10-11）
[MUST][BASELINE]    G-SP15-03 Release Identity 一经发布不得无痕改指；要改就新 Revision（§15）
[MUST][BASELINE]    G-SP15-04 授权 / Attempt / 完成声明必须带显式 Target Scope（§22、§81 同旨）
[MUST][BASELINE]    G-SP15-05 Delivery Authorization 适用性受 §30 触发约束；旧授权不得
                     被当作永久通行证（§29-30、§140）
[MUST NOT][BASELINE] G-SP15-06 Outcome Unknown 时对非幂等步骤盲目 Retry——先确认实际
                     Target State 再 Reconcile（§42-44）
[MUST][BASELINE]    G-SP15-07 Rollout Proceed 依据 Ch4 Invariant + Slice 级 Target 证据；
                     聚合指标不得掩盖 Slice 失败；计时器不作为充分依据（§54、§57）
[MUST][BASELINE]    G-SP15-08 Environment Current Runtime State 如实及时更新；Mixed State
                     合法且不得冒充 Accepted Current Release（§60-64）
[MUST][BASELINE]    G-SP15-09 一切 Target-changing Action 执行前确认 Authority Token 未被
                     supersede（含 delayed rollback / traffic revert / feature disable）（§114）
[MUST][BASELINE]    G-SP15-10 Delivery Finding 必须按十类分类并路由；Candidate Defect
                     Discovered in Target 必须触发 Candidate disposition 重评（§104-105）
[MUST][BASELINE]    G-SP15-11 依赖某 Recovery Anchor 前必须核验其真实存在；Binary Rollback
                     前必须检查 Data / Contract Compatibility（§94-95）
[MUST NOT][BASELINE] G-SP15-12 删除失败 Attempt / Partial State / Recovery 历史（§102、§111）
[MUST][BASELINE]    G-SP15-13 上游门禁归零归类（same-artifact 声明 / 例外记录 / Readiness
                     N-A）必须携带可解析依据并可被再挑战（B1）
```

---

# 7. PASS Exit

```text
[ ] Release Baseline 由已验证身份引用组成，Identity 不可变，Coherence 已核验
[ ] Materialization Delta 全部处置完毕（继承依据已记录 / SP-13 重评结论已回录）
[ ] 每个目标 Target 的 Delivery Authorization 存在、Basis 可追、Applicability 边界显式
[ ] Attempt / Rollout 记录完整（身份、步骤、Slice、Proceed / Pause 依据）
[ ] 无未处置的 Outcome Unknown；非幂等步骤 Retry 均有 Reconcile 前置事实
[ ] Environment Current Runtime State 与实际一致且及时；Observation Record 已移交 SP-17
[ ] Delivery Finding 全部分类路由；Candidate Defect 类已触发 disposition 重评
[ ] Authority / Generation 控制生效，无 Outdated Action 生效事件
```

**完成不代表**：Target Validation 通过（SP-17）/ Target Release Completion（SP-17）/ Accepted Current Release 更新（SP-17）/ Feature 已暴露（SP-16，pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕）/ Recovery 完成（SP-18，pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕）/ Change 关闭或任何项目级 Current 更新（SP-19）。

---

# 8. Evidence

Evidence by Work：Attempt 记录、GitOps commit、流水线运行、平台部署记录、监控 / 仪表盘截图数据的天然载体是 CD 平台、GitOps 仓库、可观测系统（EA-12 / EA-15）。必须显式产生的：

```text
- Authorization Basis 记录与 Applicability / Revalidation 登记
- Authority Token 确认事实（每次 Target-changing Action）
- Rollout Proceed / Pause 决策依据（Slice 级证据引用）
- Delivery Finding 分类记录（含 Candidate Defect 类的 disposition 重评指针）
- Recovery Anchor 真实性核验记录与 Data / Contract Compatibility 检查结论
- Outcome Unknown 的 Reconcile 事实链（inspect → reconcile → 决策）
```

---

# 9. Current Update Obligation

```text
writesCurrent: environment-current-runtime-state-only
```

Release / Deployment 产生的是事实与决策记录：Release Baseline、Authorization、Attempt、Runtime State。其中 **Environment Current Runtime State 是 observed-fact Current**——Ch9 §33 列为 Baseline Kind，§35 明确 Runtime Current 在执行期即记录、不等待 Change Closure——本规程在 Authority 背书下于执行期提交它；SP-19 只核验该 Commit Fact，不重复提交。它**不等于** Accepted Current Release（GI-05：Accepted ≠ Observed）——Accepted Current Release 的 Ledger 迁移发生在 Target Release Completion，归 SP-17；项目级 Current（Design / Structure / Calibration / Change Closure）提交统一走 SP-19。Merge / Deploy 均不等于项目级 Current 更新。

---

# 10. FAIL / Return Path

```text
Release Formation 身份缺口        → SP-14 补身份 / Delta 评估；新产物回 SP-13
Authorization Basis 前提失效       → 授权失效，回 A4 重判；必要时回 SP-13 / SP-05
Deployment 步骤失败               → A11 分类：Process Defect 修 EA-12；Environment
                                    修 Target 后可 redeploy same Release（§106）
Outcome Unknown                  → 先确认实际 Target State（§42-44），禁止盲重试
Rollout Slice FAIL               → Proceed = STOP；Finding 分类路由（A11）；
                                   需要恢复 → A12 → SP-18
Candidate Defect in Target       → 重评 Candidate disposition → SP-13 / SP-06 / SP-05（§105）
信号归因失败                      → 隔离 / 分解 / 暂停其一 / 降级 NOT_READY（§120-121）
Stale / Superseded Action        → 阻止生效，记录事件，审计 Authority 机制（§116）
```

---

# 11. Exception / Alternative Path

## 11.1 无 Rollout 的 Deployment

低风险 / 无流量渐变价值的交付可不经 Rollout 直接部署（§47）：A8 退化为一行必要性判断记录，Observation 与 SP-17 验证语义不豁免。

## 11.2 Client / Mobile / Firmware 交付

无服务端 Environment 的交付形态用 Distribution Record / Channel / Cohort / Installation / Adoption Observation / Version Exposure / Withdrawal Record 实现同类语义（§88）；禁止为形式伪造服务端 Environment 记录。Exposure 面变化的细节仍归 SP-16（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5）。

## 11.3 Feature Exposure 变化按交付动作处理

Flag off→on、流量 0%→100% 等会 materially 改变用户行为的变化，按 Target-changing Delivery / Rollout Action 走本规程的 Authority / Observation / Rollout 控制（§86-87）；Flag 设计与生命周期归 SP-16（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5）/ SP-05。

## 11.4 Emergency

Ch8 fast-path 可压缩授权等待与 Rollout 节奏（§144 接口），但 Authorization Basis 可追、Authority Token 确认、Unknown 不盲重试、Finding 分类、历史保留不豁免；Forward Fix 走压缩路径的强制事后对账（§97）经 SP-21（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5）/ SP-19 补齐。

---

# 12. Theory Trace

```text
第一篇  GI-03 / GI-05 / GI-13；Ch1 Decision Point / Record / Authority / Ledger 机制
第二篇  Build / Release WHAT 边界（Ch7 §2）；Deploy ≠ Release ≠ Launch（§86）
第三篇  Runtime / Deployment WHERE（Ch7 §3）
第四篇  Ch7 §97（Forward Fix 回 Ch5 / Ch6 链）；
        Ch7 §10-11（Materialization Delta 重评 Evidence Applicability；
        Ch6 §10-11 同旨于成员身份绑定）、Ch7 §143 / Ch6 §142
        （Candidate Accepted ≠ Release Authorized ≠ Deployment Complete ≠
        Production Validation）；
        Ch7 §8-22（Formation / Baseline / Decision / Target）、§23-32（Authorization /
        Basis / Applicability / Revalidation / Entry Condition）、§33-45（Attempt /
        Step / Unknown / Reconciliation / Retry）、§46-59（Rollout）、§60-65
        （Runtime State / Observation Record）、§86-88（Exposure / Client Distribution
        边界）、§89-102（Recovery 入口语义）、§103-121（Finding / Ordering /
        Generation / Authority / Concurrency / Attribution）、§139-140（Minimum
        Requirements 与 Authorization Applicability MUST-BASELINE）；
        Ch8（Emergency 压缩，§144）；Ch9（Calibration 边界，§145）
```

Theory Trace 只说明受哪些理论约束；本规程不复制理论正文，不成为第二份 Authority。

---

# 13. Executable Asset References

```text
EA-12 Deployment Definition   target-scoped deploy workflow / IaC / script 的载体与 Revision
EA-13 Environment / Secret    Target 接入与密钥注入（Secret 不进任何 Baseline / Record）
EA-15 Observability           Slice 级信号、按 version / cohort 分解的指标能力（§53-54）
EA-16 Recovery                rollback / forward / repair script；Recovery Anchor 的物质载体
```

工具适合：执行 Deployment / Rollout、签发与检查 Generation / Authority Token、采集与分解信号、更新 Runtime State、保留历史。工具不适合：Release / Authorization 决策结论（低风险可自动）、Finding 分类结论、Recovery 路径选择、Anchor 真实性判断、"看起来没事"式的推进判断。

---

# 14. Reference Profile Bindings

```text
通用层        Operation Contract / Theory Trace / Evidence 语义 / Control 语义——全 Profile 共用
Delivery Shape  决定 Target 形态与 Attempt / Record 形态（服务端 Environment 记录 vs
                Client Distribution Record，§88）；决定 Rollout 机制有无（§47）
Risk Overlay    决定授权自动化程度（§24/§31）、并发策略严格度（§117）、
                Representativeness 与 Observation 要求（§55）、Recovery Anchor 要求深度
```

具体 Profile 绑定在组6 RP 补齐时登记；本规程不预留学生位。

---

# 15. Example

**CHG-WO-142 / Release WO-1.9.0 交付——接 SP-14 示例，引 SP-17 / SP-18。**（本示例走 Ch7 §122-138 WorkOrder 的 Canary FAIL 分支；同一 Change 在 Ch9 §84 / SP-19 示例中走 Validation PASS 分支——两个分支各自忠于其理论源，阅读时以各自篇章的分支设定为准。）

A1-A2：SP-13 移交 ACCEPT(C2)（成员：backend image `sha256:9f2c…`、migration V203、contract C9、search config S5、config P2）；SP-14 移交身份清单与签名信封 Delta 的"可继承"依据。Release Formation 组成 WO-1.9.0 Baseline：上述成员 + Deployment Definition DD8 + C2 Evidence Set 引用——**全部引用，不重建**（§9、§123）。

A3-A5：Release Decision 通过。对 Production-US 作 Delivery Authorization：Basis = {C2 accepted、Baseline coherent、target production-us、容量足够、数据库 expand 兼容、必需可观测就绪、**previous safe artifact (v1.8) 保留——Recovery Anchor 核验通过**、无冻结}（§124）。授权登记 Applicability 边界。

A6-A9：Attempt D1（release WO-1.9.0 / target Production-US / strategy canary / starting accepted 1.8.0，§125）。Slice S1 = 5% 流量跑新产物：Current Runtime State 如实记为 **mixed 1.8 / 1.9**，Accepted Current Release 仍为 1.8（§126、§62-63）。观察按 version / cohort 分解（§127）。

A11-A12：S1 上 new version transfer error material、old version 正常 → 形成 Delivery Finding：**Candidate Defect Discovered in Target**（非 "Deployment Failed"），触发 C2 disposition 重评 → 修复走 SP-06 → C3 → SP-13 重验（§132）。Recovery Decision：核验 v1.8 仍能读取 expanded schema / data（§95）→ 路径 = traffic revert + artifact rollback，Recovery Anchor = verified v1.8 digest。Recovery Attempt R1：traffic → stable pool、artifact → v1.8、migration expand 保留、backfill pause——因为 schema expand 本身 backward compatible，**不需要 destructive rollback**（§129-130）。执行归 SP-18；Recovery Validation 与"Accepted Current Release 保持 1.8"判定归 SP-17（§131）。

反例对照：

```text
若 Canary 健康但 Production-US 节点配额耗尽 → Target Environment Finding，
不 Reject C2；修 Target 后 redeploy same Release（§106、§133）
若 V203 执行器 timeout 结局 Unknown → 禁止直接 Retry V203；先查 schema /
migration table 实际状态，Reconcile 后再定 resume / retry / recovery（§43、§134）
若 D1（1.9）与 D2（1.10）并发、D2 先完成、D1 延迟任务后完成 → 无 Generation
控制时 Production 被无声降回 1.9；有 Target Deployment Generation 时 D1 已
superseded，不能成为 Desired State（§112-116、§135）
Multi-target：US accepted = 1.9 后 EU 仍可 accepted = 1.8——不同 Target Scope
各自的 Current Reality，不是矛盾（§84、§136；Completion 判定归 SP-17）
```

---

# 16. 最终原则

> **交付规程的全部意义在于目标环境事实的真实性：被授权的、被部署的、被观察的必须指向同一个可辨认的 Release；授权不是永久通行证，部署成功不是目标达成，聚合绿色不是 Slice 真相，rollback 命令成功不是系统恢复。旧意图不得覆盖新现实，失败历史不得被删除，恢复锚点必须在依赖它之前真实存在。Release 一旦形成身份即冻结，Target 一旦变化事实即更新——其余一切，交给验证与恢复各自的规程去判断。**
