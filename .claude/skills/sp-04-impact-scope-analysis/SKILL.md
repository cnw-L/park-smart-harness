---
name: sp-04-impact-scope-analysis
description: 'SP 规程 SP-04 Impact / Scope Analysis｜Impact / Scope Analysis（软件项目开发工程规范指南·第五篇）：Understand a Change against truthful Current: identify material effects on engineering facts, dependencies, consumers, verification, delivery and runtime, and convert findings into an Engineering Obligation Profile. Not code search, not full-graph traversal, no design decisions, no final file list. 适用触发：impact entry satisfied；reimpact material context change；reimpact new consumer or version；reimpact requirement meaning change；reimpact implementation deviation。'
metadata:
  spec.part5.sp-id: SP-04
  spec.part5.name: Impact / Scope Analysis
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP04-ImpactScopeAnalysis-正式操作规程.md
---

# SP-04 Impact / Scope Analysis｜Impact / Scope Analysis

> 《软件项目开发工程规范指南》第五篇执行规程 SP-04 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Understand a Change against truthful Current: identify material effects on engineering facts, dependencies, consumers, verification, delivery and runtime, and convert findings into an Engineering Obligation Profile. Not code search, not full-graph traversal, no design decisions, no final file list.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- impact entry satisfied
- reimpact material context change
- reimpact new consumer or version
- reimpact requirement meaning change
- reimpact implementation deviation
- reimpact candidate evidence

## 操作步骤

### A1 · Confirm analysis starting point (SP-03 outputs complete, baseline resolvable)
控制模式：automation


### A2 · Select impact seeds
控制模式：engineering-decision


### A3 · Generate impact claims
控制模式：engineering-decision


### A4 · Execute trace propagation per concern
控制模式：automation-assisted


### A5 · Judge stop reasons; form impact frontier
控制模式：engineering-decision


### A6 · Handle scope expansion
控制模式：engineering-decision

- expansion is a normal outcome, not change drift
- supplementary baseline refs update working baseline with a reason; starting baseline history untouched
- split considered only on scale/risk/owner divergence; never automatic

### A7 · Form confirmed affected scope + concern matrix
控制模式：engineering-decision


### A8 · Classify impact unknowns
控制模式：engineering-decision


### A9 · Form risk driver set
控制模式：engineering-decision


### A10 · Produce engineering obligation profile
控制模式：engineering-decision


### A11 · Form change disposition basis
控制模式：engineering-decision


### A12 · Judge impact sufficiency
控制模式：guardrail + engineering-decision

- sufficient != exhaustive; sufficient != perfect
- no global impact percentage without a stable explainable denominator

## 硬门禁（不可跳过）

- **G-SP04-01**：no-sufficiency-with-impact-blocking-unknowns
- **G-SP04-02**：no-impact-claims-require-per-concern-basis
- **G-SP04-03**：no-design-before-impact
- **G-SP04-04**：tool-confidence-not-engineering-confidence
- **G-SP04-05**：gate-zeroing-classification-requires-resolvable-rationale-evidence

## 通过出口（什么算完成）

`passExit = impact-sufficiency-met AND obligation-profile-formed`



**完成不意味着**：design-ready, all-unknowns-eliminated, affected-scope-is-final-file-list, change-accepted

## 回退路径（发现问题去哪）

- impact-blocking unknown unresolvable → ['clarification to trigger/requirement source', 'or change BLOCKED with owner + recheck trigger']
- baseline ref failure / material current change → working-baseline reconciliation with reason; re-evaluate affected claims; starting baseline untouched
- scope explosion → evaluate split/supersede; do not force one change
- cross-owner coordination failure → explicit external-decision unknown; never a silent propagation stop
- gate-relevant structure finding on critical path → repair finding before judging sufficiency

## 证据义务

- 自然证据：['impact assessment record (navigable from change record)', 'trace snapshots as evidence (snapshot != authority)', 'baseline references on claims', 'stop-reason supporting evidence', 'scope expansion / re-evaluation version history']
- 额外证据（仅当）：['disposition decision', 'rationale']
- 证据规则：
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-01 新项目从 0 到第一条正常 Change
- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data
- JG-05 新增或升级 Dependency / Toolchain / Config

## 理论回溯

- **part1**：GI-02, GI-03, GI-05, GI-07
- **part2**：ch2-requirement, ch4-quality, ch5-architecture, ch7-contract, ch8-data
- **part3**：ch7-trace-mapping, ch8-structure-health-finding
- **part4**：ch1-baseline-context, ch3-full, ch3-minimum-requirements-checklist

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
