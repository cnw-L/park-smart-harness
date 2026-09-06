---
name: sp-07-contract-evolution
description: 'SP 规程 SP-07 Contract Evolution｜Contract Evolution（软件项目开发工程规范指南·第五篇）：Run the professional evolution of a change that touches cross-boundary contracts: establish contract current facts (Current Baseline / Stability / Lifecycle / consumer picture), judge compatibility and breaking change across four views (Source / Wire / Semantic / Operational), choose the evolution … 适用触发：change touches cross boundary contract；contract add evolve retire；de facto dependency governance；removal condition due。'
metadata:
  spec.part5.sp-id: SP-07
  spec.part5.name: Contract Evolution
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP07-ContractEvolution-正式操作规程.md
---

# SP-07 Contract Evolution｜Contract Evolution

> 《软件项目开发工程规范指南》第五篇执行规程 SP-07 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Run the professional evolution of a change that touches cross-boundary contracts: establish contract current facts (Current Baseline / Stability / Lifecycle / consumer picture), judge compatibility and breaking change across four views (Source / Wire / Semantic / Operational), choose the evolution strategy (backward-compatible evolution / Parallel Change / new major), and organize deprecation / removal governance. Contract != Interface != Schema; structural compatibility != contract compatibility; version is a tool, not a compatibility strategy itself.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- change touches cross boundary contract
- contract add evolve retire
- de facto dependency governance
- removal condition due

## 操作步骤

### A1 · Confirm entry and contract touch surface
控制模式：automation-assisted

- enumerate all cross-boundary contracts touched; classify by six types (§8); governance strength by consumer independence (§7)
- B1 re-challenge: upstream no-contract-impact / internal-only classifications without resolvable rationale return to SP-04

### A2 · Establish contract current facts
控制模式：engineering-decision

- resolve Current Contract Baseline per contract (§67-69), Stability x Lifecycle (§28), provider / consumer (§19)
- build consumer picture (§43-44): who / which versions / external? / force-upgradable? / long-offline clients? / persisted old messages?
- the less visible the consumer, the more conservative the provider
- register de-facto dependencies; disposition = promote / migration window / explicit stop-support (§37)

### A3 · Contract diff and compatibility judgment
控制模式：engineering-decision

- produce before/after comparison (§66): OpenAPI diff / proto checker / schema-registry compatibility / git diff / manual semantic review
- judge across four views (§32-36) against the §38-42 breaking list
- judgment carries basis (B1): "compatible" explains each view; "breaking" names the commitment facet touched
- judgment is re-challengeable by SP-05 / SP-13 / group audit

### A4 · Choose evolution strategy
控制模式：engineering-decision

- priority (§45): backward-compatible evolution -> Parallel Change / migration -> new major / new contract only when necessary
- non-atomic upgrade must first define supported version combinations (§73.4 [MUST][BASELINE]): old-consumer+new-provider always; new-consumer+ old-provider when rolling/independent deploy; rollback combos (§75); stored old message/data (§76)
- express combinations + verification status in a Compatibility Matrix (§74); N/A combos must be real and consistent with deployment / rollback strategy — N/A is a gate-zeroing judgment and carries rationale (B1)

### A5 · Parallel Change phase control (when applicable)
控制模式：engineering-decision + guardrail

- define Expand / Migrate / Contract phases (§48-52); applies to any non-atomic provider/consumer scenario, not only HTTP APIs
- every compatibility layer gets cleanup condition + owner (§51)
- migrate-phase state (who migrated / who not) truthfully maintained; no permanent dual-stack

### A6 · Deprecation / removal governance (when applicable)
控制模式：guardrail + engineering-decision

- {'deprecation record': '8 fields (§53)'}
- removal condition over arbitrary dates (§55); stability level shapes the deprecation promise (§56)
- a label without migration target / state / exit condition is a comment, not deprecation (§54)

### A7 · Contract artifact and verification strategy
控制模式：engineering-decision

- authoritative discoverable current contract source (§57); machine-readable artifact preferred for multi-consumer long-lived HTTP APIs (§58-59); events use AsyncAPI / schema + event semantics (§60); proto discipline (§61)
- verification strategy covers applicable facets of §65: shape / semantic rule / error / default / compatibility / authorization / ordering-delivery / idempotency
- contract test / CDC introduced per fit conditions (§63-64); execution hands off to SP-11 / SP-12 / SP-13 — this procedure only defines which commitment facets must be verified

### A8 · Review organization and owner confirmation
控制模式：engineering-decision

- contract owner duties (§70): provider owner vs consumer owner; external consumers managed via documentation / support / telemetry / communication
- review covers risk boundaries by type (§71); checklist by applicability (§72) with N-A items carrying rationale (B1); review execution = SP-12

### A9 · Handoff and downstream boundaries
控制模式：engineering-decision

- material design layer -> SP-05 (evolution strategy and compatibility conclusions as design input; Parallel Change phase plan feeds transition design)
- implementation (incl. contract-artifact sync hard rule) -> SP-06
- verification execution and candidate conclusion -> SP-11 / SP-12 / SP-13
- delivery and target validation -> SP-15 / SP-17
- emergency breaking change (§77 four cases) -> Ch8 + SP-21 pending-definition (group-5) for compressed execution and reconciliation; the 8 minimum records and this procedure's compatibility analysis are never exempted

### A10 · Contract debt and health registration
控制模式：guardrail

- register compatibility layers / permanent dual versions / never-removed deprecations / cross-boundary DB reads / duplicate events / temp adapters / compatibility flags with risk + owner + cleanup condition (§78)
- long-lived projects may observe health signals (§79); never forced KPI

## 硬门禁（不可跳过）

- **G-SP07-01**：no-silent-breaking-of-stable-contract
- **G-SP07-02**：non-atomic-upgrade-requires-defined-verified-version-combinations
- **G-SP07-03**：deprecated-contract-requires-replacement-migration-owner-removal-condition
- **G-SP07-04**：stable-boundary-requires-explicit-contract
- **G-SP07-05**：machine-diff-or-schema-compat-never-final-breaking-verdict
- **G-SP07-06**：no-blind-change-of-key-contract-without-consumer-knowledge
- **G-SP07-07**：no-compatibility-layer-without-cleanup-condition-and-owner
- **G-SP07-08**：proposed-contract-never-precovers-current
- **G-SP07-09**：unchanged-version-string-never-claims-no-breaking
- **G-SP07-10**：gate-zeroing-judgment-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = Contract Evolution Plan established (bound to contract identity + current baseline revision): four-view compatibility judgment with basis per touched contract + explicit evolution strategy (backward-compatible / Parallel Change phase plan / new major) + verification strategy covering applicable commitment facets (§65) + when applicable: matrix combinations with verification status, deprecation record, compatibility-layer cleanup obligations -> handoff to SP-05 (when material) / SP-06
`



**完成不意味着**：verification-passed, contract-released, consumers-migrated, current-contract-updated

## 回退路径（发现问题去哪）

- consumer picture unknowable and change is key → build consumer information first (§43-44 lightweight means); otherwise only conservative strategy; blind change forbidden (G-SP07-06)
- verification strategy coverage insufficient → back to A7 to add commitment facets
- material design problem (transition / target change) → SP-05
- de-facto dependency dispute → explicit three-way disposition (§37); never shelved
- rollback / stored-message combination unsupportable → back to A4 to redefine combinations or adjust release strategy (§75-76)
- emergency breaking → Ch8 + SP-21 pending-definition (group-5) compressed path; §77 eight records and this procedure's compatibility analysis never exempted

## 证据义务

- 自然证据：['contract evolution record (judgment + strategy + basis)', 'contract diff (machine + manual semantic comparison)', 'compatibility matrix (when applicable)', 'deprecation record / removal evaluation (when applicable)', 'review record (SP-12, revision-bound)']
- 额外证据（仅当）：['breaking-judgment-rationale', 'na-combination-rationale', 'de-facto-disposition-decision', 'emergency-eight-records']
- 证据规则：all other evidence emerges naturally from the work
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-01 新项目从 0 到第一条正常 Change（按需）
- JG-02 开发一个新能力 / 修改现有能力（按需）
- JG-03 修改公共 API / Event / Contract

## 理论回溯

- **part1**：GI-03, GI-05
- **part2**：p2-ch7-contract-full-chapter, p2-ch6-module-public-capability-prerequisite
- **part3**：contract-consumer-mapping
- **part4**：ch3-contract-impact-deepening, ch4-transition-design-handoff, ch5-contract-artifact-sync-rule, ch8-emergency-breaking-path

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
