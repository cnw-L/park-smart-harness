# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-19 Calibration / Current Update / Change Closure Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-31：组3 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1050 处引用核验 PASS AFTER REPAIR（备注级）；证据见组3 审计报告与横向回归报告）  
> 单一职责：把一个 Engineering Change 的实际结果受控地校准成 truthful Current——对 Actual Result 与 Accepted Basis 的 Material Delta 给出明确 Disposition，把每个适用 Current Transition Obligation 真实提交到正确 Authority（或确认保持不变 / 受控过渡 / 正式转移 / 不再适用），证明 Scoped Current Update Completeness，并在 Closure Basis 最后一刻仍适用时作出 Closure Decision（OPEN → CLOSED + Terminal Disposition）。  
> SP-19 是 Calibration 与 Change Closure 的唯一规程，也是绝大多数 Baseline Kind 的 Current Commit 执行处；Release / Runtime 类 Current Transition 由 Ch7 规程（SP-15 / SP-17）在 Authority 背书下于执行期提交，SP-19 核验其 Commit Fact 而不重复提交。  
> Closure ≠ 第一次 Current Update；Actual Reality ≠ Current Authority；Ledger ≠ Authority Commit；Release Completion ≠ Change Closure。  
> 结构化镜像：`第五篇-SP19-CalibrationCurrentUpdateChangeClosure-OperationContract.yaml`

---

# 1. Trigger

```text
A. Change 走完其适用执行路径（Implement / Candidate / Release / Target Validation），
   需要最终 Calibration 与 Closure
B. Ch8 特殊生命周期（Emergency / Cancellation / Supersession / Long-running / Partial）
   前置条件完成后进入 Closure（前置由 Ch8 负责，SP-19 不补做）
C. Calibration 单独触发：Drift / Structure Health Finding 需要 Current 校准
   （经显式 Change 进入，GI-03；通常先走 SP-03 建立修复 Change）
D. Closure Revalidation 发现 Material Change →  reconcile 后重进本规程
```

红线：**没有 Closure Accountability Scope 的最终对账，不得形成 Closure Obligation Set**（§32 Reconciliation Barrier）；Initial Scope ≠ Closure Accountability Scope。

---

# 2. 输入

```text
Change Record（OPEN，含完整历史：Starting / Working Baseline、Impact、Design、
  Candidate、Release、Ch8 Residual / Transfer 记录——按实际路径适用）
Final Accepted Responsibility       最终被接受的 Requirement / Design / Decision 集合
Actual Result Set                   Source / Artifact / Migration / Runtime / Data /
                                    Structure / Deployment / Validation / Recovery
                                    Evidence Ref——不是"开发说已经做完"
Earlier Current Transition Facts    执行期已成立的 Current Transition
                                    （如 Requirement R2、Accepted Release 1.9），
                                    保留真实发生时间，不得伪造为"刚刚更新"
Ch8 特殊生命周期前置（适用时）        Fence / Transfer / Emergency Reconciliation 完成证据
```

每个 Calibration Subject 的最低字段（第四篇 Ch9 §11）：

```text
Change ID / Baseline Kind / Baseline Scope / Subject·Concern
Accepted Basis Ref / Actual Evidence Ref / Authority Ref
```

---

# 3. 输出

```text
Calibration Record                  每 Subject：Delta 分类 + Disposition + 证据
Current Transition Commit Fact      Authority 真实生效的 resulting revision / state
Current Baseline Transition Ledger  可导航的 From→To/Unchanged + Authority + Evidence
                                    + Effective Time + Trigger Change 记录
Scoped Current Update Completeness  五维度完整性判定（Progress Fact）
Closure Basis                       可追快照 / Reference Set（引用而非复制）
Closure Decision                    Record State OPEN → CLOSED + Terminal Disposition
                                    （COMPLETED / REJECTED / CANCELLED / SUPERSEDED，
                                     沿用 Ch1，不新增终态）
```

SP-19 **不输出**：

```text
Candidate Acceptance / Required Verification 结论（Ch6 / SP-13）
Release / Target Validation 执行（Ch7 / SP-15 / SP-17）
Fence / Transfer / Emergency Reconciliation（Ch8；SP-21 pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5）
对 WHAT 的新定义（Requirement / Contract / Data 长什么样不归本规程决定）
```

---

# 4. 核心语义

```text
Closure ≠ First Current Update           执行期已成立的 Transition 保留真实时间
Actual Reality ≠ Current Authority       Observed 更接近现实也不自动成为 Authority
Calibration ≠ 让文档机械迁就代码          也不让代码机械服从过时文档
Permitted Variance ≠ Material Delta      私有实现细节不改 Authority-level 语义
Ledger ≠ Authority Commit                Ledger 只引用事实，不能制造事实
Completeness ≠ 全球同版                   各 Baseline Scope 各自 truthful 即可
Truthful Current ≠ Zero Finding          但 Finding 必须有 Owner / Disposition / Exit
Truthful Transition ≠ 无剩余责任          Exit 责任仍归本 Change 就不得 Closure
Candidate REJECTED ≠ Change REJECTED     前者是 Ch6 候选事实，后者是终态 Decision
Release Completion ≠ Change Closure      第七章完成不等于本 Change 责任结束
Closure Basis 会过期                      最终关单前必须 Revalidation
CLOSED ≠ 历史可被改写                     后续新发现走新 Finding / Incident / Change
```

---

# 5. Engineering Actions

## A1 — 确认 Closure Entry 前提并形成 Closure Accountability Scope

核验 Ch8 前置（适用时）：Emergency 的 Deferred Obligation / Temporary Mitigation / Evidence Gap 已处置；Cancellation 的 Fence / In-flight / Residual 已处置；Supersession 的 Transfer Map / Successor Rebind 已完成。缺失 → 回 Ch8 路径，**不得用 Closure Checklist 掩盖**（§3、§77、§107）。

[MUST][BASELINE] 形成 Closure Accountability Scope（§28）：

```text
= Final Accepted Change Responsibility
+ Material Actual Reality caused / owned by Change
+ Applicable Current Transition Obligation
+ Transition / Exception / Cleanup / Residual Responsibility
- Validly Transferred Responsibility
- Authoritatively No-longer-applicable Responsibility
```

历史（Starting Scope / Initial Impact / Old Design Scope）保留不改写（§29）。执行 Closure Current Obligation Reconciliation Barrier（§32）：把 Initial / Accepted Scope 与 Material Actual Reality、late Finding、Delivery / Recovery Reality、Ch8 Residual Register 做最终对账——任何本 Change 已造成或仍负责的 Material Reality，不得因"最初没写在 Scope"而消失。特别检查：Data / Config / Migration / External Side Effect / Feature Flag / Runtime Mapping / Partial Delivery / Cleanup（§54）。

## A2 — 形成 Applicable Current Transition Obligation Set

对每个 Baseline Kind + Scope（§33：Requirements / Design / Module / Contract / Data / Structure / Development Integration / Runtime / Accepted Release / Active Transition / Maintenance——不要求全含），综合以下来源决定义务（§31）：

```text
Accepted Requirement / Change Decision
Impact Assessment / Engineering Obligation
Accepted Design / Target / Transition
Actual Implementation / Candidate
Release / Runtime / Recovery Result
Calibration Material Delta
Ch8 Residual / Transfer
执行晚期新发现的 Material Fact
```

[MUST][BASELINE] 执行期已成立的 Current Transition（如 Requirement R2、Runtime 1.9、Accepted Release）**确认其 Commit Fact 已成立且仍适用即可，不得重复伪造为"刚刚更新"**（§34-36）。

每个 Obligation 的可结束语义（§37）：

```text
CURRENT_COMMITTED
UNCHANGED_CONFIRMED
CONTROLLED_STATE_EXPLICIT（+ responsibility transferred / retained elsewhere）
TRANSFERRED
NO_LONGER_APPLICABLE_BY_AUTHORITY
```

以下一律不算完成：`TODO later` / `Docs pending` / `Someone knows` / `Ticket linked but successor not accepted` / `Ledger says updated but Authority still old` / `Exception exists but no owner/exit`。`UNCHANGED` 是合法结果（§38）；小 Change 不机械记录所有未影响 Baseline。

## A3 — 建立 Calibration Subject Set

Calibration 不是全局 Boolean（§10）。按 `Subject + Baseline Kind + Baseline Scope + Concern + Basis + Result` 拆 Subject（如 `Production-US / Runtime / Release`、`Development / Module Structure`），每 Subject 带 §2 最低字段。

复核上游使 Gate 归零的处置（各层 N/A / DELEGATED / Non-blocking / Known-defect=0）Rationale / Evidence 可解析；发现伪装 → 回来源规程挑战，不得静默继承。

## A4 — 执行 Actual vs Accepted 受控比较

对每个 Subject：取 Accepted Basis（§12：Current Requirement / Accepted Change Design Revision / Current·Target Contract / Current Data Baseline·Migration Decision / Current·Target Structure / Candidate Acceptance / Release Baseline / Target Release Completion / Authorized Transition·Exception——九个来源按 Subject 适用），取 Actual Result Set（§13：可证明实际长期工程结果的 Evidence Ref 集合——不是口头声明），比较形成 Calibration Delta（§15）。

[MUST][BASELINE] Evidence 不足（实际部署了谁 / Migration 是否 commit / Runtime 是否 mixed / 哪个 Contract 正被消费——无法确认）时，不得 assume aligned；保持 `EVIDENCE_GAP / NOT_READY` 并补 Evidence / Reconciliation（§25）。

## A5 — 分类 Delta 并给出 Calibration Disposition

语义型 Disposition 词汇表（§18-26）：

```text
ALIGNED                          Actual 实质符合 Accepted Basis
PERMITTED_VARIANCE               差异真实但在 Accepted Design Freedom 内；
                                 不改 Authority-level Meaning，必要时留 rationale
CONTROLLED_TRANSITION            Actual 处于已接受 Transition 中
                                 （Owner / Scope / State / Exit / Remaining Obligation 齐全）
VALID_EXCEPTION                  存在有效 Exception
                                 （Authority / Scope / Reason / Risk / Expiry / Recheck）
FIX_REALITY / REWORK             Actual 违反仍有效 Accepted Basis → 按原因返回：
                                 new impact→Ch3 / invalid target·design→Ch4 /
                                 implementation defect→Ch5 / candidate·evidence→Ch6 /
                                 delivery·runtime→Ch7 / special lifecycle residual→Ch8
UPDATE_ACCEPTED_AUTHORITY        实际变化合理·必要·长期 → 必须先经该 Concern 真实
                                 Authority 的 Decision 并完成适用 Impact / Verification，
                                 然后才 Update Current（§24）；不得 Actual→Current 直达
EVIDENCE_GAP / NOT_READY         见 A4
CONTEXT_RECONCILIATION_REQUIRED  Calibration 期间相关 Current 被并发 Change 改变
                                 → rebind latest → 重比 Delta → 按需 re-impact / re-calibrate
```

Material Delta 判定（§17）：改变 Requirement Behavior / Module Responsibility / Public Contract / Data Meaning·Authority / Security·Trust Boundary / Long-lived Structure / Runtime·Deployment Boundary / Migration·Compatibility / Recovery Direction / Verification Obligation / Supported Release Reality 之一的差异是 Material，不得用 "implementation detail" 掩盖；反之，不改变公共边界的私有实现选择是 Permitted Variance，不强迫 Current Design 追踪私有细节（§16、§20）。

## A6 — Authority-backed Current Commit（Commit Guard + Commit Barrier）

对每个 `CURRENT_COMMITTED` 目标，提交前执行 **Current Update Commit Guard**（§42-43）：

```text
Expected Current Revision still current?
Authority source still same?
Baseline Scope still same?
Requirement / Design Decision still applicable?
Concurrent Change produced material delta?
Transition / Exception basis changed?
```

并发无 Material Effect（如只改无关 README / unrelated module）→ 记录 no material effect，允许 rebase / commit，不要求全量重做（§44）。并发有 Material Effect（改了同一 Contract / Data Authority / Runtime Mapping / Target Scope）→ **STOP stale update**，Context Reconciliation 后按需回 Ch3 / Ch4 / Ch6 / Ch7 / Ch9（§45）。乐观并发可用 expected revision / compare-and-set / ETag / generation / manual recheck 实现，规范不强制技术（§46）。

[MUST][BASELINE] 提交结果必须能解析 Authority Confirmation（§47）：Baseline Kind / Scope / Previous Authority Revision / Resulting Authority Revision·State / Effective·Accepted At / Decision·Evidence / Trigger Change / Transition·Exception Ref（适用）。结果为 `FAILED / UNKNOWN / CONFLICTED` → 保持 `NOT_COMMITTED`，**不得进入 Closure**（§48 Authority-backed Current Commit Barrier：Change-local Ledger / Checklist / PR Description 只能引用该事实，不能自己制造或证明 Authority Commit）。

## A7 — 记录 Current Baseline Transition Ledger

Authority-backed Transition Fact 成立**之后**，在 Ledger 中记录 / 引用（§41）。Ledger 可导航：From / To·Unchanged / Scope / Authority / Decision·Evidence / Effective Time / Trigger Change / Transition·Exception（§60），但不复制专项 Authority 全部内容，更不是所有 Current 的 Ultimate Authority。

## A8 — Truthful Current 与 Cross-Baseline Coherence 检查

Truthful Current Barrier（§49）：存在已知 Material Actual Reality 与对外导航的 Current / Transition / Exception 表达冲突，且无有效 Authority Update / 受控 Transition·Exception / Finding+accepted follow-up / 真实 Recovery 解释 → 不得声明 Completeness。

Current 可以 health-affected（Accepted Current + Health Finding 并存合法，§50），但导航入口必须可见 Mismatch / Owner / Disposition / Successor·Exit。

Cross-Baseline Coherence（§61）：同一 Scope 下相关 Current 必须实质一致，或被受控 Transition / Exception 显式解释（如 Accepted Release 1.9 与 Current Contract C7 不兼容且无解释 → Completeness FAIL）。Cross-Scope 差异（Development S20 / Production S18 / Legacy S16）只要 Scope 与责任清楚即合法（§62）。

## A9 — 判定 Scoped Current Update Completeness

五维度核验（§53-60，Guardrail 可自动核验存在性 / 可解析性，充分性结论归 Engineering Decision）：

```text
1. Scope completeness                 没只看 initial scope，无漏掉的 late material reality
2. Authority completeness             每条 Current Statement 的 Authority 可解析；
                                      不得"README 比 Registry 新就信 README"（§55）
3. Reality / Evidence completeness    Evidence Gap 存在 → NOT_READY
4. Transition / Exception / Residual responsibility completeness
                                      Owner / Scope / Exit·Expiry / Remaining Obligation /
                                      Responsibility holder 齐全
5. Ledger / Trace completeness        Ledger 可导航到真实 Commit Fact
```

Transition Responsibility Barrier（§58-59）：Active Transition 是 truthful Current fact ≠ 本 Change 无剩余责任。Exit / Expiry / Cleanup 责任仍由本 Change 承担 → Change 保持 OPEN；只有 Exit 完成或责任被明确 Successor / Maintenance Owner **可追接受**后才不阻断 Closure。

## A10 — 形成 Closure Obligation Set 与 Closure Basis

Closure Obligation Set（§63）：Closure Accountability Scope 下，本 Change 关闭前仍须完成 / 转移 / Authority-based no-longer-applicable / 证明已被 earlier Transition 满足的 Calibration、Current Update、Residual、Transition、Exception、Finding、Evidence、Decision 与 Cleanup 责任集合。

Closure Basis（§64-65）：支持 Closure Decision 的可追快照 / Reference Set——Final Accountability Scope / Terminal Disposition / Calibration Result / Completeness / Residual Transfer·N-A Decision / 关键 Evidence·Authority / 有效时间。**引用** Candidate Evidence Set / Release·Target Validation / Ledger / Calibration Record / Successor Acceptance，不复制全部日志进 Ticket。

Technical Debt / Finding 边界（§78-81）：Closure 不要求 finding_count = 0 或 debt = 0；但每个 Known Finding / Debt 必须判断——是否违反仍有效 Accepted Obligation / 是否仍由本 Change 承担 / 是否影响 Current Truth / 是否 Gate-Relevant / 是否已有独立可追被接受的后续责任。**未满足的 Requirement / Contract / Data / Security / Transition Obligation 不得改名为 Technical Debt 绕过 Closure**（§79），除非 Requirement Authority 正式改变或剩余义务被 accepted successor 有效承接。

## A11 — Closure Revalidation 与 Closure Decision

Closure Readiness 最低条件（§66，Guardrail 核验）：

```text
Closure Accountability Scope complete
Calibration material subjects dispositioned
Scoped Current Update Completeness satisfied
No unresolved blocking Evidence Gap
No active obligation retained by this Change
Ch8 special lifecycle prerequisites satisfied（适用）
Closure Basis still applicable
```

[MUST][BASELINE] 最终 OPEN→CLOSED 前执行 Closure Revalidation Barrier（§67-68）：重新确认 Closure Basis 依赖的 Material Current / Authority / Requirement·Design Decision / Evidence Applicability / Transfer Acceptance / Transition·Exception / Residual 没有失效变化。无关变化（只改 unrelated docs）→ No Material Effect → 可关，不要求全量重测（§69）；Material Change → Reconcile 后重新决定。

Closure Decision（§70）确定 Terminal Disposition，**沿用 Ch1 四个终态，不新增**（§71）：

```text
COMPLETED    最终 Accepted Responsibility 已实现·验证·交付·校准到适用范围；
             Current Transition 责任已完整处置；无本 Change 仍承担的 Material Residual
             ——不表示系统零 Bug / 零 Debt / 未来不再有 Change（§72）
REJECTED     Change 本身经 Authority Decision 不再继续，且已产生的实际 Side Effect /
             Current·Transition·Residual 责任已处理完成（§74）
             ——Candidate C1 REJECT → C2 只是 Ch6 候选事实，≠ Change REJECTED（§73）
CANCELLED / SUPERSEDED   以 Ch8 前置完成为前提，SP-19 不补做 Fence / Transfer（§77）
```

Early Reject（Impact 后即拒，无 Source change / persistent side effect / Current transition）可极轻量关闭：Decision + Reason + Authority + 无副作用确认（§75）。Late Reject 已有 schema / external registration / config / backfill 等副作用 → 先 reconcile / recover / retain / transfer，再 close（§76）。

## A12 — Closure 后义务

Closure 是 point-in-time engineering decision（§82）：CHG-A 关闭后 CHG-B 改 Current，不使 CHG-A 的 Closure 变成"错误历史"。

[MUST][BASELINE] Closure 后发现新 Bug / hidden drift / missing dependency / 旧 Evidence 不完整 → 产生新 Finding / Incident / Change 并**引用**原 Closure；不得偷偷改写历史 Closure 假装从未关闭。发现原 Evidence / Process 重大失实 → 可审计 / 复盘原 Decision，历史记录仍保留（§83）。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Subject 最低字段 / Obligation 可结束语义 / Authority Confirmation 字段核验 | Automation / Guardrail |
| Commit Guard 并发检查（expected revision / generation 比对） | Automation |
| Ledger 记录与导航解析 | Automation |
| Closure Accountability Scope 对账（Initial vs Actual） | Automation-assisted（列出候选差异，结论归人） |
| Delta 分类（Permitted Variance vs Material）与 Disposition 选择 | Engineering Decision |
| UPDATE_ACCEPTED_AUTHORITY 的 Authority Decision | Engineering Decision（对应 Concern Authority） |
| Transition / Exception 责任是否仍由本 Change 承担 | Engineering Decision |
| Completeness 充分性 / Closure Readiness 结论 | Guardrail（条件核验）+ Engineering Decision |
| Closure Decision 与 Terminal Disposition | Engineering Decision（Authority） |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST NOT][BASELINE] G-SP19-01 不得只用 Initial Intended Scope 关闭 Change
                     （Reconciliation Barrier）。
[MUST NOT][BASELINE] G-SP19-02 Observed Reality / Evidence 不得自动成为
                     Current Authority。
[MUST NOT][BASELINE] G-SP19-03 未经 Commit Guard 检查不得提交 Current Update
                     （防 stale overwrite）。
[MUST NOT][BASELINE] G-SP19-04 Authority 写入 FAILED / UNKNOWN / CONFLICTED 时不得
                     标记 Current 已更新，不得进入 Closure。
[MUST NOT][BASELINE] G-SP19-05 存在未解释的 Material Cross-baseline 冲突时不得声明
                     Completeness。
[MUST NOT][BASELINE] G-SP19-06 Transition / Exception 的 Exit 责任仍由本 Change
                     承担时不得 Closure。
[MUST NOT][BASELINE] G-SP19-07 未满足的 Accepted Obligation 不得改名为
                     Technical Debt 绕过 Closure。
[MUST NOT][BASELINE] G-SP19-10 Candidate REJECT 不得自动成为 Change Terminal
                     REJECTED。
[MUST NOT][BASELINE] G-SP19-11 CANCELLED / SUPERSEDED / Emergency 路径不得绕过
                     Ch8 前置。
[MUST NOT][BASELINE] G-SP19-08 使 Gate 归零的处置（PERMITTED_VARIANCE /
                     UNCHANGED_CONFIRMED / NO_LONGER_APPLICABLE / TRANSFERRED /
                     no-material-effect 判断）必须携带可解析 Rationale / Evidence
                     指针；伪装处置可被挑战回本规程。
[MUST NOT][BASELINE] G-SP19-09 不得在无 Closure Revalidation 的情况下执行
                     OPEN → CLOSED。
[MUST NOT][BASELINE] G-SP19-12 不得改写历史 Closure / Current Transition 记录。
```

（编号与 Operation Contract YAML 的 gates 一一对应；G-SP19-08 / 09 在本文件中的列举位置按论证顺序排列，编号不变。）

---

# 7. PASS Exit

```text
Calibration-only 调用：Scoped Current Update Completeness（该调用范围）Progress Fact 形成，
  五维度满足，Ledger 可解析到真实 Commit Fact
Change Closure 调用：上述 + Closure Readiness 七条件满足 + Revalidation PASS
  + Closure Decision 记录（Record State = CLOSED + Terminal Disposition + Closure Basis Ref）
```

完成**不代表**：系统零 Bug / 零 Technical Debt；所有 Baseline / Environment 全球同版；Candidate 被接受（Ch6 事实）；未来演进被冻结；历史可被改写。

---

# 8. Evidence

Evidence by Work：

```text
Calibration Record（Subject + Delta + Disposition + Evidence Ref）
Authority-backed Commit Fact（§47 字段，存在于真实 Authority Source）
Current Baseline Transition Ledger 条目（引用事实，非事实本身）
Closure Basis（Reference Set）
Closure Decision（Disposition + Reason + Authority + Basis Ref）
```

只有 Disposition Rationale（PERMITTED_VARIANCE / N-A / no-material-effect）、Transfer Acceptance、Exception 条款必须显式记录；小团队可在一个 Issue 内折叠 Calibration / Current Update / Residual / Closure 四段（§99），语义不可省略。

---

# 9. Current Update Obligation

SP-19 **是 Current 的正式写入方**：`CURRENT_COMMITTED` 处置在本规程 A6 经 Commit Guard + Authority-backed Commit 执行。边界：

```text
执行期已成立的 Transition（Requirement / Accepted Release / Runtime）
  由其来源规程（Ch7 → SP-15 / SP-17）在 Authority 背书下提交；
  SP-19 核验 Commit Fact，不重复提交、不伪造时间。
UPDATE_ACCEPTED_AUTHORITY 必须先经该 Concern 真实 Authority 的 Decision（§24）。
SP-01 / SP-03~06 等任何其他规程不得直接写 Current（规则不变）。
```

组1 / 组2 各规程中的过渡条款（"SP-19 落地前，Current 校准 / 更新 = Domain Authority 显式登记的 Change"）自本规程 SEALED 起由本规程正式承接；届时需回改组1 / 组2 文档中的 pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕 标记（列入组3 横向回归检查项）。

---

# 10. FAIL / Return Path

```text
Ch8 前置缺失（Emergency / Cancel / Supersede / Partial）  → 回 Ch8 路径；
                                   SP-21 / SP-20 pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕（组5），
                                   落地前按 Ch8 正文执行
FIX_REALITY 按原因（§23）：
  New Impact                    → SP-04
  Invalid Target / Design       → SP-05
  Implementation Defect         → SP-06
  Candidate / Evidence 问题     → SP-13
  Delivery / Runtime 问题       → SP-15 / SP-17
Evidence Gap / NOT_READY        → 补 Evidence / Reconciliation，不得 assume aligned
Stale Current（Material）       → Context Reconciliation → 更新 Calibration Basis
                                   → 产出新 Revision 或确认现状
Transition Exit 责任未了        → 完成 Exit，或转移给可追接受的 Successor /
                                   Maintenance Owner（Current 导航须显示
                                   active transition + 新 Owner）
Closure Basis 过期（Revalidation FAIL）→ Reconcile 后重新决定
```

---

# 11. Exception / Alternative Path

## 11.1 Small Change

可在一个 Issue + PR/CI + Current docs/registry + Release record 中折叠全部记录（§99，允许项）；Subject 拆分、Disposition、Commit Fact、Closure Decision 语义不省略。

## 11.2 Calibration-only 调用（无 Closure）

Drift / Health Finding 驱动的校准：执行 A3-A9，产出 Completeness Fact 与 Ledger 记录即 PASS；不触发 Closure 动作（A10-A12 不适用）。Current 更新义务仍走显式 Change（GI-03）。

## 11.3 Early Reject / Late Reject

见 A11：Early Reject 轻量关闭（Decision + Reason + Authority + 无副作用确认）；Late Reject 必须先处置全部 persistent side effect。

## 11.4 高风险项目加强

可加入 machine-readable Obligation Set / optimistic concurrency guard / artifact-runtime reconciliation / contract·schema diff / structure drift scan / closure policy-as-code / independent configuration audit（§100，允许项）；不强加给所有项目。

---

# 12. Theory Trace

```text
第一篇：GI-02（Truthful）、GI-03（Every Change Controlled）、GI-05（状态不坍缩：
        Accepted ≠ Observed）、GI-07（工具不取得语义权威）、GI-11/12（Authority 按
        Concern+Scope）
第二篇：WHAT 各 Authority（Requirement / Design / Contract / Data / Release）作为
        Accepted Basis 来源被消费，不被本规程重定义
第三篇：Ch8 Calibration → Update Accepted Current 方向复用；Observed Evidence ≠
        Authority；Structure Finding ≠ auto Current Update；Current 可 health-affected
第四篇：Ch1（OPEN/CLOSED、Terminal Disposition、Progress Fact、Ledger、Starting/
        Working Context）；Ch9 全章（§9-26 Calibration、§27-38 Closure Accountability
        Scope 与 Obligation、§39-50 Authority-backed Commit、§51-62 Completeness、
        §63-83 Closure、§98 Minimum Requirements）；Ch2-Ch8 各返回接口（§102-107）
```

---

# 13. Executable Asset References

```text
EA-17 Current Navigation     Authority 可解析是 Completeness 维 2 的承载
EA-01 Execution Navigation   Closure Basis / Ledger 的可导航入口
```

适配规则：工具适合——Commit Guard 并发比对、字段完整性核验、Ledger 记录与解析、drift scan（高风险项目）。工具不适合——Delta 分类、Disposition 选择、Transfer Acceptance、Closure Decision；模板填完不构成 Completeness 证据（GI-06）。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH：
  Current Design / Structure carrier   docs/current/*.md + registry（git SHA 绑定）
  Data Current                         alembic head + backfill 状态记录
  Accepted Release / Runtime           deployment record / release registry
  Ledger                               Change Record 内的 Current Update 段（引用式）
RP-B-CLI / RP-C-SDK（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组6）：
  Runtime Current 显式 absent；Accepted Release = published artifact version + channel
```

---

# 15. Example

**CHG-WO-142（工单转派能力升级，续第四篇 Ch9 §84-96）**——本示例沿 Ch9 §84-96 的 Validation PASS / 正常 Closure 分支；同一 Change 在 Ch7 §122-138 的 Canary FAIL 分支见 SP-15 / SP-17 示例。

```text
CHG-WO-142：
Calibration 拆 8 个 Subject（Requirement / Design / Module / Contract / Data /
Structure / Release / Transition-cleanup）。
Design Subject 发现 Material Delta：notification-worker 直写 work_order 表
（改 Data Authority / Module Responsibility，不是 implementation detail）
→ FIX_REALITY，回 Ch3 / Ch4 / Ch5 修复后重校准 = ALIGNED。
Data Subject：V203 expand + backfill complete → 提交 Data Authority，
得 Commit Fact DT-203，再记 Ledger。
Structure Subject 提交时 Commit Guard 命中：并发 CHG-139 已 S20→S21 且改了
Notification Runtime Mapping（Material）→ STOP → Context Reconciliation → S22。
Transition Subject：adapter A7 Exit 转 Maintenance Change M-17，M-17 可追接受
owner/scope/exit，Current 导航显示 active transition + M-17。
Revalidation PASS → CLOSED + COMPLETED，Closure Basis = CB-WO-142-v1；
Starting Baseline / Impact / Candidate / Release / Calibration / Ledger 全历史保留。
```

---

# 16. 最终原则

> **SP-19 不是"上线后更新文档并关 Ticket"。它证明：这个 Change 把自己造成、接受或继承的 Material Engineering Responsibility，全部变成了 truthful、Authority-correct、可追踪的 Current / Transition / Transfer / No-longer-applicable 事实。Calibration 既不让文档迁就代码，也不让代码服从过时文档；Observed Reality 不是 Authority，Ledger 不是 Commit，Release Completion 不是 Closure。CLOSED 结束的是本 Change 的责任，不是冻结系统的未来演进。**
