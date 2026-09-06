---
name: sp-15-release-deployment
description: SP 规程 SP-15 Release / Deployment｜发布/部署（软件项目开发工程规范指南·第五篇）：Form an accepted candidate into a release baseline with truthful, immutable identity and explicit scope; make the release decision; make traceable, revalidatable per-target delivery authorization; execute controlled deployment attempts and rollouts; 适用触发：release formation；release decision or authorization；authorization revalidation；deployment attempt or rollout；delivery finding。 边界：Never produces candidate acceptance or evidence applicability conclusions (SP-13), artifact identities (SP-14), target validation …
metadata:
  spec.part5.sp-id: SP-15
  spec.part5.name: Release / Deployment
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP15-ReleaseDeployment-正式操作规程.md
---

# SP-15 Release / Deployment｜发布/部署

> 《软件项目开发工程规范指南》第五篇执行规程 SP-15 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Form an accepted candidate into a release baseline with truthful, immutable identity and explicit scope; make the release decision; make traceable, revalidatable per-target delivery authorization; execute controlled deployment attempts and rollouts; maintain truthful, timely environment current runtime state; and route delivery findings back to the correct layer. SP-14 produces identity, SP-13 decides candidate acceptance and evidence re-evaluation; SP-17 owns target validation and completion; SP-16 owns feature exposure detail (pending-definition, group 5); SP-18 owns recovery execution detail (pending-definition, group 5 — until it lands, recovery execution follows Ch7 §89-102 directly and this procedure keeps the execution records). Release formation never rebuilds a "similar" artifact and claims it verified.


## 边界（本规程不做的事）

Never produces candidate acceptance or evidence applicability conclusions (SP-13), artifact identities (SP-14), target validation conclusions / target release completion / accepted current release updates (SP-17), feature exposure strategy (SP-16, pending-definition), recovery execution detail (SP-18, pending-definition), or any project-level current update (SP-19). Release formation references verified identities; it never rebuilds content. Deployment tool success is never target validation; environment current runtime state is never accepted current release.


## 触发

- release formation
- release decision or authorization
- authorization revalidation
- deployment attempt or rollout
- delivery finding
- outcome unknown or stale intent
- sp17 assessment arrives

## 操作步骤

### A1 · Verify release formation entry
控制模式：guardrail

- candidate accepted with exceptions visible; acceptance scope covers intent
- SP-14 identity list resolvable; formation scope explicit (no fixed env chain)
- re-challenge upstream gate-zeroing classifications (B1)

### A2 · Compose the release baseline
控制模式：automation + guardrail

- reference (never rebuild) SP-14 identities: artifact, migration, contract, config schema/profile, deployment definition revision, evidence set ref
- verify member coherence; issue immutable release identity
- every new-identity materialization delta has its SP-13 re-evaluation conclusion recorded before formation completes

### A3 · Make the release decision
控制模式：decision-point


### A4 · Make / re-judge delivery authorization
控制模式：decision-point + policy


### A5 · Check release entry conditions
控制模式：guardrail


### A6 · Execute the deployment attempt
控制模式：automation + guardrail

- record per-step results; emit the environment deployment record
- retry of the same release gets a new attempt identity; old records kept

### A7 · Control steps and unknown outcomes
控制模式：guardrail + engineering-decision

- steps preferably idempotent; non-idempotent steps register a reconcile path
- unknown outcome (timeout / crash / partial migration): never retry directly — inspect actual target state, reconcile, then decide resume / retry / recovery
- retries form traceable facts
- deployment result recorded apart from target validation conclusions

### A8 · Execute rollout
控制模式：engineering-decision + guardrail

- rollout necessity judged by risk / policy — not every deployment needs one
- scope and slice sequence explicit; slice is not candidate scope
- per-slice observation with canary / control comparison; metrics decomposed by version / cohort — aggregate green never masks slice failure
- insufficient representativeness downgrades the conclusion
- proceed decisions cite Ch4 invariants + slice target evidence, never a timer
- pause is normal and recorded
- attribution conflict: isolate / decompose / pause one change / downgrade to NOT_READY

### A9 · Maintain environment current runtime state
控制模式：automation + guardrail

- update timely after every target-changing action; mixed state recorded honestly
- never equate with accepted current release or release completion
- emit deployment observation records for SP-17

### A10 · Enforce ordering / generation / authority
控制模式：automation + guardrail

- maintain a target deployment generation per material target (monotonic id / GitOps commit / lease / lock all legal)
- every target-changing action — including delayed rollback, automated recovery, traffic revert, feature disable — confirms its authority token is not superseded before executing
- outdated attempts never become desired state; block and record
- same-boundary concurrency gets explicit ordering / isolation; no global single-deployment mandate

### A11 · Classify and route delivery findings
控制模式：engineering-decision

- **判定词汇**：
  - release-baseline-packaging
  - candidate-defect-in-target
  - deployment-process-defect
  - target-environment-infrastructure
  - migration-data
  - rollout-transition
  - validation-evidence-gap
  - external-dependency
  - requirement-design-impact-gap
  - unknown

### A12 · Recognize recovery triggers and prepare decision inputs
控制模式：engineering-decision + guardrail

- recognize the nine trigger classes; assemble actual state + failure/unknown evidence + Ch4 recovery direction + data/contract compatibility check + anchor verification
- no globally fixed rollback-vs-rollforward choice
- forward fix producing new software content routes back to SP-06 / SP-13 or the Ch8 compressed path with mandatory after-the-fact reconciliation
- open the recovery attempt fact frame (eight of the nine P4 Ch7 §98 fields — validation stays with SP-17); execution detail is SP-18 (pending-definition)
- recovery command success is never recovery complete; validation and post-recovery accepted-current-release judgement are SP-17 / SP-18
- failed attempt / partial state / recovery history never deleted

## 硬门禁（不可跳过）

- **G-SP15-01**：release-formation-never-rebuilds-a-similar-artifact-and-claims-it-verified
- **G-SP15-02**：new-materialized-identity-blocks-formation-until-sp13-reevaluation-recorded
- **G-SP15-03**：release-identity-immutable; changes-mean-new-revision
- **G-SP15-04**：authorization-attempt-completion-claims-carry-explicit-target-scope
- **G-SP15-05**：authorization-applicability-bound-by-revalidation-triggers; no-permanent-pass
- **G-SP15-06**：no-blind-retry-of-non-idempotent-steps-on-unknown-outcome
- **G-SP15-07**：rollout-proceed-on-invariants-plus-slice-evidence; aggregates-never-mask; timer-never-sufficient
- **G-SP15-08**：runtime-state-truthful-and-timely; mixed-state-never-masquerades-as-accepted
- **G-SP15-09**：every-target-changing-action-confirms-unsurperseded-authority-token
- **G-SP15-10**：findings-ten-class-classified-and-routed; candidate-defect-forces-reevaluation
- **G-SP15-11**：recovery-anchor-verified-real-before-reliance; binary-rollback-checks- data-contract-compatibility
- **G-SP15-12**：failed-attempt-partial-state-recovery-history-never-deleted
- **G-SP15-13**：zeroing-classifications-carry-rationale-and-stay-rechallengeable

## 通过出口（什么算完成）

`passExit = release-formed-and-delivered-with-truthful-target-facts`

- release baseline composed of referenced verified identities; coherence verified
- all materialization deltas disposed (inheritance basis / SP-13 conclusions recorded)
- per-target authorization exists with traceable basis and explicit applicability
- attempt / rollout records complete with proceed / pause basis
- no undisposed unknown outcome; non-idempotent retries have reconcile facts
- runtime state matches reality and is timely; observation records handed to SP-17
- findings classified and routed; candidate-defect class triggered re-evaluation
- authority / generation control effective; no outdated action took effect

**完成不意味着**：target-validation-passed, target-release-complete, accepted-current-release-updated, feature-exposed, recovery-complete, change-closed, any-project-level-current-updated

## 回退路径（发现问题去哪）

- identity gap in formation → SP-14 identity / delta work; genuinely new artifact returns to SP-13
- authorization basis premise lapsed → authorization lapses; A4 re-judgement; SP-13 / SP-05 as needed
- deployment step failure → A11 classification — process defect -> fix EA-12; environment -> repair target, same release may redeploy
- outcome unknown → confirm actual target state then reconcile; blind retry forbidden
- rollout slice fail → proceed = STOP; finding routing; recovery via A12 -> SP-18
- candidate defect in target → candidate disposition re-evaluation -> SP-13 / SP-06 / SP-05
- attribution failure → isolate / decompose / pause one change / downgrade to NOT_READY
- stale / superseded action → block, record, audit the authority mechanism

## 证据义务

- 自然证据：['CD platform / GitOps records, pipeline runs, observability systems']
- 额外证据（仅当）：['authorization-basis-and-applicability-registry', 'authority-token-confirmations', 'rollout-proceed-pause-basis', 'finding-classification-records', 'anchor-verification-records', 'unknown-outcome-reconcile-chains']
- 证据规则：the carrier folds into existing platforms; semantic records never waived
- Current 更新：writesCurrent = environment-current-runtime-state-only
  The environment current runtime state is an observed-fact current (P4 Ch9 §33 baseline kind; §35 — runtime current is recorded at execution time, never deferred to change closure): this procedure commits it at execution time under authority backing, and SP-19 only verifies the commit fact without re-committing. It never equals the accepted current release (GI-05: accepted is not observed) — the accepted-current-release ledger transition happens at target release completion (SP-17); project-level currents (design / structure / calibration / change closure) go through SP-19. Neither merge nor deploy updates any project-level current.


## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data
- JG-05 新增或升级 Dependency / Toolchain / Config
- JG-06 构建并发布一个版本
- JG-07 部署后验证、扩大暴露或恢复

## 理论回溯

- **part1**：GI-03, GI-05, GI-13, ch1-decision-record-authority-ledger
- **part2**：build-release-what-boundary, deploy-not-release-not-launch
- **part3**：runtime-deployment-where
- **part4**：ch7-forward-fix-97, ch7-materialization-delta-10-11, ch6-member-identity-binding-10-11-same-intent, ch7-ch6-interface-143, ch6-ch7-interface-142, ch7-formation-baseline-decision-target-8-22, ch7-authorization-basis-applicability-revalidation-entry-23-32, ch7-attempt-step-unknown-reconciliation-retry-33-45, ch7-rollout-46-59, ch7-runtime-state-observation-60-65, ch7-exposure-client-distribution-boundary-86-88, ch7-recovery-entry-89-102, ch7-finding-ordering-generation-authority-attribution-103-121, ch7-minimum-requirements-139-140, ch8-emergency-144, ch9-calibration-145, ch9-runtime-current-33-35

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
