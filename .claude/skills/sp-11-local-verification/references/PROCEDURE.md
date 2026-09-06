# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-11 Local Verification Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-31：组3 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1050 处引用核验 PASS AFTER REPAIR（备注级）；证据见组3 审计报告与横向回归报告）  
> 单一职责：为一个明确 Implementation Revision / Revision Set 生产 **revision-bound、可信、已分类的 Local Evidence**——组成并执行 Local / Pre-submit 两个 Feedback Scope 的 Feedback Run，绑定其真实上下文，判断结果的适用性与失效，处置 Unreliable Feedback 与 Required Feedback Evidence Gap，把每一次失败分类并路由到正确返回层，最后把证据按诊断价值裁剪保留并如实移交。  
> 本规程是 SP-06 A6–A8（Feedback Loop / Feedback Binding / Failure Classification）的**专门化细则**：SP-06 在 Work Package 控制层要求"反馈必须持续存在、被绑定、被分类"并把它作为 Outputs Ready 的候选条件；SP-11 规定反馈运行本身怎么组成、怎么绑定、怎么判效、怎么处置。SP-06 的其余动作（Guardrail Set 解析、Deviation/Drift 处置、Ready 判定）不在本规程。  
> 边界：Local Verification ≠ Required Verification 全集；Feedback Build ≠ Candidate Build ≠ Release Build；Local Evidence ≠ Candidate 成员（Ch6 显式选择绑定后才可能成为）；Feedback Green ≠ Candidate Accepted ≠ 任何 Current 更新。  
> 结构化镜像：`第五篇-SP11-LocalVerification-OperationContract.yaml`

---

# 1. Trigger

```text
A. Implementation Unit 在 Local Workspace 发生可运行变化
   （edit → build / check / test 的持续循环，不是 Implementation 完成后第一次发生）
B. 准备进入 Review / Shared Integration 之前——Pre-submit 反馈建立基本可审 / 可集成事实
C. Head Revision / Base Revision / Dependency Context / Test Definition 任一变化，
   需要重新判断已有 Feedback 结果的适用性
D. 某项 Required Feedback 因 Flaky / Quarantine / Skipped / Tool Failure /
   Context 不匹配而没有产生可信 Evidence——需要处置 Evidence Gap
E. Feedback FAIL——需要先分类再决定 Return Path
```

红线：**Check 没有可靠执行 ≠ Evidence Pass**（第四篇 Ch5 §93）；平台 UI 把 skipped job 显示为 success，不改变工程语义（§94）。

不触发本规程的情形：

```text
Candidate 形成 / Required Verification Obligation 判定 / Acceptance Decision → SP-13（Ch6）
Review Approval / Integration-context 进入决策 / Shared Baseline 治理        → SP-12（Ch5 §E）
Canonical Build / Artifact Identity / Provenance                              → SP-14（Ch6/Ch7）
Target 环境验证                                                                → SP-17（Ch7）
```

---

# 2. 输入

```text
Implementation Revision / Revision Set    本次反馈针对的真实内容（Ch5 §34；
                                          multi-repo / multi-build-unit 必须绑定一个
                                          可解释的 Revision Set，§36）
Working Source / Base Context             来自 SP-06 A1/A3；Base 变化可使旧结果失效（§84）
Applicable Guardrail Set 中验证相关义务    来自 SP-06 A2（如 Security Scan、Architecture Rule）
Required Local Feedback Obligation Set     本规程判定哪些反馈是"Required"的来源清单：
   - Project Policy / Gate 声明的 merge check
   - Accepted Design / Verification Obligation 声明的兼容性、迁移、安全义务
   - 后续 Candidate Acceptance 明确需要的证据（Ch6 输入预期）
   - Behavior Change 的最直接 Regression Protection（§78；§306 [SHOULD][BASELINE]）
Feedback 机制载体                          Build Definition / Static Check 配置 /
                                          Change-local Test 集（EA-04 / EA-07 / EA-08）
历史 Feedback Binding 记录                 用于 reuse / rerun 判断（§83、§143-144）
```

入口再挑战义务（B1 系统性规则）：上游所有 gate-zeroing 处置——SP-06 的 "Change-local Feedback 无 Known Blocker"、被声明为 optional 的 check、被 delegated 的验证义务——必须携带可解析理由或证据指针；没有理由或理由不成立的，挑战回来源规程，不得在本规程内默默继承。

---

# 3. 输出

```text
Local Evidence Set                  每次 Feedback Run 一条 Feedback Binding（§81 最小字段），
                                    结果状态为 SATISFIED / FAILED / UNRELIABLE / GAP 之一
Finding Register                    每个 Finding：分类（§97 九类）+ Return Path + 处置结果
Evidence Gap Record                 Required Feedback 缺可信结果时：缺口 + 处置
                                    （替代 Evidence / 受控 Exception·Bypass / 阻止依赖决策）
Quarantine Record                   Owner + Reason + Follow-up（§92）
Pre-submit Readiness Fact           scope-bound 三态（供 SP-12 消费）：
                                    READY = Pre-submit 义务全部满足（含以替代
                                    Evidence 满足）；READY-WITH-EXCEPTION = 有经受控
                                    Exception 处置的缺口，例外显式随行；
                                    NOT_READY = 存在以"阻止决策"处置的缺口
```

**不输出**（本规程无权产生）：

```text
Candidate Baseline / Candidate 成员资格      → SP-13（Ch6；Feedback Artifact 须被显式选择，§72）
Required Verification Satisfied / Assessment → SP-13
Candidate Accepted                           → SP-13
Review Approval / Integration 决策            → SP-12
任何 Current 更新                             → SP-19（Merge / Green 均不更新 Current，GI-05）
```

---

# 4. 核心语义

**Implementation Feedback Run `[BASELINE]`（§54）**：针对一个明确 Implementation Revision / Integration Context 执行的一组 Build、Compile、Static Check、Change-local Test、Generated Artifact Check 或其他快速验证动作。四个特征（§55）：`revision-bound / fast enough / repeatable enough / diagnostic enough`——后三者都是项目上下文判断，不是固定分钟数（§56-58）。

**Feedback Scope（§59-67）**：Local / Pre-submit / Integration-context / Shared-baseline 四个 Scope **不是四个强制 Stage**；项目可以合并、省略、自动化，只要风险和结果可解释。本规程拥有 Local 与 Pre-submit 两个 Scope 及全部通用机制语义；Integration-context 与 Shared-baseline 的进入决策属于 SP-12，SP-12 复用本规程的绑定 / 失效 / 分类机制，不另建一套。

**Feedback Build（§68-72）**：仍是第二篇 Build WHAT，但 ≠ Candidate Build ≠ Release Build。Feedback Artifact 若具备明确 Identity、可追 Source / Build Inputs、足够稳定 Context，**Ch6 可以选中它**——但必须显式选择和绑定（§72）；Output Set / Feedback Artifact 不得自动冒充 Candidate Baseline（§304）。

**Local Verification 的覆盖边界（§73-78）**：Static Check ≠ Dynamic Test（不执行被测行为时不得混称）；Change-local Test 主要保护本次 Implementation 直接引入 / 修改的 Behavior，**通常不覆盖** full cross-service integration / performance / security / acceptance / target environment validation（§77）；Behavior Change 应尽量同步带最直接的 Regression Protection，日常流程不应默认"先 Merge logic 几天后再补 test"（§78）。

**Feedback Binding `[BASELINE]`（§80-81）**：最小绑定六字段——Subject Revision / Revision Set、Base / Integration Context（适用）、Check / Test Identity、Result、Relevant Dependency / Build Context（按风险）、Observed At。**Green Result 不是永久事实**（§82）：R1 green 只表示 R1 在对应 Context 里 green。

**适用性失效触发（§83-87、§276）**：Head Revision 改变 / Base Revision 改变 / Dependency Context 改变 / Test Definition 改变——任一发生，相关 Feedback 必须重新判断 rerun / reuse / not applicable；Review Feedback 同样绑定 Revision（§87）。Rework 不要求所有 Check 全量重跑（§143），但**不能无依据复用 Green**（§144）：必须能说明"为什么旧 Evidence 仍覆盖新 Revision"。

**Unreliable Feedback `[BASELINE]`（§88-92）**：同一适用 Input / Context 下无法稳定给出一致结果的反馈机制（Flaky Test、non-deterministic build、unstable environment、clock/order-dependent test）。**不允许默认 rerun-until-green**（§90）：fail → rerun → pass 不能自动删除第一次 FAIL；先判断失败类型（§91）；Quarantine 必须带 Owner / Reason / Follow-up，不是永久解决（§92）。

**Required Feedback Evidence Gap `[BASELINE]`（§93-94、§299）**：被 Policy / Gate / Design / Verification Obligation / Candidate Acceptance 明确需要的反馈，因 Flaky / Quarantine / Skipped / Tool Failure / Context 不匹配而没有可信 Evidence 的状态。处置只有三种：提供替代 Evidence；记录受控 Exception / Bypass；保持 Evidence Gap 并**阻止依赖该证据的 Decision**。Optional local feedback 被跳过可以继续其他工作；承担 required 角色的不行。

**Failure Classification（§95-108、§279）**：Failure ≠ Implementation Defect。九类分类的目的不是统计，而是**决定回哪一层修**（§98）。Unknown 是合法暂态：不确定时先保留 Unknown、收集 Evidence，不为流程强行归类（§108）。

**Feedback Evidence Retention `[BASELINE]`（§145-148、§287）**：目标是"关键事实不丢 + 本地噪声不淹没 Change Record"。每次 compile typo / local unit fail 不必写入 Change Record（§145）；与 Design / Impact Decision Change、Shared Baseline Breakage、Required Gate / Review Failure、Material Security / Data Finding、Accepted Exception / Bypass、Persistent / Repeated Failure、有未来价值的 Root Cause 相关的失败必须长期可追（§146）。

---

# 5. Engineering Actions

## A1 — 确认入口并解析 Required Local Feedback Obligation Set

确认当前 Implementation Revision / Revision Set 可解析（SP-06 A1 已建立 Execution Context），然后回答：**对当前 Revision，哪些 Local / Pre-submit 反馈是 Required 的？** 来源按 §2 输入清单逐项解析——Policy / Gate 声明、Design / Verification Obligation、Candidate Acceptance 预期、Behavior Change 的直接回归保护。产出一份带来源指针的 Obligation Set；每项标注 required / optional 及理由。

同时执行 B1 再挑战：上游（SP-06 A11 的 "无 Known Blocker" 声明、被标 optional 的 check、被 delegated 的义务）没有理由或证据指针的，退回来源规程。

## A2 — 组成 Feedback Run

为每项 Obligation 选择或组成 Feedback Run，并核对四特征：

```text
revision-bound      能绑定到当前 Revision / Revision Set（不满足则结果无意义）
fast enough         Developer 能把结果用于当前实现决策（项目上下文判断）
repeatable enough   同一关键 Input 不会无法解释地一会儿绿一会儿红
diagnostic enough   失败至少能大致判断 Product / Test / Build / Infra / Integration / Unknown
```

不满足 repeatable / diagnostic enough 的机制先按 A6 处置，不得直接拿来出 Result。Static Check 与 Dynamic Test 分开登记；Change-local Test 登记其保护边界（本次直接引入 / 修改的 Behavior），不得声明覆盖 §77 列举的全集外领域。

## A3 — 执行并完成 Feedback Binding

执行 Build / Check / Test，**当场**完成最小绑定六字段（§81）。绑定缺失或不可解析（如 "main 分支最新" 这种不可复现指代）的运行不产生有效 Local Evidence——结果记为 GAP 而非 SATISFIED。Feedback Build 使用临时环境 / 不保留 Artifact 均合法（§70），但因此失去 Identity 的 Artifact 不得事后补声称具备 Candidate 资格。

## A4 — 判定每次运行的结果状态

```text
SATISFIED    机制可信执行 + 绑定完整 + 结果通过
FAILED       机制可信执行 + 绑定完整 + 结果不通过 → 进 A8 分类
UNRELIABLE   机制本身不可信（flaky / 不可复现 / 不可诊断）→ 进 A6
GAP          Required 反馈没有可信执行（skipped / 工具失败 / 上下文不匹配）→ 进 A7
```

工具退出码 success、平台 UI 绿色、job 被标记 skipped-but-success **都不是** SATISFIED 的充分条件——充分条件是"可信执行 + 绑定 + 通过"。

## A5 — 判断旧结果的适用性（reuse / rerun / not applicable）

Revision / Base / Dependency / Test Definition 任一变化后（Trigger C），对每条历史 Binding 逐项判断：

```text
rerun           变化触及该反馈保护的行为或其输入上下文 → 对最新 Revision 重跑
reuse           能说明"为什么旧 Evidence 仍覆盖新 Revision"（依据写入 Binding 记录）
not applicable  该义务对新 Revision 不再适用 → 携带理由，作为 gate-zeroing 处置
                登记，供 SP-12 / SP-13 入口再挑战（B1）
```

reuse 与 not applicable 都是**工程判断**，必须留依据；默认动作是 rerun。Review Feedback 的 Approval 同样随 Material Revision 变化失效（§87，SP-12 执行重审判断）。

## A6 — 处置 Unreliable Feedback

发现 flaky / 不可复现 / 不可诊断的机制：

```text
1. 禁止 rerun-until-green：第一次 FAIL 记录不得被后续 pass 自动删除（§90）
2. 先判断失败类型（§91）：Product? Test? Environment? Concurrency? Infra? External? Unknown?
3. 确认机制缺陷 → 修机制（Test / Check Defect 路径）或 Quarantine
4. Quarantine 必须登记 Owner + Reason + Follow-up（§92）；
   被 Quarantine 的若是 Required 反馈 → 立即转 A7 形成 Evidence Gap
```

长期依赖 rerun 掩盖的 flaky 机制是 Process Signal，记入 Finding Register 供过程改进（不作为人员 KPI，§151）。

## A7 — 处置 Required Feedback Evidence Gap

每个 Required 缺口三选一，并显式记录：

```text
替代 Evidence      用另一个可信、绑定完整的机制满足同一 Obligation（说明等价理由）
                   ——义务被满足，不阻塞下游
受控 Exception     按 Authority 要求记录 Exception / Bypass（Scope + 期限 + 批准者）
                   ——可移交，例外必须显式随行供下游再挑战
阻止决策           保持 Gap；凡依赖该证据的下游决策（Pre-submit 就绪、Review 进入、
                   Candidate 评估）一律不得进行——移交结论为 NOT_READY
```

平台把 skipped 显示为 success 不改变缺口事实（§94）。缺口记录随证据包移交，SP-12 / SP-13 入口必须能再挑战其处置。

## A8 — 分类每个 Finding 并路由返回层

每个 FAILED 结果先分类再行动（§99-108）：

```text
Implementation Defect                → 本层修（回 SP-06 Rework，产生新 Revision）
Test / Check Defect                  → 修测试 / 检查机制，不动产品代码凑绿
Design Assumption Invalidated        → 回 SP-05（Ch4）
New Impact Discovery                 → 回 SP-04（Ch3）
Requirement Semantic Gap             → 回 Requirement Authority（Ch2）→ SP-04 → SP-05（适用）
Integration Conflict / Context Change → Context Reconciliation（SP-12 域）+ 必要时重评
Tool / Infrastructure Failure        → 修反馈基础设施；不得为 Infra 失败 Revert 产品代码
External Environment / Dependency    → 隔离外部原因；结果记 GAP / NOT_READY 而非产品 FAIL
Unknown                              → 保留 Unknown，收集 Evidence，不强行归类
```

分类必须基于证据而不是"谁方便修"。所有 FAIL 默认归 Developer 会产生错误修复（§99）。

## A9 — 证据裁剪与保留

按 §146 清单决定长期保留：Design / Impact Decision Change、Shared Baseline Breakage、Required Gate / Review Failure、Material Security / Data Finding、Accepted Exception / Bypass、Persistent / Repeated Failure、有未来诊断价值的 Root Cause ——必须可追。普通本地噪声（编译笔误、即时修复的 unit fail）不强制归档。小 Change 可直接以 VCS / PR / CI 记录为载体（§308 [SHOULD][BASELINE]），不要求独立 Evidence Document。

## A10 — 移交 Local Evidence

按去向如实移交：

```text
→ SP-06 A11   Feedback 状态作为 Outputs Ready 第三项候选条件的输入
              （"无 Known Blocker" 必须由本规程的已执行、已绑定记录支撑）
→ SP-12       Pre-submit Readiness Fact（scope-bound 三态）；Review 不应是编译错误
              第一发现者（§157）——Readiness 为 NOT_READY（存在以"阻止决策"处置的
              缺口）时不移交；READY-WITH-EXCEPTION 可移交，例外显式随行
→ SP-13       Local Evidence Set 全文；其中具备 Identity / 可追 Input / 稳定 Context 的
              Feedback Artifact 可被 Ch6 显式选中绑定（§72）——选与不选是 SP-13 的决策，
              本规程只保证证据"可被选中"的质量
```

移交时附：Obligation Set 及每项最终状态、Gap / Quarantine / Exception 记录、reuse 依据。任何移交都**不是** Candidate Accepted、不是 Required Verification Complete、不是 Current 更新。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| A1 Obligation 解析 | Engineering Decision（自动化可提示 Policy / Gate 声明） |
| A2 组成 Feedback Run | Engineering Decision + Automation |
| A3 执行与绑定 | Automation（绑定记录必须自动产生，不可事后补写） |
| A4 结果状态判定 | Guardrail（规则机械） |
| A5 适用性判断 | Engineering Decision（自动化可发起挑战，结论留人） |
| A6 Unreliable 处置 | Engineering Decision |
| A7 Evidence Gap 处置 | Engineering Decision + Authority（Exception 需批准） |
| A8 Finding 分类路由 | Engineering Decision（工具不得代行分类） |
| A9 证据裁剪 | Guardrail（§146 清单机械）+ Policy |
| A10 移交 | Automation + Guardrail（不完整不移交） |

Hard Gates：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST NOT][BASELINE] G-SP11-01 用旧 Revision / 旧 Context 的 Green 证明新 Revision
                     （§82/§276/§303；Head/Base/Dependency/Test Definition 变化必须重判）
[MUST NOT][BASELINE] G-SP11-02 rerun-until-green：后续 pass 自动抹掉第一次 FAIL（§90/§278）
[MUST NOT][BASELINE] G-SP11-03 Quarantine / Skip 静默把 Required Evidence 变成 Green；
                     平台 UI success 不改变缺口语义（§94/§299）
[MUST NOT][BASELINE] G-SP11-04 把 Feedback Build / Run 的 Success 解释成 Candidate Accepted、
                     Required Verification Complete 或 Release Ready（§277）
[MUST NOT][BASELINE] G-SP11-05 未经分类就把 FAIL 归给产品实现（§99/§279）
[MUST NOT][BASELINE] G-SP11-06 把 Static Check 冒充 Dynamic Test，或把 Change-local Test
                     冒充 Required Verification 全集（§74/§77）
[MUST NOT][BASELINE] G-SP11-07 让 Feedback Artifact 未经 Ch6 显式选择绑定就成为
                     Candidate 成员（§72/§304）
[MUST][BASELINE]    G-SP11-08 重要 Feedback 必须当场绑定实际 Revision 与适用 Context（§275/§81）
[MUST][BASELINE]    G-SP11-09 reuse / not-applicable 处置必须携带可解析理由或证据指针，
                     且在 SP-12 / SP-13 入口可被再挑战（§144/§276 + B1 规则）
[MUST][BASELINE]    G-SP11-10 Required Feedback Evidence Gap 必须记录并以替代证据 /
                     受控例外 / 阻止决策三者之一处置（§299）
```

---

# 7. PASS Exit

本规程完成 = **Local Evidence State 对当前 Revision 真实建立**：

```text
[ ] Required Local Feedback Obligation Set 每项有明确最终状态：
    SATISFIED / FAILED-已分类已路由 / GAP-已处置 / not-applicable-带理由
[ ] 每条 SATISFIED 绑定六字段完整、对当前 Revision 适用（或 reuse 依据已记录）
[ ] 无未处置的 Required Evidence Gap；无裸 Quarantine；无 rerun-until-green 残留
[ ] Finding Register 中无未路由的 FAILED
[ ] 移交包（Obligation 状态 + Gap / Quarantine / Exception + reuse 依据）已发出
```

存在 Gap 时按处置分流：以替代 Evidence 满足的义务不阻塞下游；经受控 Exception 处置的缺口以 READY-WITH-EXCEPTION 移交、例外显式随行；以"阻止决策"处置的缺口使结论成为 **NOT_READY for downstream decision**，依赖该证据的下游动作被阻止——这是 truthful 结果，不是规程失败。

**完成不代表**：Candidate 已形成 / Required Verification 已满足 / Review 已通过 / 可进入 Shared Baseline（SP-12 判断）/ 任何 Current 已更新。

---

# 8. Evidence

Evidence by Work：Local Evidence 的天然载体是 VCS、PR / CL、CI 运行记录与任务运行器输出（§308），不要求独立证据文档。必须额外显式产生的只有：

```text
- Required Local Feedback Obligation Set（带来源指针）
- reuse / not-applicable 的依据记录
- Quarantine Record（Owner / Reason / Follow-up）
- Evidence Gap Record 及处置
- Finding 分类与路由记录（仅 §146 清单范围内的必须长期可追）
```

绑定记录必须在运行时自动产生（A3），事后补写的绑定不是 Evidence。

---

# 9. Current Update Obligation

```text
writesCurrent: false
```

Local Verification 不更新任何 Current。Feedback Green、Pre-submit 就绪、甚至后续 Merge / Integration 均不构成 Current 更新（§305，GI-05）；Current 校准与提交唯一通道是 SP-19（本组内已落地正式候选）。本规程产生的 Local Evidence 是 SP-19 校准时的 Actual Evidence Ref 候选之一。

---

# 10. FAIL / Return Path

```text
Feedback FAILED → A8 分类 → 九类 Return Path（见 A8 表）
机制 UNRELIABLE → A6（修机制 / Quarantine + Gap）
Required 缺口   → A7（替代 / 例外 / 阻止决策）
本层无法继续（外部依赖、缺决策）→ Work Package Blocker（SP-06 §10 Return Path），
                 不等于 Change BLOCKED（Ch1 非终态语义）
```

Rework 产生新 Revision 后回到 Trigger A / C；旧 Ready 声明不自动覆盖新 Revision（§303）。

---

# 11. Exception / Alternative Path

## 11.1 Emergency

Ch8 fast-path 下可压缩反馈**广度**（§79）：可暂缓非关键检查，但分类、绑定、Gap 处置从不豁免；压缩范围显式记录，变更后必须以 post-change verification 补齐，事后经 SP-21 / SP-19 对账。

## 11.2 Small Change / Lightweight Evidence

小 Change 直接以 VCS / PR / CI 为证据载体（§308）；Obligation Set 可折叠进 PR 描述；语义项（绑定、分类、Gap 处置）一项不可省。

## 11.3 Optional Feedback 跳过

被正确分类为 optional 的 local feedback 可跳过并继续其他工作（§94 前半）；但 optional 分类本身是 gate-zeroing 处置，必须带理由并可被 SP-12 / SP-13 再挑战。承担 required merge check / 关键兼容性 / 安全 / 迁移义务的检查不得按 optional 处理。

## 11.4 受控 Quarantine 路径

Quarantine 合法但永不免费：Owner + Reason + Follow-up 三要素齐全，Required 项同步形成 Evidence Gap 并按 A7 处置；Follow-up 到期未解决升级为 Finding 路由。

---

# 12. Theory Trace

```text
第一篇  GI-03（Current 经 Change）、GI-05（Merge/Green 不更新 Current）、
        GI-13（MD 为规范源）
第二篇  Testing / Quality WHAT；Build WHAT（Feedback Build 仍满足）；Evidence 语义
第三篇  Source / Runtime 作为 Evidence Context；Source WHERE 可解析
第四篇  Ch5 §C 全节（§54-108：Feedback Run / Binding / Unreliable / Gap / 九类分类）、
        §142-148（Rework 复用与 Evidence Retention）、§157（Review 非编译错误第一发现者）、
        §274-279 / §287 / §299 / §303-305（MUST-BASELINE 要求）；
        Ch6（Evidence Record / Validity / Gap 语义的消费方接口，§38-55 / §70-75 / §72——
        规范所有权属于 SP-13，本规程只对齐生产者侧义务）；
        Ch8（Emergency 压缩 + post-change verification）
```

Theory Trace 只说明受哪些理论约束；本规程不复制理论正文，不成为第二份 Authority。

---

# 13. Executable Asset References

```text
EA-04 Task Runner          local / CI 等价性：同一 Feedback Run 本地与 CI 结果可互释
EA-07 Reusable CI          Pre-submit / CI 检查模板承载绑定记录自动产生
EA-08 Verification Harness test fixtures / contract harness 的确定性执行（repeatable enough）
EA-03 Dev Environment      Local Workspace 环境一致性（Dependency Context 可绑定）
```

工具适合：执行 Feedback Run、自动产生绑定、发起适用性挑战、保留记录。工具不适合：Finding 分类、reuse 依据判断、Gap 处置决策、Exception 批准。

---

# 14. Reference Profile Bindings

```text
通用层    Operation Contract / Theory Trace / Evidence 语义 / Control 语义——全 Profile 共用
Risk Overlay  决定 Required Local Feedback 的深度与广度（高风险：安全扫描、迁移一致性
              进入 Required Set；低风险可裁剪，裁剪登记理由）
```

具体 Profile 绑定（如 RP-ONLINE-API-PY-GH 的 local pytest / pre-submit PR checks 映射）在组6 RP 补齐时登记；本规程不预留学生位。

---

# 15. Example

**CHG-WO-142 / WP-1（data expand）——接第四篇 Ch5 §G Work Order（与 SP-06 示例同故事线；SP-06 示例内 ID 为 CHG-WO-017）。**

A1：Obligation Set 解析出 4 项 Required——migration smoke（Design 声明的迁移义务）、module unit test（Policy merge check）、 focused contract check（Candidate Acceptance 预期）、lint（Policy）；2 项 optional（benchmark、docs link check，理由登记）。

A2-A3 第一轮：migration smoke FAIL——列被写成 NOT NULL。绑定记录完整（WP-1@R1 / base main@a1b2 / migration V203 / 依赖上下文锁定）。

A8 分类：**Implementation Defect**（Design 仍成立，是迁移写错）→ 本层修，R2 重跑 SATISFIED。无需回 SP-05。

第二轮 Finding：旧 ORM 版本读不了新增列。A8 分类：**Design Assumption Invalidated**（Design 假设了 runtime 兼容范围）→ 回 SP-05；若因此发现受影响 runtime 范围更大 → 连带回 SP-04。本规程不动产品代码凑绿。

Flaky 插曲：focused contract check 在 CI 上 fail → rerun → pass。A6 介入：第一次 FAIL 记录保留；判断为 order-dependent test（Test Defect）；Quarantine 登记 Owner=QA lead / Reason=order dependency / Follow-up=两周内修复。该 check 是 Required（Candidate 预期）→ A7 形成 Evidence Gap，处置=替代 Evidence（本地确定性重跑三次 + 绑定记录），Pre-submit 就绪不被阻止，但 Gap 记录随移交包进入 SP-13 视野。

A10 移交：Obligation 4 项 SATISFIED（1 项经替代证据）、Gap 1 条已处置、Quarantine 1 条、Finding 2 条已路由。这只是 **Local Evidence State 建立**——Candidate 是否接受这些证据，是 SP-13 的事。

---

# 16. 最终原则

> **Local Verification 的价值不取决于"绿了多少"，而取决于每个结果绑定在哪个 Revision、由多可信的机制产生、缺口被如何处置。绿而无绑定等于没有证据；fail 而不分类等于没有诊断；skip 而不记录等于没有工程。本规程的每一次运行都要能回答：这个结果对哪个 Revision、在哪个 Context、由哪个机制、以什么可信度成立——以及当它不再成立时，谁会知道。**
