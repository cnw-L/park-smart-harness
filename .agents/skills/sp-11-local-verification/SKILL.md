---
name: sp-11-local-verification
description: 'SP 规程 SP-11 Local Verification｜本地验证（软件项目开发工程规范指南·第五篇）：Produce revision-bound, trustworthy, classified Local Evidence for an explicit Implementation Revision / Revision Set: compose and run Feedback Runs in the local / pre-submit scopes, bind them to their real context, judge applicability and invalidation, dispose unreliable feedback and required … 适用触发：local implementation change；pre submit；binding context change；required feedback missing；feedback fail。 边界：Never re-decides candidate formation, required verification sufficiency, acceptance (SP-13), review approval or integration entry (SP-12), …'
metadata:
  spec.part5.sp-id: SP-11
  spec.part5.name: Local Verification
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP11-LocalVerification-正式操作规程.md
---

# SP-11 Local Verification｜本地验证

> 《软件项目开发工程规范指南》第五篇执行规程 SP-11 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Produce revision-bound, trustworthy, classified Local Evidence for an explicit Implementation Revision / Revision Set: compose and run Feedback Runs in the local / pre-submit scopes, bind them to their real context, judge applicability and invalidation, dispose unreliable feedback and required feedback evidence gaps, classify every failure to the correct return layer, retain evidence by diagnostic value, and hand off truthfully. This procedure is the specialized detail behind SP-06 A6-A8; feedback green is not required verification complete, and local evidence is not candidate membership.


## 边界（本规程不做的事）

Never re-decides candidate formation, required verification sufficiency, acceptance (SP-13), review approval or integration entry (SP-12), canonical build / provenance (SP-14), target validation (SP-17), or any current update (SP-19). A check not reliably executed is not evidence pass; platform UI showing skipped as success changes nothing.


## 触发

- local implementation change
- pre submit
- binding context change
- required feedback missing
- feedback fail

## 操作步骤

### A1 · Resolve required local feedback obligation set
控制模式：engineering-decision

- resolve from policy / gate declarations, design verification obligations, candidate acceptance expectations, direct regression protection
- every obligation labeled required / optional with rationale and source pointer
- re-challenge upstream gate-zeroing dispositions (B1)

### A2 · Compose feedback runs
控制模式：engineering-decision + automation

- **特征**：
  - revision-bound
  - fast-enough
  - repeatable-enough
  - diagnostic-enough
- fast / repeatable / diagnostic enough are project-context judgements, not fixed minutes
- mechanisms failing repeatable / diagnostic enough go to A6 before producing results
- static check registered apart from dynamic test; change-local test registers its protection boundary and never claims coverage of cross-service integration / performance / security / acceptance / target validation

### A3 · Execute and bind
控制模式：automation

- **最小绑定**：
  - subject-revision / revision-set
  - base / integration-context (when applicable)
  - check / test-identity
  - result
  - relevant dependency / build-context (risk-scaled)
  - observed-at
- binding is produced at run time, never backfilled
- unbound or unresolvable runs record GAP, not SATISFIED
- temporary-environment / non-retained feedback builds are legal but their artifacts must not later claim candidate eligibility

### A4 · Judge run result state
控制模式：guardrail

- **判定词汇**：
  - satisfied: trustworthy execution + complete binding + pass
  - failed: trustworthy execution + complete binding + fail
  - unreliable: mechanism not trustworthy
  - gap: required feedback without trustworthy execution
- tool exit code success / platform green / skipped-but-success are not sufficient for satisfied

### A5 · Re-judge applicability of prior results
控制模式：engineering-decision

- **失效条件**：
  - head-revision-change
  - base-revision-change
  - dependency-context-change
  - test-definition-change
- **处置选项**：
  - rerun
  - reuse
  - not-applicable
- default action is rerun
- reuse must record why old evidence still covers the new revision
- not-applicable is a gate-zeroing disposition: rationale recorded, re-challengeable at SP-12 / SP-13 entry (B1)
- review approval invalidates on material revision change (SP-12 executes re-review)

### A6 · Dispose unreliable feedback
控制模式：engineering-decision

- no rerun-until-green; the first FAIL record is never auto-deleted
- classify the failure type first (product / test / environment / concurrency / infra / external / unknown)
- fix the mechanism (test / check defect path) or quarantine
- quarantine carries owner + reason + follow-up; a quarantined required check immediately forms an evidence gap (A7)
- chronically flaky mechanisms are process signals, never personnel KPIs

### A7 · Dispose required feedback evidence gaps
控制模式：engineering-decision + authority

- **处置选项**：
  - alternative-evidence
  - controlled-exception
  - decision-blocked
- gap records travel with the evidence bundle; re-challengeable at SP-12 / SP-13 entry
- optional local feedback may be skipped; required-role checks never

### A8 · Classify every finding and route the return layer
控制模式：engineering-decision

- **判定词汇**：
  - implementation-defect: fix in layer (SP-06 rework, new revision)
  - test-check-defect: fix the test/check; never bend product code for green
  - design-assumption-invalidated: return to SP-05
  - new-impact-discovery: return to SP-04
  - requirement-semantic-gap: return to requirement authority, then SP-04 / SP-05 as applicable
  - integration-conflict-context-change: context reconciliation (SP-12 domain) + re-evaluate as needed
  - tool-infrastructure-failure: fix feedback infrastructure; never revert product for infra failure
  - external-environment-dependency: isolate external cause; record GAP / NOT_READY, not product FAIL
  - unknown: retain unknown and collect evidence; never force-classify

### A9 · Retain evidence by diagnostic value
控制模式：guardrail + policy

- **长期保留**：
  - design-impact-decision-change
  - shared-baseline-breakage
  - required-gate-review-failure
  - material-security-data-finding
  - accepted-exception-bypass
  - persistent-repeated-failure
  - root-cause-with-future-value
- local noise (compile typo, instantly fixed unit fail) not mandated for archive
- small changes may use VCS / PR / CI as the evidence carrier directly

### A10 · Hand off local evidence
控制模式：automation + guardrail

- **移交**：
  - → SP-06：feedback state feeding the outputs-ready no-known-blocker condition
  - → SP-12：pre-submit readiness fact (scope-bound three-state); NOT_READY never hands off; READY-WITH-EXCEPTION hands off with the exception travelling visibly
  - → SP-13：full local evidence set; artifacts with identity / traceable inputs / stable context are selectable by Ch6 — selection is SP-13's decision
- handoff is never candidate accepted, never required verification complete, never a current update

## 硬门禁（不可跳过）

- **G-SP11-01**：no-old-green-for-new-revision
- **G-SP11-02**：no-rerun-until-green
- **G-SP11-03**：no-silent-quarantine-or-skip-of-required-evidence
- **G-SP11-04**：feedback-success-is-not-candidate-accepted-verification-complete-or-release-ready
- **G-SP11-05**：no-unclassified-failure-attribution
- **G-SP11-06**：static-check-is-not-dynamic-test; change-local-test-is-not-required-verification-set
- **G-SP11-07**：no-implicit-candidate-membership-of-feedback-artifacts
- **G-SP11-08**：material-feedback-bound-at-runtime
- **G-SP11-09**：reuse-and-not-applicable-require-resolvable-rationale
- **G-SP11-10**：required-evidence-gap-requires-explicit-disposition

## 通过出口（什么算完成）

`passExit = local-evidence-state-truthfully-established`

- every required obligation has a final state (satisfied / failed-classified-routed / gap-disposed / not-applicable-with-rationale)
- every satisfied result fully bound and applicable to the current revision (or reuse rationale recorded)
- no undisposed required gap, no bare quarantine, no rerun-until-green residue
- no unrouted FAILED in the finding register
- handoff bundle emitted (obligation states + gaps + quarantines + exceptions + reuse basis)

**完成不意味着**：candidate-formed, required-verification-satisfied, review-passed, shared-baseline-entry, any-current-updated

## 回退路径（发现问题去哪）

- implementation defect → SP-06 in-layer rework, new revision
- test / check defect → fix the feedback mechanism; product code untouched
- design assumption invalidated → SP-05
- new impact discovery → SP-04
- requirement semantic gap → requirement authority, then SP-04 / SP-05 as applicable
- integration conflict / context change → SP-12 context reconciliation; re-evaluate as needed
- tool / infrastructure failure → fix feedback infrastructure; never revert product
- external environment / dependency failure → isolate external cause; gap / not-ready, not product fail
- unknown failure → retain unknown, collect evidence
- cannot continue locally (external dependency / missing decision) → work-package blocker via SP-06; not change BLOCKED

## 证据义务

- 自然证据：['VCS / PR / CI run records with runtime-produced bindings', 'task runner output']
- 额外证据（仅当）：['obligation-set-with-sources', 'reuse-not-applicable-rationale', 'quarantine-record', 'evidence-gap-disposition', 'retained-finding-classification']
- 证据规则：retention by diagnostic value; full retention not mandated; backfilled bindings are not evidence
- Current 更新：writesCurrent = False
  Local verification never updates any current. Feedback green, pre-submit readiness, even later merge / integration, do not constitute current updates; SP-19 (formal candidate within this group) is the sole calibration / commit channel. Local evidence produced here is a candidate Actual Evidence Ref for SP-19 calibration.


## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data
- JG-05 新增或升级 Dependency / Toolchain / Config

## 理论回溯

- **part1**：GI-03, GI-05, GI-13
- **part2**：testing-quality-what, build-what, evidence-semantics
- **part3**：source-runtime-as-evidence-context, source-where-resolvable
- **part4**：ch5-feedback-loop-binding-classification, ch5-rework-evidence-retention, ch5-minimum-requirements-274-279-287-299-303-305, ch6-evidence-semantics-producer-side, ch8-emergency-compression

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
