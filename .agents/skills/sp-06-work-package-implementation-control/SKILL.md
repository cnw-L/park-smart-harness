---
name: sp-06-work-package-implementation-control
description: 'SP 规程 SP-06 Work Package Implementation Control｜工作包实现控制（软件项目开发工程规范指南·第五篇）：Turn one execution-ready Work Package into real software output under control: establish the execution context and applicable guardrails, continuously obtain revision-bound feedback, classify every failure and deviation correctly, and finally declare Implementation Outputs Ready for an explicit … 适用触发：work package execution ready；feedback or review finding rework；material base context change；execution plan adjustment。 边界：SP-06 never re-decides requirement (Ch2) and never rewrites design (Ch4); problems belonging to those layers return to those layers.'
metadata:
  spec.part5.sp-id: SP-06
  spec.part5.name: Work Package Implementation Control
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP06-WorkPackageImplementationControl-正式操作规程.md
---

# SP-06 Work Package Implementation Control｜工作包实现控制

> 《软件项目开发工程规范指南》第五篇执行规程 SP-06 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Turn one execution-ready Work Package into real software output under control: establish the execution context and applicable guardrails, continuously obtain revision-bound feedback, classify every failure and deviation correctly, and finally declare Implementation Outputs Ready for an explicit scope / revision. Implementation is not "code written"; feedback green is not required verification complete; outputs ready is neither candidate accepted nor change done.


## 边界（本规程不做的事）

SP-06 never re-decides requirement (Ch2) and never rewrites design (Ch4); problems belonging to those layers return to those layers.


## 触发

- work package execution ready
- feedback or review finding rework
- material base context change
- execution plan adjustment

## 操作步骤

### A1 · Confirm entry and establish execution context
控制模式：automation

- without execution context no later feedback can be bound
- re-check upstream gate-zeroing dispositions (SP-05 n-a / delegated / non-blocking) for resolvable rationale/evidence; challenge disguised ones back to SP-05

### A2 · Resolve applicable implementation guardrail set
控制模式：engineering-decision

- resolve by current / target / transition applicability; never a mechanical union demanding all hold simultaneously
- a legal change path (current optional -> accepted target required) is not a deviation
- deviation = departing the accepted current->transition->target path or crossing authority not licensed to change

### A3 · Locate source / build WHERE
控制模式：automation-assisted


### A4 · Form implementation units and small batches
控制模式：engineering-decision

- unit != work package; unit != PR; unit != commit
- small batch = feedback-able, revertible, reviewable semantic slice; not fixed LOC; not smaller-is-better
- behavior change and big refactor kept apart, but no mechanical PR splitting

### A5 · Produce the complete output set
控制模式：automation + engineering-decision


### A6 · Run the feedback loop
控制模式：automation

- the four scopes are not four mandatory stages
- fast / repeatable / diagnostic enough are project-context judgements, not fixed minutes
- behavior change should carry the most direct regression protection
- static check != dynamic test; change-local test != full required verification
- feedback build is a build but != candidate build != release build
- local workspace may be temporarily non-green; local failure must not persistently enter the shared baseline

### A7 · Bind feedback and judge applicability loss
控制模式：automation

- **失效条件**：
  - head-revision-change
  - base-revision-change
  - dependency-context-change
  - test-definition-change
- **最小绑定**：
  - subject-revision-or-implementation-revision-set
  - base-or-integration-context
  - check-test-identity
  - result
  - relevant-dependency-build-context
  - observed-at

### A8 · Classify every failure
控制模式：engineering-decision

- **判定词汇**：
  - implementation-defect: fix in this layer (rework)
  - test-check-defect: fix the test/check; never bend product code
  - design-assumption-invalidated: return to SP-05
  - new-impact-discovery: return to SP-04
  - requirement-semantic-gap: return to requirement authority
  - integration-conflict-context-change: integration handling + re-evaluation as needed
  - tool-infrastructure-failure: fix toolchain; never revert product for infra failure
  - external-environment-dependency: isolate the external cause
  - unknown-failure: locate before classifying
- no default rerun-until-green; classify first
- flaky test quarantine carries owner + reason + follow-up
- quarantine / skip must never silently turn required evidence green
- a required feedback evidence gap must be explicit, with disposition

### A9 · Separate detail choice / plan adjustment / deviation / drift
控制模式：engineering-decision

- detail choice: left to implementation, touches no target/boundary/contract/ data-meaning/transition/risk-obligation/recovery; still inside guardrail set
- plan adjustment updates plan/trace only; touching target/contract/data/ transition/recovery/risk upgrades it to design change (SP-05)
- the "no layer change" judgement must cite the WP's registered re-evaluation trigger list; adjustments are appended to the change record as plan revisions (SP-05 keeps semantic ownership)
- deviation judged against the applicable guardrail set; may be found before code lands; finding a deviation is good
- developer must never self-approve a deviation through code
- drift (silent data-boundary crossing / contract semantic change / transition leak) is prohibited, not a process state

### A10 · Govern review and integration
控制模式：engineering-decision

- review is feedback, not proof of all behavior correct; review != test
- review must not be the first discoverer of compile errors
- reviewer count not fixed; approval binds revision; minor revision re-review decided by policy / materiality
- integration != deployment != release; trunk-only and latest-main-per-PR not mandated; material base change forces re-judgement
- shared baseline breakage: classify first, owner assigned, restore-first; breakage is not a change state
- incomplete feature may integrate safely via feature flag mechanisms
- merge never updates any current (explicit update via SP-19 only)

### A11 · Judge implementation outputs ready
控制模式：guardrail + engineering-decision

- ready is a scoped progress fact; slices allowed; whole-change single shot not required
- ready claims can be invalidated (new revision / base change); history never deleted
- "known material defect = 0" must rest on executed, revision-bound feedback records; self-attestation without inspection does not count

### A12 · Rework and process signal
控制模式：engineering-decision

- rework returns to the correct layer and produces a new revision
- no blanket full re-run of all checks, but green reuse needs basis
- repeated rework and repeated ch5->ch3 returns are process signals, never direct personnel KPIs
- failed attempts need not all be retained; diagnostically valuable failures (new class / boundary case) are worth keeping

## 硬门禁（不可跳过）

- **G-SP06-01**：no-implementation-without-execution-context
- **G-SP06-02**：no-rerun-until-green
- **G-SP06-03**：no-silent-quarantine-of-required-evidence
- **G-SP06-04**：no-silent-guardrail-change
- **G-SP06-05**：no-ready-with-known-material-defect-or-open-design-relevant-deviation
- **G-SP06-06**：merge-push-never-updates-current
- **G-SP06-07**：gate-zeroing-judgement-requires-executed-evidence

## 通过出口（什么算完成）

`passExit = outputs-ready-progress-fact-formed`



**完成不意味着**：verification-passed, candidate-selected-or-accepted, change-done, current-updated

## 回退路径（发现问题去哪）

- implementation defect → in-layer rework, new revision
- test / check defect → fix the test; never bend product code for green
- design assumption invalidated / design-relevant deviation → SP-05
- new impact discovery / scope growth → SP-04
- requirement semantic gap → requirement authority
- material base context change → context reconciliation (rebase / merge-result build / contract recheck); re-evaluate SP-04 / SP-05 as needed
- shared baseline breakage → owner disposition, restore-first, classify then fix-or-revert
- work package cannot continue (external dependency / missing decision) → work-package blocker; not change BLOCKED (Ch1 non-terminal semantics)

## 证据义务

- 自然证据：['output set itself (code / artifact / migration / config)', 'feedback run records (revision-bound)', 'finding classification and disposition records', 'review approval (revision-bound)', 'ready claim (progress fact fields)']
- 额外证据（仅当）：['deviation proposal', 'classification rationale', 'quarantine decision']
- 证据规则：feedback retention by diagnostic value; full retention not mandated
- Current 更新：writesCurrent = False
  shared integration baseline evolution is an integration fact, not an accepted current release; all current updates go explicitly through SP-19 calibration (SP-19 sealed, group-3 — the interim explicit-recorded-change path by domain authority is formally succeeded by SP-19)

## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data

## 理论回溯

- **part1**：GI-03, GI-05, GI-06, GI-07
- **part2**：ch3-implementation-requirements
- **part3**：source-build-where, structure-health
- **part4**：ch1-progress-fact-and-blocked, ch3-ch4-as-return-layers, ch5-full, ch5-minimum-requirements-checklist

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
