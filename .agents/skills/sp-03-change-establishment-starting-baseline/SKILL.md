---
name: sp-03-change-establishment-starting-baseline
description: 'SP 规程 SP-03 Change Establishment / Starting Baseline｜Change Establishment（软件项目开发工程规范指南·第五篇）：Bring a valid Engineering Trigger under engineering control: establish stable Change identity + minimum record, bind a truthful Starting Baseline, so that Impact has an honest starting point. Never approves, never designs, never creates any Baseline Transition. 适用触发：valid trigger crossed boundary；first change after governance cutover；incident emergency fix；maintenance debt deprecation followup；spike conclusion entering product source。'
metadata:
  spec.part5.sp-id: SP-03
  spec.part5.name: Change Establishment / Starting Baseline
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP03-ChangeEstablishmentBaselineBinding-正式操作规程.md
---

# SP-03 Change Establishment / Starting Baseline｜Change Establishment

> 《软件项目开发工程规范指南》第五篇执行规程 SP-03 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Bring a valid Engineering Trigger under engineering control: establish stable Change identity + minimum record, bind a truthful Starting Baseline, so that Impact has an honest starting point. Never approves, never designs, never creates any Baseline Transition.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- valid trigger crossed boundary
- first change after governance cutover
- incident emergency fix
- maintenance debt deprecation followup
- spike conclusion entering product source

## 操作步骤

### A1 · Confirm trigger validity and control-boundary crossing
控制模式：engineering-decision


### A2 · Check duplicate / related / superseded changes
控制模式：engineering-decision


### A3 · Establish change identity + minimum establishment record
控制模式：automation


### A4 · Bind change owner
控制模式：engineering-decision


### A5 · Form initial scope hypothesis
控制模式：engineering-decision


### A6 · Execute baseline binding (selection driven by intent/scope, not full-set)
控制模式：automation-assisted

- branch-name-is-not-an-audit-anchor
- runtime-state-binds-via-observation-or-deployment-record
- requirement/contract/data bind as authority refs, never copied content

### A7 · Dispose findings carried from SP-01
控制模式：engineering-decision

- {'authority-conflict': 'stop contested semantics; designated owner rules per concern+scope (GI-12)'}
- {'known-stale-current': 'tag health-affected; schedule calibration via SP-19'}
- {'irrelevant-finding': 'record linkage, does not auto-block'}

### A8 · Classify open engineering questions
控制模式：engineering-decision

- **判定词汇**：
  - blocking-question
  - managed-unknown
- insufficient info defaults to BLOCKED, never auto-REJECT
- classifications that zero a hard gate (e.g. managed-unknown) must carry resolvable rationale / evidence pointers; downstream (SP-04 A1) may challenge disguised classifications back to this procedure

### A9 · Judge Impact Entry Condition
控制模式：guardrail + engineering-decision


## 硬门禁（不可跳过）

- **G-SP03-01**：no-substantive-impact-without-change-record
- **G-SP03-02**：baseline-ref-must-resolve-to-revision-with-scope
- **G-SP03-03**：no-impact-with-unresolved-blocking-question
- **G-SP03-05**：gate-zeroing-classification-requires-resolvable-rationale-evidence
- **G-SP03-06**：no-baseline-binding-on-current-context-without-SP01-pass-evidence

提示级：
- G-SP03-04：establishment-itself-is-not-a-gate

## 通过出口（什么算完成）

`passExit = impact-entry-condition-satisfied`



**完成不意味着**：requirement-accepted, design-ready, implementation-authorized, affected-scope-confirmed

## 回退路径（发现问题去哪）

- trigger invalid / boundary not crossed → return to trigger source, or downgrade to spike / investigation
- duplicate or should-supersede → merge / link / supersession fence; do not create new identity
- baseline binding failure (dangling ref / unclear scope / unresolved authority) → SP-01 §10 finding paths; no Impact until repaired
- blocking question unresolved → record state OPEN + execution condition BLOCKED + owner + recheck trigger
- owner cannot be designated → escalate to project governance (same bar as SP-02 R0 owner-resolvable)

## 证据义务

- 自然证据：['change record itself (Issue / PR / dedicated record)', 'pinned baseline references inside the record', 'owner binding / handoff record', 'open question classification + disposition']
- 额外证据（仅当）：['blocking-question clarification decision', 'rationale']
- 证据规则：
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-00 进入已有项目并找到 Current
- JG-01 新项目从 0 到第一条正常 Change
- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data
- JG-05 新增或升级 Dependency / Toolchain / Config
- JG-08 处理线上 Incident / Emergency（按需）
- JG-09 维护、弃用、替换或 Retirement

## 理论回溯

- **part1**：GI-01, GI-02, GI-03, tailoring-9.2, tailoring-9.3
- **part2**：requirement, project-engineering
- **part3**：ch1, ch2, ch8-current-reference-semantics
- **part4**：ch1-change-identity-record-owner, ch1-starting-working-baseline-context, ch1-record-state-execution-condition, ch2-full

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
