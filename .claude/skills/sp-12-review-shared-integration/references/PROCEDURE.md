# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-12 Review / Shared Integration Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-31：组3 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1050 处引用核验 PASS AFTER REPAIR（备注级）；证据见组3 审计报告与横向回归报告）  
> 单一职责：把一个 Review-ready Implementation Unit 受控地送进 Shared Integration Baseline——组织绑定 Revision 的 Work Product Review，选择并获取足够新的 Integration-context Feedback，用受控机制安全集成 Incomplete Feature，对 Shared Baseline Breakage 先分类、定 Owner、以 Restore 优先，并如实产出 Integration Evidence。  
> 本规程是 SP-06 A10（Review 与 Integration 受控）的**专门化细则**：SP-06 在 Work Package 控制层声明 Review / Integration 的边界红线；SP-12 规定这两件事本身的执行规程。反馈运行、绑定、失效判断、失败分类的通用机制**复用 SP-11**（Ch5 §C），本规程只定义 Review 与 Integration 特有的语义（Ch5 §E）。  
> 边界：Review 是 Feedback，不是 Required Verification 全集；Integration ≠ Deployment ≠ Release；Shared Integration Baseline ≠ Accepted Current Release；Merge / Integration Green ≠ Candidate Accepted ≠ 任何 Current 更新。  
> 结构化镜像：`第五篇-SP12-ReviewSharedIntegration-OperationContract.yaml`

---

# 1. Trigger

```text
A. Implementation Unit 满足 Review-ready 候选条件，请求进入 Review
B. Review 通过（或按 Policy 豁免），请求进入 Shared Integration Baseline
C. 并发 Change 对相同 Material Boundary（Contract / Data / Source Boundary）产生变化，
   需要获取足够新的 Integration-context Feedback
D. Shared Integration Baseline 出现疑似 Breakage——需要分类、定 Owner、恢复
E. Review Finding / Integration Failure——需要分类并路由返回层
```

红线：**Merge ≠ Current Design Update**（§190，GI-05）——Source 进入 main 只说明 Source Fact 变化，Design / Structure / Contract / Data 的 Current 更新唯一通道是 SP-19。

不触发本规程的情形：

```text
Local / Pre-submit 反馈机制本身                      → SP-11
Candidate 形成 / Evidence Binding / Acceptance       → SP-13（Ch6）
Deployment / Release / Target 环境动作               → SP-15 / SP-17（Ch7）
Deviation / Drift 处置、Outputs Ready 判定           → SP-06
```

---

# 2. 输入

```text
Review-ready Implementation Unit    Revision 可解析；SP-11 移交的 Pre-submit
                                    Readiness Fact 与 Local Evidence 包
Review 对象全集                      按适用性：Source / Migration / Contract Definition /
                                    Config / Generated Change / Test / Build Definition（§154）
Reviewer 选择依据                    Ownership / Risk / Policy / Specialist Concern（§160）
Integration Context 定义             项目定义的 Shared Source / Build Context 形态
                                    （trunk / integration branch / protected merge result /
                                    merge queue result，§166）与 Context Freshness 政策
并发 Change 图景                     已知影响相同 Material Boundary 的在途 Change（§187）
Incomplete Feature 集成机制（适用）   Feature Flag / Inactive Code Path / Branch by
                                    Abstraction / Backward-compatible Contract /
                                    Internal-only Slice（§170），含 Ch4 Transition /
                                    Cleanup 设计依据（§171）
```

入口再挑战义务（B1 系统性规则）：SP-11 移交包中的 gate-zeroing 处置——optional 分类、reuse 依据、not-applicable 声明、Quarantine 与 Evidence Gap 处置——必须携带可解析理由；没有理由或理由不成立的，退回 SP-11 处置，不得带着未挑战的缺口进入 Review / Integration。

---

# 3. 输出

```text
Review Record                     Approval / Finding，绑定具体 Revision（§161）；
                                  Finding 带分类与 Return Path
Integration Record                Unit + Integration Context + 结果；
                                  Merge Result 作为 Feedback Subject 时的绑定（§188）
Integration Evidence              绑定 Integration Context 的反馈证据集（§193），
                                  供 Ch6 判断 Candidate 与当前开发上下文的组合正确性
Shared Baseline Health Fact       Buildable / Testable / Integrable / Traceable 状态（§168）；
                                  Breakage 记录（分类 + Owner + Restore 路径）
```

**不输出**：

```text
Candidate Accepted / Required Verification Satisfied   → SP-13（§194）
Release / Supported 版本状态                            → SP-15（§165）
Accepted Current Release                                → SP-15 / SP-17（§192）
任何 Current Design / Structure / Contract / Data 更新   → SP-19（§190-191）
Change State 变更（Breakage 不是 Change State）          → §173 / §300
```

---

# 4. 核心语义

**Review 的定位（§153-159）**：Review 是 Implementation Feedback，不是"所有行为正确"的证明，不是 Required Verification 全集（§288）；Review ≠ Test——Review 适合 read / reason / inspect，Dynamic Test 适合 execute / compare（§159）；即使 CI Green，Concurrency / Boundary / Semantic Compatibility / Complexity 问题仍需主动推理（§158）。Review 对象不只有 Code（§154）。

**Review-ready `[BASELINE]`（§155-157）**：已获得足够 Pre-submit Feedback、Output Set 基本同步、目的 / 设计依据 / 风险可被 Reviewer 理解的 Implementation Revision。最低候选条件：Build / Run works（适用）、Change-local Test passes、Static Check 无 Known Blocker、Contract / Migration / Config 已同步、无明显 secret / debug artifact、Description 解释 Why、Design / Work Package Trace 可解析（§156）。**Review 不应是编译错误的第一发现者**（§157）。

**Approval 绑定 Revision（§161-162、§289）**：对 R3 的 Approval 不自动覆盖 Material R4；Minor Revision 是否重新 Review 由 Policy / Materiality 决定——不要求每个 typo fix 都完整重审，但 minor / material 的划分是带理由的 gate-zeroing 判断。Reviewer 数量不固定，由 Risk / Ownership / Policy 驱动（§290）。

**Integration `[BASELINE]`（§163-167）**：把 Implementation Unit 与项目定义的 Shared Source / Build Context 组合成可共同构建、检查、继续开发的共享工程状态，并获取并发变化带来的真实反馈。Integration ≠ Deployment ≠ Release（§164-165）。不强制 Trunk-only（§167）；追求 frequent small integration，不是工具宗教。Shared Baseline 核心要求：Buildable / Testable / Integrable / Traceable（§168）。

**Context Freshness（§185-188、§294-295）**：不强制每个 PR 都 latest-main；Freshness 由 change rate / risk / merge queue / build cost 决定（§186、§295）。但已知并发 Change 影响同一 Contract / Data / Source Boundary 时，**必须**获取足够新的 Integration-context Feedback（§187、§294）。Merge Result 可以成为 Feedback Subject——绑定 synthetic merge M1 的 Status Check 比只测 R5 更有意义（§188）。

**Incomplete Feature 集成（§170-171、§293）**：Local Branch 可以不完整，但避免 Long-lived Divergence（§169）。Incomplete Feature 用受控机制（§170 清单）形成可集成中间状态；**Feature Incomplete 不得被当作 Shared Baseline 长期 Broken 的理由**（§293）；Feature Flag 必须服从 Ch4 Transition / Cleanup 设计，不能只为 merge easy 引入永久 Flag（§171）。

**Shared Integration Baseline Breakage `[BASELINE]`（§172-182、§291-292、§300）**：某次 Change / Integration Result 使共享基线在关键 Build / Check / Test / Integration Contract 上进入已知不可工作状态。Breakage 是 **scoped Baseline Condition / Finding，不是 Change State**（§173、§300）；与 Change Execution Condition 分离——不阻塞当前 Change 独立工作的 Breakage 不使 Change BLOCKED（§174）。判断是项目上下文相关的：任意 warning ≠ broken，看 critical shared capability（§175）。处置：优先目标是 **Restore Shared Baseline**（§176、§291）；Restore ≠ 一律 Revert——fix forward / revert / disable incomplete path / restore dependency / repair test·infra 按分类选择（§177、§292）；Product Defect 可以 Revert（§178）；**Infra Failure 不应该 Revert Product**（§179）；**Broken Test 修 Test，不得删正确产品行为凑绿**（§180）；Breakage 必须有 Owner（§181）；Broken Baseline 上继续堆 Change 会造成 Root Cause 混淆 / Defect 累积 / Feedback 失真（§182）。

**Integration Evidence（§193-194）**：可帮助 Ch6 判断 Candidate 是否已和当前开发上下文正确组合；但 Integration Green 仍 ≠ Candidate Accepted——Ch6 还要判断 Required Verification / Candidate Identity / Evidence Applicability。

---

# 5. Engineering Actions

## A1 — 确认 Review-ready

对照 §156 七项最低候选条件逐项核验，证据来自 SP-11 移交包（Pre-submit Readiness Fact + Local Evidence）。任一不满足 → 退回 SP-11 / SP-06，附带缺项清单。同时执行 B1 再挑战：移交包中的 optional 分类、reuse 依据、not-applicable、Quarantine / Gap 处置没有理由或理由不成立的，退回 SP-11。

## A2 — 组成 Review

按适用性确定 Review 对象全集（§154：不只是 Code——Migration / Contract / Config / Generated Change / Test / Build Definition 按触及面纳入）。按 Ownership / Risk / Policy / Specialist Concern 定 Reviewer 构成（§160）——数量不固定，但高风险面（Contract 语义、Data Migration、Security）必须有对应 Specialist 视角，缺席需登记理由。向 Reviewer 提供：Why（Description）、Design / Work Package Trace、SP-11 证据包。

## A3 — 执行 Review 并绑定 Revision

Reviewer 主动推理（§158），不以 CI Green 替代判断。每个 Review Finding 复用 SP-11 的九类分类并路由（实现缺陷回本层；Design 未定义的语义回 SP-05；新影响回 SP-04）。结论——Approval 或 Change-request——**绑定具体 Revision**（§161）。Review 后产生新 Revision：Material 变化 → Approval 适用性重新判断（§289）；Minor / Material 划分按 Policy 并记录理由（§162），该划分可被 SP-13 再挑战。

## A4 — 判定 Integration 路径与 Context Freshness

选择 Integration 形态（§166，工具无关）并回答：**当前 Integration Context 够新吗？** 不强制 latest-main（§186、§295）；但若已知并发 Change 触及同一 Material Boundary，必须先把 Context 推进到包含该变化、再获取 Integration-context Feedback（§187、§294）。Freshness 判断的依据（change rate / risk / 已知并发变化）写入 Integration Record。

## A5 — 执行 Integration 并获取 Integration-context Feedback

执行组合（rebase / synthetic merge / merge queue / integration branch），对 **Merge Result** 运行适用的 Integration-context Feedback——绑定 Merge Result 而非仅绑定分支 head（§188）。反馈运行、绑定、失效判断、UNRELIABLE / GAP 处置全部复用 SP-11 机制（A3-A7），本规程不另建。常见并发交互（Contract conflict / Dependency conflict / Data migration order / Generated artifact conflict / Behavior interaction，§184）逐项排查。

## A6 — 处置 Incomplete Feature 的安全集成

Feature 未完成但需集成时，确认使用 §170 受控机制之一，且：old behavior preserved、new path inactive、schema / contract 兼容、shared checks green。Feature Flag 必须能追溯到 Ch4 Transition / Cleanup 设计（退出语义 + Owner）；只为 merge easy 引入的永久 Flag 拒绝集成，退回 SP-05 / SP-06。Local Branch 的不完整是合法的；Long-lived Divergence 是风险，记录并推动分批（§169、§307 SHOULD）。

## A7 — 进入 Shared Baseline

进入前核验 Shared Baseline 核心要求（§168：Buildable / Testable / Integrable / Traceable）在 Integration Context 上成立。进入动作本身只是 Integration Record 的一条事实：**不更新任何 Current**——项目若定义 "main integrated = Development Current"，必须经对应 Baseline Transition Rule / Record 显式表达（§191），且该规则的执行归 SP-19 通道。

## A8 — 监控并处置 Shared Baseline Breakage

疑似 Breakage 时按序执行：

```text
1. 定性：是否关键 Build / Check / Test / Integration Contract 已知不可工作？
   任意 warning ≠ broken；看 critical shared capability（§175）
2. 定性为 Breakage → 建立 Breakage 记录（scoped Baseline Condition / Finding），
   不得创建新 Change State（§173、§300）
3. 分类来源：当前 Change / 并发 Change / Test / Dependency / Infrastructure（§173）
4. 指定 Owner（§181）
5. Restore 优先（§176）：按分类选 fix forward / revert / disable / restore
   dependency / repair test·infra（§177-180）
6. 判定与 Change Execution Condition 的关系：不阻塞独立工作的，Change 继续；
   关键 Work Package 无法获得可信 Integration Feedback 且别无路径的，
   走 Work Package Blocker / Change BLOCKED 规则（§174、§298）
7. Broken Baseline 未恢复前，阻止继续堆叠新 Change（§182）
```

## A9 — 分类 Integration Failure

Integration 失败的分类粒度（§189）：merge conflict / build fail / test fail / dependency fail / infra fail——各自 Return Path 不同；映射到 SP-11 九类后路由。Merge conflict 本身是 Integration Conflict / Context Change 类，走 Context Reconciliation，不是产品缺陷。

## A10 — 移交 Integration Evidence

向 SP-13 移交：Integration Record、绑定 Integration Context / Merge Result 的反馈证据、Breakage 与处置历史、Review Record（Revision-bound）。移交语义仅为"Candidate 与当前开发上下文的组合已有这些真实反馈"（§193）；Integration Green ≠ Candidate Accepted（§194）。向 SP-06 回送：A10 控制层所需的 Review / Integration 状态事实，供 Outputs Ready 判定引用。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| A1 Review-ready 核验 | Guardrail（七项清单机械）+ B1 再挑战 |
| A2 组成 Review | Engineering Decision + Policy |
| A3 执行 Review | Human Judgment（工具可呈现证据，不得代行 Approval） |
| A4 Freshness 判断 | Engineering Decision（并发图景可由工具提示） |
| A5 Integration 执行与反馈 | Automation + SP-11 机制 |
| A6 Incomplete Feature 集成 | Engineering Decision + Guardrail（§171 红线机械） |
| A7 进入 Shared Baseline | Automation + Guardrail（Current 红线机械） |
| A8 Breakage 处置 | Engineering Decision（分类 / Owner / Restore 选择）+ Guardrail（不建 Change State） |
| A9 失败分类 | Engineering Decision |
| A10 移交 | Automation + Guardrail |

Hard Gates：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST NOT][BASELINE] G-SP12-01 用 Review 替代 Dynamic Testing / Required Verification（§288）
[MUST][BASELINE]    G-SP12-02 Review / Approval 必须绑定 Revision；Material 新 Revision
                     后 Applicability 重新判断（§289/§161）
[MUST NOT][BASELINE] G-SP12-03 为所有 Change 规定固定 Reviewer 数（§290）
[MUST][BASELINE]    G-SP12-04 Shared Baseline 已知 Critical Breakage 优先恢复；
                     Restore 不得机械等同 Revert——按分类选择（§291/§292）
[MUST NOT][BASELINE] G-SP12-05 把 Feature Incomplete 当作 Shared Baseline 长期 Broken
                     的理由（§293）
[MUST][BASELINE]    G-SP12-06 并发 Change 触及同一 Material Boundary 时，必须获取足够新
                     的 Integration-context Feedback（§294/§187）
[MUST NOT][BASELINE] G-SP12-07 把 Merge / Integration 解释成任何 Current 更新（§190-191/§305，GI-05）
[MUST NOT][BASELINE] G-SP12-08 把 Shared Baseline Breakage 建成新 Change State（§173/§300）
[MUST NOT][BASELINE] G-SP12-09 为 Infra Failure Revert 产品代码；为 Broken Test 删除正确
                     产品行为（§179/§180；§292 [MUST][BASELINE] 同旨）
[MUST][BASELINE]    G-SP12-10 minor-revision 免重审、Context Freshness 裁剪、optional
                     继承等 zeroing 判断必须携带理由并可被 SP-13 再挑战（§162/§186 + B1）
```

---

# 7. PASS Exit

```text
[ ] Review Record 存在且绑定当前 Revision（或新 Revision 已按 §289 重判 / 重审）
[ ] Review Finding 全部分类并路由；无悬而未决的 Change-request
[ ] Integration Record 存在；Integration-context Feedback 对足够新的 Context 成立
[ ] Incomplete Feature（若有）经受控机制集成，Flag 可追溯到 Ch4 设计
[ ] Shared Baseline 无 Known Critical Breakage；或 Breakage 已有 Owner + Restore
    路径且与当前 Change 的执行条件关系已显式判定
[ ] Integration Evidence 已移交 SP-13；Review / Integration 状态事实已回送 SP-06
```

**完成不代表**：Candidate Accepted（SP-13）/ Release 或 Supported 版本成立（SP-15）/ Development Current 或任何 Current 已更新（SP-19）/ Change Done（SP-06 / SP-19）。

---

# 8. Evidence

Evidence by Work：Review Record、Integration Record、Status Check 的天然载体是 PR / CL 平台、Merge Queue、CI 与仓库规则（EA-05 / EA-06 / EA-07）。必须额外显式产生的只有：

```text
- Reviewer 构成依据（高风险面 Specialist 缺席理由）
- minor / material revision 划分理由（免重审时）
- Context Freshness 判断依据（已知并发变化清单）
- Breakage 记录（分类 + Owner + Restore 路径 + 与 Change 执行条件的关系判定）
- Feature Flag 的 Ch4 Transition / Cleanup 追溯指针
```

---

# 9. Current Update Obligation

```text
writesCurrent: false
```

本规程不更新任何 Current。Merge / Integration 只改变 Source Fact（§190）；项目自定义的 Development Current 推进必须经显式 Baseline Transition Rule / Record（§191），由 SP-19 通道执行。Shared Integration Baseline 的状态是 Baseline Health Fact，不是 Accepted Current Release（§192）。

---

# 10. FAIL / Return Path

```text
Review Finding          → SP-11 九类分类路由（本层修 / SP-05 / SP-04 / Requirement）
Material 新 Revision     → Approval 适用性重判（§289）；需要时重新 Review（§162）
Integration Failure      → A9 分类：conflict → Context Reconciliation；build/test fail →
                           SP-11 机制处置；dependency fail → SP-09 域；infra fail → 修基础设施
                           （Reconciliation 结论按 SP-06 §10 追加到 Change Record 的
                           Working Baseline 段——append-only 唯一追加点）
Shared Baseline Breakage → A8 七步（分类 → Owner → Restore 优先）
Material Base Change     → 重新获取 Integration-context Feedback（§187），
                           必要时重评 SP-04 / SP-05
```

---

# 11. Exception / Alternative Path

## 11.1 Minor Revision 免重审

Typo / 注释级变化可按 Policy 免完整重审（§162）；划分理由必须记录，且该记录可被 SP-13 / 事后审计再挑战。涉及 Contract / Data / Security 语义的一律不属 minor。

## 11.2 Small Change

小 Change 可将 Review-ready 核验、Review Record、Integration Record 折叠进单个 PR 流；语义项（绑定、分类、Breakage 红线）不省。

## 11.3 Emergency

Ch8 fast-path 可压缩 Review 广度与 Integration 等待，但 Approval 绑定 Revision、Breakage 处置、Current 红线不豁免；事后经 SP-21 / SP-19 对账补齐。

## 11.4 Merge Queue / 自动化形态

Merge queue、protected merge result 等形态（§166）等价合法；关键是 Feedback 绑定的是 **Merge Result** 而非仅分支 head（§188），且 Breakage Owner 制度不因自动化而消失。

---

# 12. Theory Trace

```text
第一篇  GI-03 / GI-05（Merge 不更新 Current）/ GI-13
第二篇  Implementation / Review / Quality WHAT；Build WHAT
第三篇  Source / Build WHERE；Shared Baseline 作为结构事实
第四篇  Ch5 §E 全节（§153-194）、§155-156（Review-ready）、§172-182（Breakage 语义）、
        §185-188（Freshness / Merge Result）、§288-295 / §298 / §300 / §305
        （MUST-BASELINE 要求）；Ch5 §C 通用反馈机制（经 SP-11 复用）；
        Ch5 §193-194（对 Ch6 的消费方接口；规范所有权属 SP-13）；Ch8（Emergency）
```

Theory Trace 只说明受哪些理论约束；本规程不复制理论正文，不成为第二份 Authority。

---

# 13. Executable Asset References

```text
EA-05 Change / PR Template    required fields 可用：Why / Trace / 风险声明
EA-06 Repository Rules        required checks enforced；Breakage 时阻止继续堆叠
EA-07 Reusable CI             Integration-context Feedback / Merge Result 绑定自动化
EA-08 Verification Harness    集成级 fixture 的确定性执行
```

工具适合：执行集成、绑定 Merge Result、强制 required checks、呈现并发图景。工具不适合：Review Approval、Finding 分类、Freshness 判断、Breakage 定性与 Restore 选择。

---

# 14. Reference Profile Bindings

```text
通用层        Operation Contract / Theory Trace / Evidence 语义 / Control 语义——全 Profile 共用
Delivery Shape  决定 Shared Baseline 形态与 Integration Feedback 构成（如 CLI / SDK 的
                下游兼容矩阵 CI，runtime feedback 缺省须显式声明）
Risk Overlay    决定 Reviewer 构成、Context Freshness 严格度、Breakage 定级门槛
```

具体 Profile 绑定在组6 RP 补齐时登记；本规程不预留学生位。

---

# 15. Example

**CHG-WO-142 / WP-1 与 WP-2——接 SP-11 示例。**

A1-A3：WP-1 修到 R4 后进入 Review。Reviewer 主动推理发现：真实 Transition 需要 `new provider + old consumer` 组合，但 Change-local test 只测了 `new + new`。分类判断：若 Design 已明确兼容关系 → 只是 missing direct test，回本层补测（SP-11 机制）；若 Design 根本没定义 mixed-version semantics → 回 SP-05。本例属后者，SP-05 出新 Design Revision 后 WP-1 到 R5，Review Approval 重新绑定 R5（R4 的 Approval 不自动覆盖）。

A4-A5：期间同事 WP-2 改了同一 Contract 包——Material Base Change。Integration Context 推进到含 WP-2 的 synthetic merge M1，Status Check 绑定 M1（而非仅 WP-1 head），发现 Contract 序列化冲突 → Integration Conflict 类 → Context Reconciliation 后重跑。

A8：WP-2 Merge 后 shared contract build 变红。定性：关键 Build 不可工作 → Breakage 记录（不是任何 Change 的 State）。分类：先查 source mismatch / generated artifact / concurrent merge / CI infra——若是 Product Source Defect：fix forward 或 revert，Restore 优先；若只是 CI Runner Failure：修 Infrastructure，不回滚产品逻辑。Owner = 当日 maintainer。

A6：WP-3 的搜索增强未完工，以 Feature Flag（inactive path）集成：old behavior preserved、schema 兼容、shared checks green；Flag 追溯到 SP-05 的 Transition / Cleanup 设计，Owner 与退出条件登记。

A10 移交：Review Record（R5-bound）、Integration Record（M1-bound）、Breakage 记录一条（分类分支按实际定性落定，带 Owner / Restore 结果）。Integration Green——但这只说明 Candidate 与当前开发上下文组合已有真实反馈；Candidate Accepted 与否，是 SP-13 的事。

---

# 16. 最终原则

> **Review 与 Integration 的全部价值在于"和并发现实碰撞"——绑定 Revision 的人脑推理，加上绑定 Merge Result 的真实反馈。Approval 不随 Revision 漂移，Green 不随 Context 漂移；Breakage 先分类再动手，Restore 优先但不等于 Revert；Incomplete 可以集成，Broken 不可以过夜。而无论 main 绿到什么程度，它都只是 Shared Baseline 的健康事实——不是 Candidate Accepted，不是 Release，更不是 Current。**
