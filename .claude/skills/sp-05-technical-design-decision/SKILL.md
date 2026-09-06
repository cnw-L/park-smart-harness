---
name: sp-05-technical-design-decision
description: 'SP 规程 SP-05 Technical Design / Decision｜Technical Design / Decision（软件项目开发工程规范指南·第五篇）：Convert impact conclusions into an executable, evolvable solution: state the facts that must hold at Target, design a safe Transition to reach it, form an Accepted Design, and split out execution-ready Work Packages. 适用触发：impact sufficiency passed；design reevaluation；material plan change upgrade。'
metadata:
  spec.part5.sp-id: SP-05
  spec.part5.name: Technical Design / Decision
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP05-TechnicalDesignDecision-正式操作规程.md
---

# SP-05 Technical Design / Decision｜Technical Design / Decision

> 《软件项目开发工程规范指南》第五篇执行规程 SP-05 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Convert impact conclusions into an executable, evolvable solution: state the facts that must hold at Target, design a safe Transition to reach it, form an Accepted Design, and split out execution-ready Work Packages. Design is change-local authority; Accepted Design is not Current Software Fact, not release completion, and not a permanent freeze.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- impact sufficiency passed
- design reevaluation
- material plan change upgrade

## 操作步骤

### A1 · Confirm design entry inputs
控制模式：automation

- unaccepted requirement must not be used as current requirement
- re-check upstream gate-zeroing classifications (SP-04 unknown routing, no-impact basis) for resolvable rationale/evidence; challenge disguised ones back to SP-04

### A2 · Write target design
控制模式：engineering-decision

- baseline-scoped; inherits confirmed affected scope and risk driver set
- understandable by later verification and comparable by calibration
- target non-goals required
- no unrelated future wishlist
- target must not be secretly shrunk for implementation convenience (shrinking = back to SP-04)

### A3 · Resolve each engineering obligation
控制模式：engineering-decision

- **判定词汇**：
  - designed
  - n-a-with-reason
  - delegated
  - blocking
- delegated is explicit handoff with recipient, not "later"
- gate-zeroing dispositions (n-a / delegated) require resolvable, challengeable rationale; the recipient must exist and have been informed

### A4 · Design transition when applicable
控制模式：engineering-decision

- exit condition must not rest on date alone
- transition without cleanup becomes transition leak
- recovery direction != rollback; obeys data semantics; risk-of-recovery considered; partial failure has designed semantics
- expand/migrate/contract are patterns, not fixed procedure; contracting too early is a classic incident
- no global day-count; may span multiple releases
- target becomes new-current candidate only after transition ends

### A5 · Separate decision, assumption and alternative
控制模式：engineering-decision

- alternative analysis only when a real material alternative exists
- no fabricated alternatives to pad the record
- ADR may carry a decision; ADR != the whole change design

### A6 · Classify design open items
控制模式：automation + engineering-decision


### A7 · Judge scoped design sufficiency
控制模式：guardrail + engineering-decision

- judged per scope; no whole-change single freeze
- scoped sufficiency must not bypass key boundaries (data authority / irreversible contract)
- shared guardrail revision change reopens existing scoped sufficiency (coherence, not a new freeze gate)

### A8 · Accept and anchor the design
控制模式：engineering-decision

- bind design revision + corresponding impact revision
- forms design-sufficient progress fact
- accepted design must be discoverable and versioned
- acceptance may be revoked with reason
- design DRI != change owner != architecture authority; review depth follows risk; async allowed

### A9 · Form execution plan and work packages
控制模式：automation + engineering-decision

- split by target slice, by transition phase, or both
- design <-> work package bidirectionally traceable; no work package from personal memory
- execution dependency is not source-only (schema expand -> writer; consumer compat -> mixed rollout; cross-team)
- parallel allowed but shared boundary must not be ignored
- execution-ready is scoped readiness; must not lock an unresolved critical decision
- enabling work allowed but stays under change/design trace
- plan evolves; plan change upgrades design only when target / transition / key boundary affected
- SP-05 keeps semantic ownership of the execution plan; in-flight plan adjustments (SP-06 A9) are appended to the change record as plan revisions consumable by this procedure's re-evaluation triggers; the "no layer change" judgement must cite the WP's registered re-evaluation trigger list, never the implementer's say-so

### A10 · Register re-evaluation triggers
控制模式：engineering-decision


## 硬门禁（不可跳过）

- **G-SP05-01**：no-design-before-impact
- **G-SP05-02**：no-sufficiency-with-blocking-open-items
- **G-SP05-03**：no-sufficiency-without-critical-assumption-validation-plan
- **G-SP05-04**：no-implementation-with-unresolved-blocking-obligation
- **G-SP05-05**：accepted-design-never-written-to-current
- **G-SP05-06**：gate-zeroing-disposition-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = scoped-design-sufficiency-passed AND accepted-design-anchored AND execution-plan-exists AND at-least-one-work-package-execution-ready AND re-evaluation-triggers-registered`



**完成不意味着**：all-questions-answered, formal-documents-complete, review-meeting-held, implementation-done-or-candidate-accepted

## 回退路径（发现问题去哪）

- design entry inputs missing → spike/draft allowed without formal-basis claim; return to SP-03 / SP-04 to complete
- blocking open item cannot converge → design-insufficient with gap + owner + next step; may return to SP-04 or requirement clarification
- critical assumption validation fails → material design change -> new design revision (history preserved)
- material context change / hidden consumer found → return to the layer registered in A10
- implemented work package meets design revision → no automatic rework; evaluate per revision applicability

## 证据义务

- 自然证据：['accepted design revision (carrier-free: design doc / issue / PR description / ADR set)', 'obligation resolution record', 'transition design and invariants', 'critical assumption + validation plan', 'work package definitions and dependencies', 'sufficiency judgement record']
- 额外证据（仅当）：['decision', 'rationale']
- 证据规则：design and execution plan versioned; fixed filenames not mandated
- Current 更新：writesCurrent = False
  design revision never auto-updates current design; target becomes new-current candidate only after transition ends (for no-transition changes: after outputs ready + Ch6 acceptance), via SP-19 calibration — SP-19 sealed (group-3); the interim domain-authority calibration path is formally succeeded by SP-19

## 所属 Journey

- JG-01 新项目从 0 到第一条正常 Change
- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data

## 理论回溯

- **part1**：GI-02, GI-03, GI-05, GI-07
- **part2**：ch3-technical-solution, ch5-architecture
- **part3**：ch4-target-transition-projection
- **part4**：ch3-inputs, ch4-full, ch4-minimum-requirements-checklist

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
