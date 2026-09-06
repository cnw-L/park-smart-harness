# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-13 Candidate / Evidence Binding Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-31：组3 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1050 处引用核验 PASS AFTER REPAIR（备注级）；证据见组3 审计报告与横向回归报告）  
> 单一职责：把 Implementation Output 组织成一个**不可歧义、immutable-for-evidence 的 Candidate Baseline**，定义版本化的 Required Verification Set，把每条 Evidence 绑定到明确的 Subject / Context / Definition Revision，按 Candidate Delta ∩ Evidence Dependency Set 判断复用，维护 Coverage Map 并如实区分 FAIL / Evidence Gap / Exception，最终形成 Candidate Verification Assessment 并作出 scope-bound 的 Candidate Acceptance Decision。  
> 边界：Candidate ≠ Engineering Change ≠ Release Baseline ≠ Implementation Revision Set；Coverage Complete ≠ Verification Satisfied；Candidate ACCEPT ≠ Release Authorization ≠ Production Validation；Candidate REJECT ≠ Change 关闭。  
> 结构化镜像：`第五篇-SP13-CandidateEvidenceBinding-OperationContract.yaml`

---

# 1. Trigger

```text
A. 一个有意义 Candidate Scope 所需的 Implementation Output 已形成
   （SP-06 Outputs Ready，分片合法——Candidate Formation 不要求整个 Change 完成，§25）
B. SP-11 / SP-12 移交的 Local / Integration Evidence 到达，需要绑定到 Candidate
C. Candidate 内容发生 Material Change → 形成新 Candidate Revision（C1 → C2），
   需要 Candidate Delta 与 Evidence 复用判断
D. Verification Basis 发生 Material Change（Objective / Pass Basis / Required Context /
   Exception Policy）→ 需要版本化重评
E. Revalidation Trigger 触发（§63）→ 旧 Evidence 适用性重评
F. Evidence / Coverage 齐备（或 Gap / Exception 已处置）→ 进入 Assessment 与
   Acceptance Decision
G. SP-14 Canonical Build 完成（或 Artifact 身份 / Provenance 事实更新）→ Build Facts
   到达，供 Candidate 成员绑定与核验
```

红线：**PASS ≠ Valid Evidence**（§50）；** skipped / quarantined / platform-success 不得自动当作 Required Evidence PASS**（§137）；**不能到 Test FAIL 后悄悄删除 Required Check 让 Candidate 变绿**（§34/§37）。

不触发本规程的情形：

```text
Local / Pre-submit 反馈生产                → SP-11
Review / Integration 决策                  → SP-12
Canonical Build / Artifact Identity 生产   → SP-14（本规程消费其产物作 Candidate 成员）
Release Formation / Delivery Authorization → SP-15（Ch7）
Target Validation                          → SP-17（Ch7）
```

---

# 2. 输入

```text
Ch5 移交包（Ch6 §141 正式接口）  Implementation Output Set + Implementation Revision Set
                                + Design / Work Package Trace + Change-local Feedback
                                + Review / Integration Evidence
                                （含 Shared Baseline Breakage 与处置历史——SP-12 A10）
                                + Known Delegated Verification Concern
                                + Known Exception / Transition Context
SP-14 Build Facts                Canonical Build Result / Artifact Identity（Digest）/
                                Provenance / Materialization Delta 处置状态——Artifact 类
                                成员的绑定与可解析性核验以此为基础（SP-14 A8 移交）
Required Verification 来源       Requirement / Impact / Obligation / Design / Policy（§29）
                                ——不是"项目所有 Test"
Verification 机制与环境           Test / Analysis / Review / Contract Harness / Migration
                                环境 / Representative Environment（§44）
历史 Candidate 与 Evidence Set    C1 → C2 时的 Candidate Delta 判断基础（§57/§105）
Acceptance Policy                Risk / Policy 决定的自动化程度与 Exception Authority（§93/§96）
```

入口再挑战义务（B1 系统性规则）：SP-11 / SP-12 移交证据中的 gate-zeroing 处置——reuse 依据、not-applicable、optional 分类、Quarantine / Evidence Gap 处置、minor-revision 免重审——必须携带可解析理由；不成立的退回来源规程，不得带着未挑战缺口进入 Assessment。

---

# 3. 输出

```text
Candidate Baseline                Candidate ID / Revision + Candidate Scope +
                                  Candidate Manifest（成员不可歧义绑定，不含 Secret）
Required Verification Set         版本化、可追；每项 Obligation 带最低信息（§31）
Candidate Evidence Set            Evidence Record 集：Subject / Context / Definition
                                  Revision / Producer / Result + Validity / Applicability 判断
Verification Coverage Map         Obligation × Disposition 覆盖图（≠ Code Coverage，§67）
Candidate Verification Assessment SATISFIED / FAILED / NOT_READY + 每项 Obligation Disposition
Candidate Acceptance Decision     ACCEPT / ACCEPT_WITH_EXCEPTION / REJECT / DEFER，
                                  绑定 Candidate Revision / Scope / Verification Basis /
                                  Evidence Set（§137）；Known Exception 对 Ch7 可见（§96）
Verification Progress Fact        五要素：Candidate ID / Revision、Acceptance Scope、
                                  Verification Basis Revision、Evidence Set Ref、
                                  Observed / Decided At（§110-111）——不永久覆盖新 Candidate
```

**不输出**：

```text
Release Baseline / Release Decision / Delivery Authorization  → SP-15（Ch7；§21/§95）
Production / Target Validation 结论                            → SP-17（§95/§136）
任何 Current 更新                                              → SP-19
Engineering Change 关闭                                        → SP-19（REJECT 不关闭 Change，§103）
```

---

# 4. 核心语义

**Candidate Baseline `[BASELINE]`（§6-10）**：把"要验证的软件"固定成不可歧义候选状态。Candidate 不是一个 Artifact 的别名（§7）；Candidate Scope 必须显式（§8-9）；Candidate Manifest 列举适用 Source / Artifact / Migration / Config / Contract / Infrastructure 等 Material Member。**Member Binding（§11、§139 [MUST][BASELINE]）**：影响被验证行为的 Material Member 必须绑定不可歧义 Revision / Digest / Version，或使用可事后重新解析当时真实内容的 Version / Time Anchor；`latest`、`current`、裸 branch name 等可变别名不得单独承担 Candidate Identity（§12）。Dynamic Config / Feature State 必须绑定有效状态（§13）；**Evidence Context 必须记录当时实际解析结果**（§14、§140 [MUST][BASELINE]）；Manifest 不含 Secret Value（§15）。

**Immutable-for-Evidence（§18-19）**：Candidate 一旦开始绑定 Material Evidence，不得原地无痕修改；Material Change 形成新 Candidate Revision。Accepted 之后 Manifest 仍保持历史稳定——要修就形成 C2（§102）。成员之间必须 Coherent（§26-27）。

**四组分离（§20-23）**：Candidate ≠ Engineering Change；Candidate ≠ Release Baseline；与第二篇 Release Candidate 的关系保持边界；**Implementation Revision Set 不得直接冒充 Candidate Baseline**（§23、§137）。Feedback Artifact 被纳入 Candidate 必须显式选择绑定（Ch5 §72/§304）。

**Required Verification Set（§28-33）**：在 Candidate Acceptance 前必须明确（§137），来源是 Requirement / Impact / Obligation / Design / Policy（§29）。**Verification Obligation `[BASELINE]`（§30-31）**：可独立判断的 Verification Concern / Objective，最低信息——Obligation ID / Subject·Concern / Verification Objective / Required Evidence·Method Class / Pass·Acceptance Basis / Required Context·Assumption / Authority·Policy / Exception Applicability。Obligation ≠ Test Case（§32：一个兼容目标可由 Contract Test / Consumer Test / Analysis / Review 支撑）；≠ 固定 Test Type Checklist（§33：Risk drives Verification Depth）。

**Verification Basis Change `[BASELINE]`（§34-37）**：Required Set / Objective / Pass Basis / Required Context / Exception Policy 的 Material Change 必须有原因、有 Authority / Decision、有 Revision（§35）。Basis 可以合理演进（§36：发现新 Consumer → Ch3 re-impact → obligation updated → Set expanded），但**不得为让失败消失而静默削弱**（§37）。

**Verification Evidence Record（§38-49）**：Evidence 不只有 Test Result（§39：Analysis / Review / Inspection / Operational Observation 均可）。每条记录：Evidence Subject（不一定是 Artifact Digest，§40-41）、Evidence Context（当次实际解析的 Environment / Config / Workload / Dependency / Tool·Rule Revision·Fingerprint，§42、§140；Context ≠ Candidate Content，§43；Representative Context 要求，§44）、Evidence Definition 与其 Revision（§45-46）、Evidence Producer（§47；Identity 不要求全部加密签名，信任深度按风险，§48）、Evidence Result（§49）。

**Validity / Applicability / Reuse（§50-65）**：PASS ≠ Valid Evidence（§50）；Validity 看 Subject / Context / Definition 匹配与执行可信度（§52），与 Result 分离（§53）；Applicability 是"对当前 Candidate Revision 是否仍适用"，与 Validity 分离（§54-55）。**复用判断 = Candidate Delta ∩ Evidence Dependency Set**（§56-58）：Delta 影响 Evidence 的 Objective / Assumption → re-evaluate / rerun；无 Material Effect → 可复用。既不机械全重跑（§59），也不因"Artifact 没变"全继承（§60：Config 变了行为可能变）。Freshness 不用固定天数，由 Revalidation Trigger / Policy 决定（§62-63）；Performance Evidence 典型 context-sensitive（§64），Unit / Pure Function Evidence 通常更稳定（§65）。

**Coverage / Gap / Exception（§66-80）**：Verification Coverage Map 覆盖所有 applicable Obligation（§66、§137），≠ Code Coverage（§67）；小团队可折叠在 CI / PR（§69）。**Evidence Gap ≠ Verification FAIL**（§72）：Environment failed 未产生有效结论 → NOT_READY / Gap（§73）；Valid Evidence 明确证明违反 → 才是 FAILED（§74）；Tool UI green 也可能是 Gap（§75）。**Verification Exception（§76-80）**：不改写底层 Evidence Result（§77）；最低信息含 Candidate Scope / Authority / Reason / Residual Risk / Recheck 条件（§78、§137）；Exception Applicability 逐项判断（§79）；**不自动继承到新 Candidate**（§80）；不允许例外的 Obligation 不得被 Ch6 自行豁免（§137）。

**Assessment（§81-90）**：三结果——SATISFIED（所有 applicable Obligation 有有效适用 Evidence 或正式 N/A；Exception 单独暴露，不伪装 clean，§83）、FAILED（至少一个 Material Obligation 有 Valid Evidence 证明不满足，§84）、NOT_READY（证据 / 环境 / 定义不足，§85）。FAILED 与 NOT_READY 必须分开——Return Path 不同（§86）。SATISFIED_WITH_EXCEPTION 不作为 Evidence Result——Exception 属 Decision Layer（§87）。**Obligation Disposition `[BASELINE]`（§88）**：SATISFIED / FAILED / EVIDENCE_GAP / NOT_APPLICABLE / EXCEPTION_ACCEPTED，保留底层 Evidence Result。**Coverage Complete（§89）：所有 applicable Obligation 有明确 Disposition——FAIL 也可以 Coverage Complete**；**Candidate Verification Satisfied（§90）：不允许例外的全 SATISFIED + 允许例外的已合法处置 + 无 EVIDENCE_GAP / unresolved Material Finding**。Coverage Complete ≠ Verification Satisfied（§90、§112-114）。

**Acceptance Decision `[BASELINE]`（§92-99）**：复用 Ch1 的 Decision Point / Decision Record / Gate / Authority / Exception，不重建审批系统（§92）；Decision Point ≠ Gate ≠ Human Approval（§115/§143）。可自动化（§93：低风险 automated gate accept；高风险 automated evidence + specialist review + human authority）。四 Outcome：ACCEPT（对当前 Acceptance Scope 满足 Candidate-level Verification / Policy，§95）/ ACCEPT_WITH_EXCEPTION（Policy 允许 + Authority 合法 + Residual Risk 显式接受；Known Exception 必须对 Ch7 / Release Decision 可见，§96）/ REJECT（Valid FAIL / unacceptable known defect / non-waivable obligation 未满足，§97）/ DEFER·NOT_READY（证据不足或依赖未就绪，不表示已被证明错误，§98）。**Acceptance 必须有 Scope**（§99）：accepted for integration verification / delivery preparation scope，不自动升级为 whole change accepted / production accepted。

**Known Material Finding（§100-101）**：不只看 Test Green——已知 Critical Data Defect / Security Finding / Contract Violation 即使没被当前 Test 捕获，也必须先处置（Resolved / Not Applicable with reason / Accepted Exception / Blocking）才能进入 Decision。

**Reject 与复用（§103-105）**：Candidate REJECT 不关闭 Engineering Change——Change 保持 OPEN / ACTIVE 进入 Rework；Return Path 按 Finding：Implementation Defect → Ch5 / Design → Ch4 / New Impact → Ch3 / Requirement Gap → Ch2 / Evidence Gap → Ch6 / Infra·External Wait → Ch6·Block（§104）。C2 可以复用 C1 的部分 Evidence——但必须做 Applicability 判断（§105、§137）。

**Evidence Set 与 Progress Fact（§106-111）**：Candidate Evidence Set 汇集支撑 Decision 的证据（§106-107）；Integrity / Provenance 深度按 Supply-chain / Audit Risk 裁剪，SLSA 是可选增强模式而非普遍要求（§108-109、§137 SHOULD）。Verification Progress Fact 带 Candidate Revision / Basis Revision / 时间，**不永久覆盖新 Candidate**（§110-111）。

---

# 5. Engineering Actions

## A1 — 确认 Candidate Formation 入口

核验 Ch5 移交包齐备（Ch6 §141 接口清单）且 Candidate Scope 有意义——分片 Candidate 合法（§25），但 Partial Candidate 不得冒充 Whole Change。执行 B1 再挑战：上游证据包中的 reuse / optional / gap / 免重审等 zeroing 处置无理由的退回来源规程。

## A2 — 定义 Candidate Scope

显式写出：本 Candidate 覆盖哪些 Change 内容、哪些 Material Member 面（Source / Artifact / Migration / Config / Contract / Infrastructure）、不覆盖什么。Scope 是后续 Acceptance 声明的边界——Acceptance Claim 不得超出 Candidate Scope（§137）。

## A3 — 组成 Candidate Manifest 与 Member Binding

枚举 Material Member 并逐一绑定：不可歧义 Revision / Digest / Version，或可事后重新解析当时真实内容的 Version / Time Anchor（§139）。可变别名（`latest` / `current` / 裸 branch name）不得单独承担成员身份（§12）。Dynamic Config / Feature State 绑定有效状态（§13）。Manifest 不含 Secret Value（§15）；按 Supply-chain / Audit Risk 决定是否生成 Manifest Digest（§16 为风险条件项，小团队不强制；高风险时必须）与 Candidate ID / Revision（§17）。Artifact 类成员的 Identity / Provenance 由 SP-14 规程产物提供，本规程负责绑定与核验其可解析性。

## A4 — 建立 Immutable-for-Evidence 与 Coherence

自首条 Material Evidence 绑定起，Candidate 内容冻结：任何 Material Change（Source / Artifact / Migration / Config / Contract）形成新 Candidate Revision，不原地修改（§18-19、§102）。核验成员间 Coherence（§26：如 Code 依赖的新字段由绑定内的 Migration 提供；反例 §27）。

## A5 — 定义 Required Verification Set

按 §29 来源逐项推导 Obligation（Requirement / Impact / Obligation / Design / Policy），每项写明 §31 最低信息。以 Verification Objective 思考，不以 test type checklist 思考（§32-33）：Logic Bug 可能只需 focused regression；Migration 可能需要 migration + existing data + compatibility + recovery。深度由 Risk 驱动。

## A6 — 版本化 Verification Basis

Required Set 定型即版本化（§34）：团队在对 C1 开始 Verification 前必须知道"打算用什么标准判断 C1"。Basis 演进走显式路径（§36：如 re-impact → obligation updated）；任何 Material Basis Change 记录原因 + Authority / Decision + Revision（§35）。**FAIL 后静默删除 Required Check 是红线违规**（§37）。

## A7 — 绑定 Evidence

每条 Evidence 形成 Evidence Record：Subject（明确到 Candidate Revision 内成员；不限 Artifact Digest）、Context（当次实际解析结果——Environment / Config / Workload / Dependency / Tool·Rule 的 Revision / Fingerprint，§140；可变 Context Alias 不得替代）、Definition + Revision（Test 本身被改，旧 PASS 不能解释新 Oracle）、Producer、Result。Evidence 类型不限 Test——Analysis / Review / Inspection / Observation 按 Objective 适配（§39）。非 Representative Context 产生的 Evidence 标注其代表性限制（§44）。

## A8 — 判定 Validity 与 Applicability，决定 Reuse

对每条 Evidence 两问分开回答：**Valid 吗**（Subject / Context / Definition 匹配、执行可信——与 Result 无关，§53）？**对当前 Candidate Revision 仍 Applicable 吗**（§54-55）？C1 → C2 时按 Candidate Delta ∩ Evidence Dependency Set 逐项判断（§58）：影响 Objective / Assumption → rerun / re-evaluate；无 Material Effect → reuse 并记录依据。两个极端都禁止：任何变化全重跑（§59）、Artifact 未变全继承（§60）。Performance 类 Evidence 默认 context-sensitive 需重评（§64）；稳定单元证据可复用（§65）。Revalidation Trigger 触发时同样走此判断（§63）。

## A9 — 维护 Coverage Map，区分 FAIL / Gap / NOT_READY

Coverage Map 覆盖所有 applicable Obligation（可折叠在 CI / PR，§69）。每项 Obligation 的状态如实登记：

```text
Valid FAIL        有效证据明确证明不满足 → FAILED（§74）
Evidence Gap      环境失败 / 工具失败 / skipped / quarantined / 错 Subject /
                  错 Context / 定义未决 → NOT_READY，不是 FAIL（§72-73）
Tool UI green     不等于证据覆盖（§75）——skipped-but-success 计入 Gap
```

## A10 — 处置 Verification Exception

Exception 属 Decision Layer，永不改写底层 Evidence Result（§77）。最低信息：Candidate Scope / Authority / Reason / Residual Risk / Recheck 条件（§78、§137）。逐项判断 Exception Applicability（§79）；**不允许例外的 Obligation 不得豁免**（§137）；Exception 不自动继承到新 Candidate Revision（§80）。

## A11 — 形成 Candidate Verification Assessment

汇总每项 Obligation Disposition（§88 五候选，保留底层 Result）：

```text
SATISFIED   所有 applicable Obligation 有有效适用 Evidence 或正式 N/A；
            存在 Exception 时单独暴露，不得伪装 clean（§83）
FAILED      至少一个 Material Obligation 被 Valid Evidence 证明不满足（§84）
NOT_READY   证据 / 环境 / 定义尚不足（§85）——与 FAILED 分开，Return Path 不同（§86）
```

Coverage Complete（全有 Disposition）与 Verification Satisfied（§90 条件）分开陈述；FAIL 也可以 Coverage Complete（§89）。

## A12 — 作出 Candidate Acceptance Decision

Decision Point 复用 Ch1 机制（§92）；自动化程度由 Risk / Policy 决定（§93）。Decision 绑定：Candidate Revision + Acceptance Scope + Verification Basis Revision + Evidence Set（§137）。Outcome 四选一（§94-98）；ACCEPT_WITH_EXCEPTION 必须让 Ch7 / Release Decision 看到 Known Exception（§96）；决策前确认 Known Material Finding 全部处置（§100-101）。产出 Verification Progress Fact（§110 五要素：Candidate ID / Revision、Acceptance Scope、Verification Basis Revision、Evidence Set Ref、Observed / Decided At）——不覆盖未来 Candidate。REJECT 时按 §104 Return Path 路由，Change 保持 OPEN / ACTIVE（§103）。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| A1 入口核验 | Guardrail + B1 再挑战 |
| A2 Scope 定义 | Engineering Decision |
| A3 Manifest / Binding | Automation-assisted + Guardrail（别名红线机械） |
| A4 Immutable / Coherence | Guardrail |
| A5 Required Set 定义 | Engineering Decision（Risk 驱动） |
| A6 Basis 版本化 | Guardrail + Authority（Change 需 Decision） |
| A7 Evidence 绑定 | Automation（记录自动产生） |
| A8 Validity / Reuse 判断 | Engineering Decision（工具可发起挑战，结论留人） |
| A9 Coverage / Gap | Guardrail（分类规则机械） |
| A10 Exception | Authority + Engineering Decision |
| A11 Assessment | Guardrail（语义机械） |
| A12 Acceptance Decision | Decision Point：automated / specialist+human / hybrid，按 Risk·Policy |

Hard Gates：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP13-01 Candidate Scope / Revision 明确；Manifest 能不可歧义识别
                     所有 Material Member（§137）
[MUST NOT][BASELINE] G-SP13-02 可变别名（latest / current / 裸 branch）单独承担
                     Candidate Identity 或 Evidence Subject Identity（§12/§139）
[MUST NOT][BASELINE] G-SP13-03 原地无痕修改已绑定 Material Evidence 的 Candidate；
                     Material Change 必须形成新 Revision（§18-19/§137）
[MUST NOT][BASELINE] G-SP13-04 用 Implementation Revision Set 直接冒充 Candidate
                     Baseline；Feedback Artifact 未经显式选择成为成员（§23/§137，Ch5 §72/§304）
[MUST][BASELINE]    G-SP13-05 Required Verification Set 在 Acceptance 前明确且版本化；
                     不得因 Test FAIL 静默删除 Obligation（§34/§37/§137）
[MUST NOT][BASELINE] G-SP13-06 在 Subject / Context / Definition 不匹配时把 PASS Result
                     用于 Acceptance（§50/§137）
[MUST NOT][BASELINE] G-SP13-07 机械全重跑或机械全继承——Reuse 必须由 Candidate Delta ∩
                     Evidence Dependency Set 支撑（§58-60/§137）
[MUST NOT][BASELINE] G-SP13-08 把 skipped / quarantined / platform-success 自动当作
                     Required Evidence PASS（§75/§137）
[MUST NOT][BASELINE] G-SP13-09 用 Exception 改写底层 Evidence Result；Ch6 自行豁免
                     不允许例外的 Obligation（§77/§137）
[MUST][BASELINE]    G-SP13-10 Assessment 区分 SATISFIED / FAILED / NOT_READY；
                     Evidence Gap ≠ FAIL，Environment failed = NOT_READY（§72-74/§86/§137）
[MUST][BASELINE]    G-SP13-11 Known Material Finding 全部处置后才进入 Acceptance
                     Decision（§100-101/§137）
[MUST NOT][BASELINE] G-SP13-12 ACCEPT 超出 Candidate Scope、升级为 Release Authorization /
                     Production Validation；REJECT 关闭 Engineering Change（§95/§99/§103）
```

---

# 7. PASS Exit

本规程完成 = **一个 Candidate Revision 的 Acceptance Decision 已真实作出并记录**：

```text
[ ] Candidate Manifest 绑定完整、Coherent、immutable-for-evidence
[ ] Required Verification Set 版本化；Coverage Map 覆盖所有 applicable Obligation
[ ] 每项 Obligation 有明确 Disposition（五候选之一），底层 Evidence Result 保留
[ ] Assessment 语义正确（SATISFIED 不伪装 clean；FAILED 与 NOT_READY 分开）
[ ] Known Material Finding 全部处置；Exception（若有）信息完整且对 Ch7 可见
[ ] Decision 绑定 Candidate Revision / Scope / Basis / Evidence Set；
    Verification Progress Fact 已产出
```

DEFER / NOT_READY 与 REJECT 都是合法的真实结论——规程完成不等于 ACCEPT。

**完成不代表**：Release Authorized / Deployed / Production Validated（SP-15 / SP-17）/ Change Closed（SP-19）/ 任何 Current 更新。

---

# 8. Evidence

Evidence by Work：小团队可用 CI Required Checks + PR / Test Report 承载 Coverage / Evidence（§137 SHOULD），不建专用平台。天然载体：CI 记录、Test Report、Manifest 文件、Decision Record（Ch1）。必须显式产生的：

```text
- Candidate Manifest + Digest（含 Member Binding 与 Context 快照指针）
- Required Verification Set 版本记录与 Basis Change 记录
- Evidence Reuse / Applicability 判断依据
- Exception 记录（Scope / Authority / Reason / Residual Risk / Recheck）
- Known Material Finding 处置记录
- Acceptance Decision Record（绑定四要素）
```

---

# 9. Current Update Obligation

```text
writesCurrent: false
```

Candidate Acceptance 不更新任何 Current——它只是"该 Candidate Revision 可进入下一 Delivery / Release Preparation Decision"的 scope-bound 事实（§92/§95）。Accepted Candidate 后续经 SP-15 / SP-17 成为目标环境事实，Current 提交统一走 SP-19 通道；本规程产出的 Evidence Set 与 Progress Fact 是 SP-19 校准的 Actual Evidence Ref 候选。

---

# 10. FAIL / Return Path

```text
Assessment FAILED     → 按 Finding 路由（§104）：
                        Implementation Defect → SP-06（Ch5）；Design → SP-05（Ch4）；
                        New Impact → SP-04（Ch3）；Requirement Gap → Requirement（Ch2）
Assessment NOT_READY  → 补 Evidence / 修 Verification Infrastructure / Wait / Block（§86）
                        ——Environment / Infra 未就绪不证明 Candidate 错误（§98）
REJECT                → Change 不关闭，进入 Rework；新 Candidate（C2）按 §105 复用判断
Basis 需削弱           → 显式 Verification Basis Change（§35-36）；静默削弱是红线（§37）
```

---

# 11. Exception / Alternative Path

## 11.1 Partial Candidate

Change 未完成全部 WP 时可对有意义分片形成 Candidate（§25）；Scope 必须显式声明其分片边界，Acceptance 不外推为 Whole Change Accepted。

## 11.2 Automated Acceptance

低风险 Change：Manifest immutable + all required checks valid + no blocker → automated gate accept（§93）。自动化的只是 Decision 执行，Obligation 定义、Exception、Known Finding 处置的语义一项不省。

## 11.3 Emergency

Ch8 fast-path 压缩 Candidate 验证深度时必须记录压缩范围与残余风险；Emergency 不得建立另一套不留 Evidence 的机制（Ch7 §144 同旨）；事后经 SP-21 / SP-19 对账。

## 11.4 轻量 Coverage 载体

小团队把 Coverage Map 折叠在 CI / PR 中（§69、§137 SHOULD）；折叠的是载体不是语义——每项 Obligation 的 Disposition 仍必须可解释。

---

# 12. Theory Trace

```text
第一篇  GI-03 / GI-05 / GI-13；Ch1 Decision Point / Gate / Authority / Exception 复用
第二篇  Testing / Verification WHAT；Build / Release WHAT 边界（§2）；
        Release Candidate 关系边界（§22）
第三篇  Build / Runtime refs 作为 Evidence Context
第四篇  Ch6 全章（§6-115 定义与 §137-140 最低要求）；
        Ch5 §72/§304（Feedback Artifact 显式选择）；
        Ch6 §141（与第五章的正式接口——Ch5 移交包七成员）、
        Ch6 §142（与第七章的正式接口——ACCEPT ≠ Release Authorized；
        Ch7 §143 同旨）；Ch8（Emergency）
```

Theory Trace 只说明受哪些理论约束；本规程不复制理论正文，不成为第二份 Authority。

---

# 13. Executable Asset References

```text
EA-08 Verification Harness    确定性执行的 contract / migration harness（Repeatable）
EA-10 Build Definition        Candidate Artifact 的可复现构建（与 SP-14 衔接）
EA-11 Provenance              高 Supply-chain / Audit Risk 时的 Digest / Attestation（§108-109）
EA-07 Reusable CI             Required Checks / Coverage 折叠载体
```

工具适合：绑定记录自动产生、Coverage Map 维护、Applicability 挑战发起、自动化 gate。工具不适合：Obligation 定义、Reuse 结论、Exception 批准、Known Finding 处置、非低风险 Acceptance 决策。

---

# 14. Reference Profile Bindings

```text
通用层        Operation Contract / Theory Trace / Evidence 语义 / Control 语义——全 Profile 共用
Delivery Shape  决定 Candidate 成员构成（如 CLI 的跨平台 Artifact 集、SDK 的多语言包）
Risk Overlay    决定 Obligation 深度、Provenance 深度（§108）、Acceptance 自动化程度（§93）
```

具体 Profile 绑定在组6 RP 补齐时登记；本规程不预留学生位。

---

# 15. Example

**CHG-WO-142 / Candidate C1 → C2（Ch6 WorkOrder §116-136）。**

A1-A4：WP-1 / WP-2 / WP-3 就绪后形成 C1：Manifest 绑定 backend artifact Y（@commit SHA，Digest 由 SP-14 提供）、migration V203、contract bundle C9（Digest）、search mapping S5、config snapshot P2——无 `latest`。Coherence 核验通过。

A5-A6：Required Verification Set v1：VO-CONTRACT-1（old consumer + new provider 语义兼容——由 Contract Test + Consumer Test 支撑，§32）、VO-MIGRATION-1（expand 迁移 + existing data）、VO-PERF-1（搜索 p99 回归）、VO-FUNC-1（transfer flow focused regression）。

A7-A9：E1（Contract Test）绑定 Subject=C1 contract bundle C9、Context=实际解析的 consumer matrix 版本；E3（migration smoke）PASS；E5（perf）记录 Workload 指纹。E6（VO-FUNC-1 的 transfer flow focused regression）执行环境失败——**Environment failed = Evidence Gap / NOT_READY，不是 FAIL**（§73）；E6 后来在 Representative Environment 执行并 FAIL（valid FAIL，§74）。Assessment(C1) = FAILED。

A12：REJECT(C1)——Change 不关闭，回 SP-06 修复。修复后形成 **C2**（新 Revision，C1 Manifest 历史不动，§102）。

A8 复用判断：Candidate Delta = 仅 transfer logic 修复。Contract Test（E1）→ reuse（Delta ∩ Dependency Set 无 Material Effect，依据记录）；Migration → reuse if unaffected；Search Performance → rerun / re-evaluate（context-sensitive，§64）；VO-FUNC-1 → rerun。若此时才想起把 Security Scan 从 Required Set 删掉让 C2 变绿——**红线**（§37）：削弱必须走显式 Basis Change。

A12：C2 全 Obligation SATISFIED、无 Gap、无未处置 Finding → ACCEPT(C2) **for delivery preparation scope**——不是 Release Authorized，不是 Production Validated。

反例对照（§131-136 同例）：Wrong Environment PASS 不得用于 Acceptance（§133）；Known Critical Finding 未被 Test 捕获也必须先处置（§135）；Candidate Accepted 后 Production FAIL 属 Ch7 范畴（§136）——本规程的 ACCEPT 从未承诺那种事。

---

# 16. 最终原则

> **Candidate 的全部意义在于"被验证的是谁"不可歧义：成员绑定到不可变的真实内容，证据绑定到真实的 Subject / Context / Definition，判断标准在验证开始前就版本化。FAIL 与 NOT_READY 分开，Gap 与 Exception 分开，Coverage Complete 与 Satisfied 分开，ACCEPT 与 Release Authorized 分开——每一次"差不多算过"都是对未来 Production 事故的预支。而 REJECT 一个 Candidate 从不关闭 Change：被拒绝的是这个候选事实，不是变更本身。**
