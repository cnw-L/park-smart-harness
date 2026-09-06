# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-17 Target Validation / Release Completion Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-31：组3 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1050 处引用核验 PASS AFTER REPAIR（备注级）；证据见组3 审计报告与横向回归报告）  
> 单一职责：在明确 Delivery Target / Deployment Attempt / Rollout Slice 上，验证目标环境中**真实存在**的软件状态、运行行为、依赖、Data / Migration、Transition Invariant 与适用业务 / 质量要求是否达到本次 Delivery / Release Acceptance 所需条件；按 Target Scope 作出 SATISFIED / FAILED / NOT_READY 判定与 Target Release Completion 决策，并在 Completion 后按 Ch1 Ledger 机制更新 Accepted Current Release。  
> 边界：Target Validation ≠ Ch6 Required Verification 重跑全集（Ch7 §67）；Target Validation PASS ≠ Deployment Tool SUCCESS（§72）；只有有效 Evidence 证明不满足才是 FAIL，证据缺口是 NOT_READY（§73-74）；Validation Maturity 未满足必须保持 NOT_READY（§77、§141 [MUST][BASELINE]）；Target Validation 是 Target-scoped（§79）；Release Completion ≠ Change Closure（§85）。  
> 与 SP-13 / SP-15 / SP-16 / SP-18 的分工：SP-13 回答"Candidate 本身是否有足够 Candidate-level Evidence"；本规程回答"它到了这个 Target 后是否真的成为预期运行事实"（§67）。SP-15 提供 Deployment Attempt / Runtime State / Observation Record 事实并路由 Delivery Finding；本规程消费这些事实下验证结论。Feature Exposure 状态作为验证 Concern 之一（§70），其变化控制归 SP-15 / SP-16（pending-definition，组5）。Recovery Validation（§100）由本规程定义判定语义，Recovery 执行细节归 SP-18（pending-definition，组5；落地前按 Ch7 §89-102 正文直接执行，执行记录义务由 SP-15 代行）。  
> 结构化镜像：`第五篇-SP17-TargetValidation-OperationContract.yaml`

---

# 1. Trigger

```text
A. Deployment Attempt 完成或 Rollout Slice 到位——需要该 Target / Slice 的验证判定
B. Required Target Validation Obligation 的 Evidence 到达或缺口显现
C. Validation Maturity Condition 相关事件（代表性流量 / 后台周期 / 对账完成 / 状态收敛）
D. Target Release Completion 决策点——Rollout / Transition 达到预定状态
E. Recovery 执行后——需要 Recovery Validation 与恢复后 Accepted Current Release 判定
F. 发现 Validation Evidence Gap（指标缺失 / smoke 不可用 / 观测断裂 / migration 结局未知）
```

红线：**高风险场景不得因为"看起来没事"在 Evidence Gap 下推进**（§110）；即时 Smoke PASS / Deployment SUCCESS / 短时 Health 正常不得单独触发 Target Release Completion（§141）。

不触发本规程的情形：

```text
Candidate 级 Verification / Acceptance      → SP-13（本规程不重跑全集，§67）
Release Formation / Authorization / 部署执行 → SP-15（本规程消费其事实，不做交付控制）
Feature Flag / Launch 设计与执行             → SP-16（pending-definition，组5；暴露状态只是本规程的验证 Concern）
Recovery 动作执行                            → SP-18（pending-definition，组5；本规程判定恢复后状态是否达标）
Change Closure / Current Design 更新         → SP-19（Ch9 域，§85、§145）
```

---

# 2. 输入

```text
Release Baseline + Candidate Acceptance    SP-15 / SP-13：被交付对象身份、Acceptance
                                           Scope、Known Exception（§69 来源之一）
Delivery Target / Rollout Scope            明确 Target Scope（§79）；Slice 序列与
                                           Observation 计划（SP-15 A8）
Deployment Observation Record              SP-15 A9：Attempt 结果、步骤事实、
                                           Environment Current Runtime State（含 Mixed
                                           State）、Slice 级信号（§65）
Ch4 设计约束                               Transition Invariant、Rollout / Recovery
                                           Direction（§69）
Ch3 Runtime / Quality Risk                 验证深度与 Maturity 要求的驱动（§69、§78）
Target-specific Dependency / Policy        目标环境特有依赖与策略（§69）
Observability 能力                         EA-15：按 version / cohort 分解的信号
                                           （归因质量前置，§53-55 / §120-121 同旨）
Recovery Attempt 事实（Trigger E）          SP-15 A12 / SP-18：§98 九字段中除
                                           Validation 外的八字段——Recovery Attempt
                                           ID、Trigger、Starting State、Chosen
                                           Strategy、Anchor、Actions、Evidence、
                                           Final Observed State；Validation 结论由
                                           本规程产出（A10），Attempt ID 是锚定
                                           恢复事实到具体 Attempt 身份的必备项
```

入口再挑战义务（B1 系统性规则）：上游移交中的门禁归零归类——SP-15 的 Rollout Proceed 依据、Observation 计划的 N-A 声明、Known Exception 的"已受控"声明、Recovery Anchor 核验结论——必须携带可解析依据；无依据的归零归类退回来源规程。本规程自身对 Obligation 作出的 N-A / Maturity 豁免同样必须携带理由，可被 SP-19 / 组级审计再挑战。

---

# 3. 输出

```text
Required Target Validation Set   按 Release Baseline + Delivery Target + Rollout /
                                 Transition Scope 派生的 Environment-specific
                                 Validation Obligation 集合（§68 [BASELINE]）
Target Evidence                  复用 Ch6 Evidence 语义（Subject / Definition /
                                 Context / Result / Validity / Applicability），
                                 Subject = Deployment Attempt / Runtime Slice /
                                 Target State 中的适用对象（§71）
Target Validation Assessment     按 Target Scope：SATISFIED / FAILED / NOT_READY（§75）
Maturity 状态记录                 每个带 Maturity Condition 的 Obligation：
                                 条件内容与满足事实（§76-77）
Validation Gap 记录               缺口内容、影响 Obligation、处置（§74、§110）
Target Release Completion Record 按 Target Scope 的 Completion 决策与依据（§80-81）
Accepted Current Release 迁移     Completion 后经 Ch1 Baseline Transition Ledger 的
                                 迁移记录（§82-83）
Recovery Validation 结论          恢复后 Target 是否进入预期 Safe State、关键业务 /
                                 Data / Contract / Dependency / Availability 是否恢复、
                                 下一步方向（§100）
```

**不输出**：

```text
Candidate 级 Verification 结论    → SP-13（§67：不重跑全集）
Deployment / Rollout 执行控制      → SP-15（Proceed / Pause 决策在 SP-15，本规程提供证据判定）
Feature Exposure 策略             → SP-16（pending-definition，组5）
Recovery 动作执行                  → SP-18（pending-definition，组5）
Change Closure / 项目级 Current 更新 → SP-19（§85、§145）
```

---

# 4. 核心语义

**Target Validation（§66 [BASELINE]）**：在明确 Delivery Target / Deployment Attempt / Rollout Slice 上验证**真实存在**的软件状态与运行行为。它与 Ch6 的分工（§67）：Ch6 回答 Candidate 本身证据是否充分；Ch7 回答它到达这个 Target 后是否真的成为预期运行事实。Target Validation **不是**把 Ch6 Required Verification 在环境里重跑一遍。

**Required Target Validation Set（§68 [BASELINE]）**：针对 Release Baseline + Delivery Target + Rollout / Transition Scope，在本次 Target Acceptance 前必须获得处置的 Environment-specific Validation Obligation 集合。来源（§69）：Release Baseline / Candidate Acceptance、Ch4 Transition Invariant、Ch4 Rollout / Recovery Direction、Ch3 Runtime / Quality Risk、Deployment Definition、Target-specific Dependency / Policy、Migration / Data Requirement、Known Exception。常见 Concern（§70，按适用性）：产物实际在位、Config / Policy 生效、Migration / Schema 状态、应用健康、关键依赖可达、核心 smoke / 业务流、版本相关错误 / 延迟、Transition Invariant、Data 对账、安全 / 鉴权路径、可观测可用、Feature 暴露状态。

**Target Evidence（§71）**：继续复用 Ch6 Evidence 六要素，但 Subject 变为 Deployment Attempt / Runtime Slice / Target State 中的适用对象；Context 记录实际解析结果。

**结果语义（§72-75）**：Deployment Step 全部执行完成 ≠ Target Validation PASS（§72）；只有**有效 Evidence 明确证明不满足要求**才是 FAIL（§73）；required telemetry 不可用 / 验证环境或依赖不可用 / 观察窗口不足 / migration 结局未知 = **NOT_READY / Evidence Gap，不是自动 FAIL**（§74）。Assessment 复用 Ch6 三态 SATISFIED / FAILED / NOT_READY，保持与 Candidate Verification 对 Evidence Gap / Valid FAIL 的解释一致（§75）。

**Validation Maturity Condition（§76-78、§141）**：某 Obligation 除即时检查外还需达到的代表性运行 / 样本 / 事件 / 时间窗口 / 业务周期 / 状态收敛条件（如 minimum representative traffic、一个 scheduled background cycle、migration reconciliation complete、queue backlog settled、观察条件内无新 Invariant 违反）。**未满足时必须保持 NOT_READY**——即使 smoke PASS、deployment SUCCESS（§77、§141 [MUST][BASELINE]）。Maturity **不是全局固定 Soak Time**：CLI 包可能不需要等待，后台计费任务可能必须经历一个 billing cycle，高 QPS API 可能很快获得代表性样本——Risk / Behavior drives maturity（§78）。

**Target-scoped（§79-84）**：Production-US PASS 不能证明 Production-EU PASS；每个 Target Scope 有自己的真实 Runtime / Validation Fact（§79）。**Target Release Completion（§80 [BASELINE]）**：对一个明确 Release Baseline + Delivery Target Scope，预定 Rollout / Transition 达到本次 Completion 所需状态、Required Target Validation 已满足、Known Exception 已受控，可以把该 Release 认定为该 Target Scope 的 Accepted Current Release 的 Decision / Progress Fact。Completion 声明必须带 Target Scope（§81）；Completion 后 Accepted Current Release 经 **Ch1 Current Baseline Transition Ledger** 迁移，而不是修改全局 project.current_release（§82-83）；Multi-target Partial Acceptance（US=1.9 / EU=1.8 / APAC mixed）是不同 Target Scope 的 Current Reality，不是矛盾（§84）。

**Completion ≠ Change Closure（§85、§145）**：Change 可能还需另一 Target、Transition Cleanup、Calibration、Current Design / Structure Update、Closure——那是 Ch9 / SP-19 域。但**不得为了"等最终 Closure"而延迟记录 Production 当前实际运行的版本 / Migration / Config / Mixed State**（§145）。

**Recovery Validation（§99-101）**：Recovery Command SUCCESS 只表示控制面操作完成（§99）；Recovery Validation（§100 [BASELINE]）确认 Target 实际进入预期 Safe State、关键业务 / Data / Contract / Dependency / Availability 恢复，并明确下一步（重新交付 / 保持旧 Release / 进入 Incident / Rework）。恢复回 previous accepted release 且验证通过的，Accepted Current Release 可继续保持 / 回到该版本（§101）。

---

# 5. Engineering Actions

## A1 — 派生 Required Target Validation Set

按 Release Baseline + Delivery Target + Rollout / Transition Scope，从 §69 八类来源派生 Environment-specific Validation Obligation 集合（§68）。每条 Obligation 登记：验证目标、所需证据、通过依据、适用 Context、来源指针。对照 §67 红线：该集合回答"到了这个 Target 是否为预期运行事实"，不是 Ch6 全集重跑；候选 Concern 按 §70 十二项按适用性勾选，N-A 项携带理由（B1）。

## A2 — 声明 Validation Maturity Condition

对每条需要的 Obligation 声明 Maturity Condition（§76）：代表性流量下限 / 必须经历的后台周期 / 对账完成 / 队列收敛 / 观察条件内无新 Invariant 违反等。由 Risk / Behavior 驱动（§78），**不得设置全局固定 Soak Time 冒充语义**，也不得以"没有声明"逃避必要成熟度。无 Maturity 需求的 Obligation 记录"即时证据即可"的判断。

## A3 — 绑定 Target Evidence

证据产生时按 Ch6 六要素绑定（§71）：Subject 显式到 Deployment Attempt / Runtime Slice / Target State 中的适用对象；Context 记录实际解析的环境 / 配置 / 依赖状态；Definition 带 Revision。信号必须能按 version / cohort 分解到本 Slice / 本 Attempt——归因不足的证据登记 Applicability 限制（§53-55、§120-121 同旨）。

## A4 — 执行验证并如实记结果

对每条 Obligation：有效证据证明满足 = PASS；**只有有效证据明确证明不满足**才是 FAIL（§73）；证据不可得 / 环境不可用 / 观察窗口不足 / 结局未知 = NOT_READY + Gap 记录（§74）。部署工具 SUCCESS 本身永远不是 PASS 依据（§72）。

## A5 — 判定 Maturity 满足状态

带 Maturity Condition 的 Obligation：检查条件事实是否达成（代表性样本量 / 周期完成 / 对账结果 / 收敛状态 / 观察条件）。未达成 → 保持 NOT_READY，即使即时检查全绿（§77、§141）。达成事实记入 Maturity 状态记录，该 Obligation 证据方可进入 Completion 判断。

## A6 — 形成 Target Validation Assessment

按 Target Scope 汇总：全部适用 Obligation SATISFIED → SATISFIED；任一有效 FAIL → FAILED；存在未处置 Gap / 未成熟 Obligation → NOT_READY（§75）。Assessment 带显式 Target Scope（§79），一域结论不得外推他域。

## A7 — 处置 Gap 与 Finding

Evidence Gap 三处置（复用 Ch5 / Ch6 语义）：补充替代证据 / 受控例外（权限 + 残余风险）/ 阻塞决策。**高风险场景禁止"看起来没事"式推进**（§110）。验证中发现的 Candidate 缺陷证据 → Delivery Finding（candidate-defect-in-target）移交 SP-15 A11 路由回 SP-13 / SP-06；Target 环境缺陷 → SP-15 / 平台域，不影响 Candidate disposition。

## A8 — 决策 Target Release Completion

条件（§80）：预定 Rollout / Transition 达到本次 Completion 所需状态 + Required Target Validation SATISFIED（无未成熟 Obligation、无未处置 Gap）+ Known Exception 受控。满足 → 签发 Completion Record，**必须带 Target Scope**（§81）；不满足 → 保持现状并记录缺口。Completion 是 Decision / Progress Fact，不是 Change Closure（§85）。

## A9 — 迁移 Accepted Current Release

Completion 签发后，经 Ch1 Current Baseline Transition Ledger 登记该 Target Scope 的 Accepted Current Release 迁移（§82-83）：from → to、Target Scope、Completion Record 引用、时间。多 Target 各自独立迁移，Partial Acceptance 合法（§84）。**不得**修改全局指针、不得等他域、不得等 Change Closure（§145）。

## A10 — Recovery Validation 与恢复后判定

Recovery 执行后（Trigger E）：确认 Target 实际进入预期 Safe State——旧产物真实运行、数据可读、关键业务流恢复、Migration / 流量安全（§99-100）。结论三分：进入预期 Safe State → Accepted Current Release 保持 / 回到 previous accepted release（§101，经 A9 Ledger 机制）；未进入 → 保持 NOT_READY 并明确下一步（重新交付 / 进一步 Recovery / Incident-Rework）；证据不足 → Gap 处置（A7）。Recovery 执行细节归 SP-18，本规程只下判定。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| A1 派生验证集合 | Engineering Decision（来源机械枚举，裁剪留理由）+ B1 再挑战 |
| A2 声明 Maturity | Engineering Decision（Risk 驱动；反固定 Soak Time 红线机械） |
| A3 绑定 Target Evidence | Automation（运行时产生记录）+ Guardrail（归因分解要求） |
| A4 执行与记结果 | Automation + Guardrail（FAIL / NOT_READY 语义机械） |
| A5 Maturity 判定 | Guardrail（未满足即 NOT_READY 机械） |
| A6 Assessment | Guardrail（汇总语义机械） |
| A7 Gap / Finding 处置 | Engineering Decision + Authority（受控例外） |
| A8 Completion 决策 | Decision Point（条件机械 + 决策记录） |
| A9 Ledger 迁移 | Automation + Guardrail（Ledger 机制机械，禁全局指针） |
| A10 Recovery Validation | Guardrail + Engineering Decision |

Hard Gates：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP17-01 Required Target Validation Set 必须 Environment-specific
                     且在 Target Acceptance 前全部获得处置（§68）
[MUST NOT][BASELINE] G-SP17-02 把 Ch6 Required Verification 全集重跑当 Target Validation，
                     或把 Deployment Tool SUCCESS 当 Validation PASS（§67、§72）
[MUST][BASELINE]    G-SP17-03 FAIL 仅限有效证据明确证明不满足；证据缺口一律
                     NOT_READY 而非 FAIL（§73-75）
[MUST][BASELINE]    G-SP17-04 Validation Maturity Condition 未满足前必须保持 NOT_READY；
                     即时 Smoke PASS / Deployment SUCCESS / 短时 Health 正常不得单独
                     触发 Target Release Completion（§77、§141）
[MUST NOT][BASELINE] G-SP17-05 用全局固定 Soak Time 冒充 Maturity 语义——Risk /
                     Behavior drives maturity（§76、§78）
[MUST][BASELINE]    G-SP17-06 一切验证 / Completion 结论带显式 Target Scope；一域 PASS
                     不得外推他域（§79、§81）
[MUST][BASELINE]    G-SP17-07 Accepted Current Release 只能在 Completion 后经 Ch1 Ledger
                     迁移；禁止修改全局 current_release 指针（§82-83）
[MUST][BASELINE]    G-SP17-08 Completion ≠ Change Closure；不得为等 Closure 延迟记录
                     真实运行事实（§85、§145）
[MUST NOT][BASELINE] G-SP17-09 高风险场景在 Validation Evidence Gap 下以"看起来没事"
                     推进（§110）
[MUST][BASELINE]    G-SP17-10 Recovery Validation 必须确认实际 Safe State；Recovery
                     Command SUCCESS 不视为完成（§99-100）
[MUST][BASELINE]    G-SP17-11 Obligation 的 N-A / Maturity 豁免 / 受控例外必须携带
                     可解析理由并可被再挑战（B1）
```

---

# 7. PASS Exit

```text
[ ] Required Target Validation Set 已派生、Environment-specific、无无依据 N-A
[ ] 每条 Obligation 有明确结果：PASS（有效证据）/ FAIL（有效证据）/ NOT_READY（Gap 记录）
[ ] 带 Maturity Condition 的 Obligation 条件事实已核验，未成熟者保持 NOT_READY
[ ] Assessment 按 Target Scope 形成，无外推
[ ] Completion 决策条件逐条核验，Completion Record 带 Target Scope
[ ] Accepted Current Release 经 Ledger 迁移（或如实保持），无全局指针修改
[ ] Gap / Finding 全部处置路由；Candidate 缺陷证据已回 SP-15 / SP-13 链
```

**完成不代表**：Candidate 被重新验证（SP-13 域）/ 其他 Target Scope 完成（各自判定）/ Feature 已暴露（SP-16，pending-definition）/ Change 关闭或 Current Design 更新（SP-19）/ Incident 解决。

---

# 8. Evidence

Evidence by Work：Target Evidence 的天然载体是可观测系统、验证作业、平台记录（EA-15 / EA-08）；Slice 级信号来自 SP-15 的 Observation Record。必须显式产生的：

```text
- Required Target Validation Set（含来源指针与 N-A 理由）
- Maturity Condition 声明与满足事实
- NOT_READY / Gap 记录与处置（替代证据 / 受控例外 / 阻塞）
- Target Release Completion Record（Target Scope + 条件核验 + 依据）
- Accepted Current Release 的 Ledger 迁移记录
- Recovery Validation 结论与下一步方向
```

---

# 9. Current Update Obligation

```text
writesCurrent: accepted-current-release-ledger-only
```

本规程唯一的"Current 写入"是 Target Release Completion 后**该 Target Scope** 的 Accepted Current Release Ledger 迁移（§82-83）——这是 Ch7 域内的目标环境事实，由本规程登记。项目级 Current（Design / Structure / Calibration / Change Closure）一律走 SP-19（§85、§145）；本规程的验证结论与运行事实是 SP-19 Calibration 的 Actual Evidence 来源。

---

# 10. FAIL / Return Path

```text
Target Validation FAILED（有效证据）  → Finding 分类移交 SP-15 A11：Candidate 缺陷
                                        → SP-13 / SP-06 链；环境 / 依赖缺陷 → 平台域
Target Validation NOT_READY            → 补证据 / 修观测 / 等 Maturity / 受控例外 /
                                        阻塞决策（A7）；不得改记 PASS 或 FAIL
Maturity 长期无法满足                   → 回 A2 重审条件设计（Risk 变化）或升级决策；
                                        禁止悄悄删除条件
Completion 条件不满足                   → 保持现状，缺口显式；Rollout 侧回 SP-15 A8
                                        （Pause / 回退方向）
Recovery Validation 未达标              → 保持 NOT_READY → SP-18（pending-definition，
                                        组5）进一步 Recovery / Incident；不得改写
                                        Accepted Current Release 冒充恢复
```

---

# 11. Exception / Alternative Path

## 11.1 小团队轻量承载

CI/CD Deployment Record + Monitoring / Smoke Check 可承载本规程语义（§139 [SHOULD]）：载体折叠，Obligation 处置、Maturity、NOT_READY 语义、Ledger 迁移不折叠。

## 11.2 观测能力缺口

required telemetry 缺失本身就是 NOT_READY（§74）：处置是补观测（EA-15）或受控例外，高风险 Target 在缺口下不得 Completion（§110）。

## 11.3 Client / Distribution 形态

无服务端 Environment 的交付，用 Distribution / Channel / Cohort / Installation / Adoption / Version Exposure / Withdrawal 记录实现同类验证语义（§88）：验证 Concern 照按适用性派生，Subject 变为 Distribution Cohort / Version Exposure 事实。

## 11.4 Emergency

Ch8 fast-path 可压缩验证深度与 Maturity 窗口（§144），但不得建立另一套不留 Evidence、不做 Reconciliation 的机制；压缩的范围与残余风险必须记录，事后经 SP-21（pending-definition，组5）/ SP-19 对账。

---

# 12. Theory Trace

```text
第一篇  GI-03 / GI-05 / GI-13；Ch1 Baseline Transition Ledger / Decision 机制
第二篇  Deploy ≠ Release ≠ Launch；Testing / Verification WHAT 边界
第三篇  Runtime WHERE 作为验证 Subject 的来源
第四篇  Ch5 §88-94 接口（Unreliable Feedback / Evidence Gap 处置语义同源）；
        Ch6 §38-55（Evidence 六要素、PASS≠Valid、Validity / Applicability）、
        §66-75（Coverage / Gap / NOT_READY 语义）——本规程复用而非重定义；
        Ch7 §37（Deployment Result ≠ Target Validation Result）、§46-59
        （Rollout Observation / Attribution 作为证据质量前置）、§60-65
        （Runtime State / Observation Record 作为输入）、§66-85（Target
        Validation / Set / 结果语义 / Maturity / Completion / Accepted Current
        Release / Multi-target）、§99-101（Recovery Validation）、§110
        （Evidence Gap 高风险红线）、§139（Minimum Requirements 相关 MUST /
        SHOULD）、§141（Maturity Completion MUST-BASELINE）、§143（Ch6 接口：
        Candidate Accepted ≠ Release Authorized ≠ Deployment Complete ≠
        Production Validation）、§144（Ch8）、§145（Ch9 接口）
```

Theory Trace 只说明受哪些理论约束；本规程不复制理论正文，不成为第二份 Authority。

---

# 13. Executable Asset References

```text
EA-15 Observability       按 version / cohort 分解的信号能力——归因质量与 Maturity 判定的前提
EA-08 Verification Harness smoke / 合同 / 对账验证的确定性执行载体
EA-16 Recovery            Recovery Validation 的执行配合（判定语义在本规程）
EA-13 Environment / Secret 验证对 Target 的接入（Secret 不进任何证据记录）
```

工具适合：采集与分解信号、执行 smoke / 对账、核验 Maturity 事实、登记 Ledger 迁移。工具不适合：Obligation 派生与裁剪结论、Maturity Condition 设计、受控例外批准、Completion 决策结论、"看起来没事"式判断。

---

# 14. Reference Profile Bindings

```text
通用层        Operation Contract / Theory Trace / Evidence 语义 / Control 语义——全 Profile 共用
Delivery Shape  决定验证 Subject 形态（服务端 Runtime Slice vs Client Distribution
                Cohort / Version Exposure，§88）与可用信号面
Risk Overlay    决定 Obligation 深度、Maturity 严格度、Evidence Gap 的可例外空间
               （高风险收紧 §110）、Completion 自动化程度
```

具体 Profile 绑定在组6 RP 补齐时登记；本规程不预留学生位。

---

# 15. Example

**CHG-WO-142 / WO-1.9.0 的 Production-US 验证与 Completion——接 SP-15 示例。**（本示例走 Ch7 §122-138 WorkOrder 的 Canary FAIL 分支；同一 Change 在 Ch9 §84 / SP-19 示例中走 Validation PASS 分支——两个分支各自忠于其理论源。）

A1-A2：对 Release WO-1.9.0 + Production-US + Canary 序列派生 Required Target Validation Set：产物在位、V203 schema 状态、search correctness、transfer 业务流、版本相关错误率、Transition Invariant（混合版本语义）、数据对账、可观测可用。其中"数据对账"与"search correctness"声明 Maturity Condition：migration reconciliation complete + 代表性流量样本；transfer 错误率为即时证据即可。

A3-A5：S1（5%）证据按 cohort 分解绑定（Subject = Slice S1 Runtime State）。Canary 观察发现 new version transfer error material、old version 正常——**有效证据明确证明不满足** → 该 Obligation FAILED（§73），Assessment(Production-US) = FAILED，Proceed = STOP（回 SP-15 A8 / A12）。

A10：Recovery R1 执行后做 Recovery Validation：100% v1.8 serving、critical transfer flow healthy、new bad path inactive、data consistent（§131）→ 确认进入预期 Safe State；Environment Current Runtime State = recovered v1.8 + expanded schema；Accepted Current Release 经 Ledger 确认保持 1.8（§101）。下一步方向明确：C2 缺陷修复链（SP-06 → C3 → SP-13）后重新交付。

后续：C3 链完成、WO-1.9.1 交付 S1-S4 全量后，A4-A6 全绿且两个 Maturity Condition 满足（对账完成 + 代表性样本达标）→ Assessment = SATISFIED → A8 签发 Completion(Production-US) → A9 Ledger 迁移 Accepted Current Release: 1.8 → 1.9.1 for Production-US。Production-EU 未交付，其 Accepted Current Release 保持 1.8——partial acceptance 合法（§84、§136）。

红线对照：

```text
若 transfer 验证所需指标管道断裂 → NOT_READY + Gap，高风险下禁止"看起来没事"
推进到 Completion（§110）
若 smoke 全绿但对账周期未完成 → 该 Obligation 保持 NOT_READY，不得触发
Completion（§77、§141）
任何人不得把 US 的 Completion 写成 "Release 1.9 COMPLETED" 不带 Target
Scope（§81），也不得直接改全局 project.current_release（§83）
```

---

# 16. 最终原则

> **目标验证规程的全部意义在于运行事实的成熟度：CI 的绿色、部署的成功、即时的健康都不等于这个 Target 真的达到了交付所需状态。证据缺口是 NOT_READY 而不是失败也不是通过；成熟度未到就如实等待；一个 Target 的真相永远不外推另一个 Target。Completion 一旦签发，Ledger 如实迁移；Closure 是另一篇的事——而真实的运行事实，一刻也不为它等待。**
