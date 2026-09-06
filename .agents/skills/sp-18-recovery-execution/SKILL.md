---
name: sp-18-recovery-execution
description: 'SP 规程 SP-18 Recovery Execution｜恢复执行（软件项目开发工程规范指南·第五篇）：Execute a delivery / operational failure that needs recovery to an explicit, safe, verifiable target state: make the recovery decision on the trigger / decision-input / anchor facts provided by SP-15, select and execute the recovery means (rollback / rollforward / disable feature / restore data / … 适用触发：in delivery loop recovery；incident recovery stabilization；recovery asset governance；forward fix routing。'
metadata:
  spec.part5.sp-id: SP-18
  spec.part5.name: Recovery Execution
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP18-RecoveryExecution-正式操作规程.md
---

# SP-18 Recovery Execution｜恢复执行

> 《软件项目开发工程规范指南》第五篇执行规程 SP-18 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Execute a delivery / operational failure that needs recovery to an explicit, safe, verifiable target state: make the recovery decision on the trigger / decision-input / anchor facts provided by SP-15, select and execute the recovery means (rollback / rollforward / disable feature / restore data / compensation / traffic shift / failover / pause), complete the recovery attempt execution record (formally taking over the duty previously performed by SP-15 under Ch7 §89-102), maintain repair-script and rehearsal assets, and hand recovery-validation verdicts to SP-17. Recovery != rollback; recovery-command success != recovery complete; a recovery anchor must really exist before it is relied upon; failed attempts / partial states / recoveries are historical engineering facts and are never deleted.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- in delivery loop recovery
- incident recovery stabilization
- recovery asset governance
- forward fix routing

## 操作步骤

### A1 · Entry and decision-input verification
控制模式：guardrail

- receive the SP-15 handoff package (trigger / actual state / evidence / recovery direction / compatibility / anchor verification)
- incomplete inputs (anchor unverified, compatibility unchecked) return to SP-15 — never start recovery actions on intuition with missing inputs
- incident path (trigger B) equally fixes the equivalent inputs first

### A2 · Recovery decision
控制模式：engineering-decision

- choose among the §90 eight candidate means per §92 facts; decision basis in writing; no globally fixed choice (§96)
- cross-verify with migration / exposure facts: backfill pause requires the SP-08-designed pause point to exist; disable feature requires the SP-16 flag / kill-switch asset and trigger conditions
- anchor invalid (old artifact deleted / schema incompatible) -> never claim rollback viable: enter forward-fix routing (A7) and escalate the incident by risk (SP-21)

### A3 · Anchor binding and old-artifact use
控制模式：automation-assisted

- bind the decision to a concrete anchor (§93: previous accepted release / verified old artifact digest / database restore point / last reconciled migration watermark / stable traffic pool)
- rollback-type recovery uses the verified old artifact from the release archive — never rebuild an "old version" at incident time (P2 §60)

### A4 · Execute (inside the target-changing action frame)
控制模式：automation

- execute the chosen means; before each recovery action SP-15 confirms the authority token is not superseded (§114-115)
- non-idempotent actions under outcome unknown reconcile the actual result before continuing (Ch7 §42-44 same-source rule)
- runtime state facts during execution are committed by SP-15 at execution time; this procedure never writes current directly

### A5 · Recovery attempt execution record
控制模式：automation

- complete the execution side of the §98 framework opened by SP-15: actions / evidence / final observed state (validation-field facts go to A6 for SP-17 to verdict)
- this is the formal succession point of the execution-record duty previously performed by SP-15

### A6 · Recovery validation fact collection and handoff
控制模式：automation-assisted

- collect §99-100 validation facts: actually running artifact, data readability, critical business flow restored, migration / traffic safe
- hand the fact set to SP-17 for the verdict (verdict semantics = §100 [BASELINE] consumed there; post-recovery accepted current release = SP-17 / §101)
- validation failing opens a new recovery attempt or escalates the incident (SP-21); unverified states are never reported as recovered (GI-06)

### A7 · Forward fix routing
控制模式：engineering-decision

- recovery needing new source / new artifact / new contract returns in principle to SP-06 (implementation) -> SP-13 (candidate / verification) before delivery; emergency scenarios use the SP-21 / Ch8 compressed path + mandatory after-the-fact reconciliation / verification (§97)
- candidate defects effectively proven in target (Ch7 §105) return with the handoff package to SP-13 for disposition re-evaluation

### A8 · Recovery assets and rehearsal
控制模式：engineering-decision + automation

- maintain versioned repair-script assets (rollback / forward / repair script, EA-16) and their availability
- complete recovery-path rehearsal / recovery smoke before high-risk releases (EA-16 evidence face), supporting SP-15's entry condition (§32 recovery direction) and authorization basis ("previous safe artifact retained")
- backup / recovery inventory kept as inspectable evidence (P3 Ch6 §83); answerability of the P2 §61 five questions (when stop / when rollback / when only forward fix / how data recovers / who decides) guaranteed executable by this procedure

## 硬门禁（不可跳过）

- **G-SP18-01**：recovery-never-defaults-to-rollback
- **G-SP18-02**：anchor-verified-real-before-relied-upon
- **G-SP18-03**：binary-rollback-requires-compatibility-three-questions
- **G-SP18-04**：command-success-is-not-recovery-complete
- **G-SP18-05**：attempt-nine-fields-complete; failed-history-never-deleted
- **G-SP18-06**：recovery-actions-confirm-authority-token-before-execution
- **G-SP18-07**：forward-fix-with-new-software-content-returns-to-normal-chain-or-ch8
- **G-SP18-08**：high-risk-release-recovery-execution-readiness-before-release
- **G-SP18-09**：gate-zeroing-classification-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = Recovery complete (bound to a recovery attempt): chosen means fully executed with authority-token confirmation facts on record + recovery attempt nine-field record complete (incl. final observed state) + recovery validation fact set handed to SP-17 and verdicted + when applicable: forward-fix routing decision in writing, post-recovery current facts committed via SP-15 / SP-17 -> handoff to SP-17 (verdict) / SP-21 (incident reconciliation, when applicable) / SP-13 (candidate re-evaluation, when applicable)
`



**完成不意味着**：target-redelivered, change-closed, incident-closed, root-cause-fixed

## 回退路径（发现问题去哪）

- decision inputs incomplete (anchor unverified / compatibility unchecked) → return to SP-15 for completion
- recovery validation fails → new recovery attempt or incident escalation (SP-21); never report recovered
- anchor invalid with no substitute → forward-fix routing (A7) + incident escalation assessment
- recovery action outcome unknown → reconcile the actual result first (Ch7 §42-44 same-source rule), never blind retry
- old recovery action superseded by newer intent → abort per Ch7 §116 outdated-attempt rules (SP-15 control); never self-cover
- candidate defect → SP-13 re-evaluation / SP-06 fix
- migration / backfill recovery-design gap → SP-08
- material design problem (recovery path itself unsound) → SP-05

## 证据义务

- 自然证据：['recovery decision record (path + basis + cross-verification)', 'recovery attempt record (§98 nine fields)', 'anchor verification and old-artifact-use facts (digest comparison)', 'authority-token confirmation facts (per recovery action)', 'recovery validation fact set (input handed to SP-17)', 'repair-script versions and rehearsal records (EA-16)', 'failure history (attempt / partial state / recovery — retained, never deleted)']
- 额外证据（仅当）：['gate-zeroing-classification-rationale', 'forward-fix-routing-rationale', 'anchor-invalidation-escalation-decision']
- 证据规则：all other evidence emerges naturally from the work
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力（按需）
- JG-06 构建并发布一个版本（按需）
- JG-07 部署后验证、扩大暴露或恢复（按需）
- JG-08 处理线上 Incident / Emergency

## 理论回溯

- **part1**：GI-03, GI-05, GI-06
- **part2**：p2-ch11-58-62-rollback-not-only-answer-execution-side-what
- **part3**：p3-ch3-mixed-recovering-state-truthful-expression, p3-ch3-runtime-relevant-change-includes-release-recovery, p3-ch6-operational-owner-backup-failover-inventory, p3-ch6-recovery-restore-what-boundary-defers-to-p2-p4-sp08
- **part4**：ch7-89-102-recovery-core-execution-authority, ch7-42-44-outcome-unknown-reconcile, ch7-114-116-authority-token-constrains-recovery-actions, ch7-122-132-workorder-canary-fail-recovery-r1, ch7-139-recovery-must-items

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
