---
name: sp-12-review-shared-integration
description: 'SP 规程 SP-12 Review / Shared Integration｜Review / Shared Integration（软件项目开发工程规范指南·第五篇）：Move a review-ready Implementation Unit into the Shared Integration Baseline under control: run revision-bound work product review, obtain integration-context feedback against a fresh-enough context, integrate incomplete features via controlled mechanisms, classify and restore shared baseline … 适用触发：review ready；integration entry；concurrent material boundary change；suspected shared baseline breakage；review finding or integration failure。 边界：Never produces candidate acceptance (SP-13), release / supported status (SP-15), target environment actions (SP-15 / SP-17), deviation / …'
metadata:
  spec.part5.sp-id: SP-12
  spec.part5.name: Review / Shared Integration
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP12-ReviewSharedIntegration-正式操作规程.md
---

# SP-12 Review / Shared Integration｜Review / Shared Integration

> 《软件项目开发工程规范指南》第五篇执行规程 SP-12 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Move a review-ready Implementation Unit into the Shared Integration Baseline under control: run revision-bound work product review, obtain integration-context feedback against a fresh-enough context, integrate incomplete features via controlled mechanisms, classify and restore shared baseline breakage with an owner, and emit truthful integration evidence. This is the specialized detail behind SP-06 A10; generic feedback run / binding / classification mechanics are reused from SP-11. Review is feedback, not required verification; integration is neither deployment nor release; merge never updates any current.


## 边界（本规程不做的事）

Never produces candidate acceptance (SP-13), release / supported status (SP-15), target environment actions (SP-15 / SP-17), deviation / drift disposition or outputs-ready judgement (SP-06), or any current update (SP-19). Breakage is a scoped baseline condition / finding, never a change state.


## 触发

- review ready
- integration entry
- concurrent material boundary change
- suspected shared baseline breakage
- review finding or integration failure

## 操作步骤

### A1 · Verify review-ready
控制模式：guardrail

- any miss returns to SP-11 / SP-06 with the gap list
- re-challenge upstream gate-zeroing dispositions (B1)

### A2 · Compose the review
控制模式：engineering-decision + policy

- review objects span more than code, by applicability
- reviewer count not fixed; driven by ownership / risk / policy / specialist concern
- high-risk surfaces (contract semantics, data migration, security) require the corresponding specialist view; absence registered with rationale
- reviewers receive why + design trace + SP-11 evidence bundle

### A3 · Run revision-bound review
控制模式：human-judgment

- active reasoning required; CI green does not replace judgement (concurrency / boundary / semantic compatibility / complexity)
- findings classified via the SP-11 nine-class vocabulary and routed
- approval binds an explicit revision; material new revision re-judges applicability
- minor-revision re-review decided by policy / materiality; the minor/material split records rationale and is re-challengeable by SP-13

### A4 · Judge integration path and context freshness
控制模式：engineering-decision

- latest-main per PR not mandated; freshness driven by change rate / risk / merge queue / build cost
- known concurrent change on the same material boundary forces advancing the context and re-obtaining integration-context feedback
- freshness rationale written into the integration record

### A5 · Integrate and obtain integration-context feedback
控制模式：automation + sp11-mechanics

- feedback binds the merge result (synthetic merge / queue result), not only the branch head
- binding / invalidation / unreliable / gap mechanics reused from SP-11
- concurrent interaction checklist: contract conflict, dependency conflict, data migration order, generated artifact conflict, behavior interaction

### A6 · Integrate incomplete features safely
控制模式：engineering-decision + guardrail

- controlled mechanism required: old behavior preserved, new path inactive, schema / contract compatible, shared checks green
- feature flags trace to Ch4 transition / cleanup design (exit semantics + owner); merge-easy permanent flags rejected back to SP-05 / SP-06
- long-lived divergence recorded and pushed toward slicing

### A7 · Enter the shared baseline
控制模式：automation + guardrail

- verify buildable / testable / integrable / traceable on the integration context
- entry is an integration record fact; it updates no current — project-defined development-current advancement goes through explicit baseline transition records via SP-19

### A8 · Monitor and dispose shared baseline breakage
控制模式：engineering-decision + guardrail

- product defect may be reverted; infrastructure failure must not revert product; broken tests are fixed at the test, never by deleting correct product behavior

### A9 · Classify integration failures
控制模式：engineering-decision

- **判定词汇**：
  - merge-conflict
  - build-fail
  - test-fail
  - dependency-fail
  - infra-fail

### A10 · Hand off integration evidence
控制模式：automation + guardrail

- **移交**：
  - → SP-13：integration record, merge-result-bound feedback, breakage history, revision-bound review record
  - → SP-06：review / integration state facts for outputs-ready judgement

## 硬门禁（不可跳过）

- **G-SP12-01**：review-never-substitutes-dynamic-testing-or-required-verification
- **G-SP12-02**：review-approval-binds-revision; material-new-revision-rejudges
- **G-SP12-03**：no-fixed-reviewer-count
- **G-SP12-04**：critical-breakage-restore-first; restore-not-mechanical-revert
- **G-SP12-05**：feature-incomplete-is-no-excuse-for-broken-shared-baseline
- **G-SP12-06**：same-material-boundary-concurrency-requires-fresh-integration-feedback
- **G-SP12-07**：merge-integration-never-updates-current
- **G-SP12-08**：breakage-never-becomes-a-change-state
- **G-SP12-09**：no-product-revert-for-infra-failure; no-product-deletion-for-broken-test
- **G-SP12-10**：zeroing-judgements-carry-rationale-and-stay-rechallengeable

## 通过出口（什么算完成）

`passExit = unit-integrated-with-truthful-evidence`

- review record bound to current revision (or applicability re-judged)
- all review findings classified and routed; no open change-requests
- integration record exists; feedback valid on a fresh-enough context
- incomplete features integrated via controlled mechanisms with Ch4-traceable flags
- no known critical breakage, or breakage has owner + restore path and its relation to the change's execution condition is explicitly judged
- integration evidence handed to SP-13; state facts returned to SP-06

**完成不意味着**：candidate-accepted, release-established, any-current-updated, change-done

## 回退路径（发现问题去哪）

- review finding → SP-11 nine-class routing (in-layer / SP-05 / SP-04 / requirement authority)
- material new revision → re-judge approval applicability; re-review per policy / materiality
- integration failure → classify — conflict -> context reconciliation; build/test -> SP-11 mechanics; dependency -> SP-09 domain; infra -> fix infrastructure
- shared baseline breakage → A8 sequence (classify -> owner -> restore first)
- material base change → re-obtain integration-context feedback; re-evaluate SP-04 / SP-05 as needed

## 证据义务

- 自然证据：['PR / CL platform records (review, approvals)', 'merge queue / CI records bound to merge results', 'repository rules enforcement logs']
- 额外证据（仅当）：['reviewer-composition-rationale', 'minor-material-split-rationale', 'context-freshness-rationale', 'breakage-record', 'flag-ch4-trace']
- 证据规则：small changes use the platform as carrier; semantic records never waived
- Current 更新：writesCurrent = False
  Merge / integration changes only the source fact. Project-defined development current advancement requires an explicit baseline transition rule / record, executed via the SP-19 channel. Shared integration baseline state is a baseline health fact, not an accepted current release.


## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-05 新增或升级 Dependency / Toolchain / Config

## 理论回溯

- **part1**：GI-03, GI-05, GI-13
- **part2**：implementation-review-quality-what, build-what
- **part3**：source-build-where, shared-baseline-as-structural-fact
- **part4**：ch5-review-integration-shared-baseline-153-194, ch5-minimum-requirements-288-295-298-300-305, ch5-feedback-mechanics-via-sp11, ch5-consumer-interface-toward-ch6-193-194, ch8-emergency

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
