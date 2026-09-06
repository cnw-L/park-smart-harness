---
name: sp-22-execution-asset-lifecycle
description: 'SP 规程 SP-22 Execution Asset Lifecycle｜执行资产生命周期（软件项目开发工程规范指南·第五篇）：Govern the lifecycle of execution assets themselves — guides, templates, workflows, scripts, reference profiles, operation contract schemas — isomorphically with software: register every asset with its seven-element identity (owner / version / compatibility / tests / consumers / deprecation / … 适用触发：new asset creation；asset modification request；asset version release；asset exit supersession drift。'
metadata:
  spec.part5.sp-id: SP-22
  spec.part5.name: Execution Asset Lifecycle
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP22-ExecutionAssetLifecycle-正式操作规程.md
---

# SP-22 Execution Asset Lifecycle｜执行资产生命周期

> 《软件项目开发工程规范指南》第五篇执行规程 SP-22 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Govern the lifecycle of execution assets themselves — guides, templates, workflows, scripts, reference profiles, operation contract schemas — isomorphically with software: register every asset with its seven-element identity (owner / version / compatibility / tests / consumers / deprecation / replacement-migration), run asset modifications as normal engineering changes through the same change loop, judge asset version compatibility and consumer impact, maintain the guide current surface (which versions valid / superseded / mirror sync), dispose of guide drift, and prove real usability via golden path regression. Core fact: current asset version. An asset modification is itself an engineering change — "just a doc / template / script" is never a bypass; an asset without seven-element registration may not be referenced by consumers; publication mirrors and research evidence do not gain normative status by existing.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- new asset creation
- asset modification request
- asset version release
- asset exit supersession drift

## 操作步骤

### A1 · Asset identity confirmation and registry entry
控制模式：automation

- confirm the asset and version behind the trigger face; new assets enter the registry with all seven elements; existing assets checked for drift (no owner / no version / unknown consumers — treated as asset debt)
- assets without seven-element registration may not be referenced; "internal asset, no registration needed" is gate-zeroing, carries rationale (B1)

### A2 · Asset modification opened as a normal change
控制模式：engineering-decision

- convert the request into an asset change via SP-03, carrying trigger facts, impact face (which consumers / which versions), modification intent
- scope explicitly includes the asset itself and affected-consumer migration obligations
- B1 re-challenge: "it's just docs" fails — a doc is an asset, an asset change is an engineering change

### A3 · Compatibility judgment and consumer impact
控制模式：engineering-decision

- judge the asset interface (check names / commands / directories / schema fields / generated structure) via the four-perspective semantics reused from SP-07 — no redefinition
- compatible -> in-place upgrade path allowed; breaking -> per-consumer migration plan (path / deadline / support window)
- consumer impact facts come from the registry's consumers element — a compatibility judgment without consumer facts is idle

### A4 · Asset version release and controlled rollout
控制模式：engineering-decision

- progressive release (opt-in -> progressive -> default for new consumers -> legacy migration), each step rollbackable; rollout execution control belongs to SP-15
- references must pin to a committable version (@v3 / digest); uncontrolled @main references to multi-consumer assets are prohibited
- breaking changes: old version stays usable until migration completes (deprecation semantics reused from SP-20) — with deadline and owner

### A5 · Golden path regression validation
控制模式：automation + guardrail

- by asset type: template -> generate + build; reusable workflow -> real run on a sample repo; contract schema -> real contract validation + shape conformance (CLI / SDK / service faces covered); guide asset -> navigation resolvable (links alive, current discoverable)
- the pass standard is the master map §G ten questions, not author self-assessment; validation framework reused from SP-11 / SP-13 — this procedure holds the asset-specific regression list

### A6 · Guide current surface maintenance
控制模式：automation

- after each asset version event update: valid versions, superseded versions (with supersession facts — successor, stop date), mirror sync status, registry verification time
- the five questions being answerable is a hard condition; when they are not, fix navigation before shipping new versions

### A7 · Guide drift disposition
控制模式：engineering-decision

- conflicting non-owner surfaces (stale indexes, outdated summaries, coexisting copies) -> register guide drift -> repair the non-owner face to the designated owner (no compromise, no coexistence) -> cross-part regression confirming no second semantics
- supersession follows Ch8 §58 — not "cancelled plus a note link": the old surface's authority is revoked, the successor is explicit and traceable

### A8 · Asset feedback loop maintenance
控制模式：automation-assisted

- collect real-use evidence (golden path breakage, misfiring gates, template defects, obsolete spec faces) into the asset feedback backlog; signals enter the SP-20 maintenance-priority ledger face
- high-value feedback converts to A2 asset changes; feedback-loop evidence references real work facts (GI-06), not sentiment

## 硬门禁（不可跳过）

- **G-SP22-01**：asset-modification-runs-controlled-change-loop
- **G-SP22-02**：referenced-assets-require-seven-element-registration
- **G-SP22-03**：asset-upgrade-requires-compatibility-and-consumer-disposition
- **G-SP22-04**：asset-reference-pinned-and-rollout-progressive
- **G-SP22-05**：guide-current-surface-answers-five-questions
- **G-SP22-06**：mirror-and-research-evidence-not-normative
- **G-SP22-07**：guide-drift-registered-repaired-regressed
- **G-SP22-08**：usability-proven-by-golden-path-regression
- **G-SP22-09**：gate-zeroing-classification-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = Execution asset obligations complete (bound to the asset change): asset seven-element registration complete and consistent with real state + asset change walked the applicable SP chain (SP-03 opening -> applicable implementation / validation SPs -> SP-15 delivery) + compatibility judgment and consumer impact disposition in writing (breaking changes carry per-consumer migration plans with deadlines) + golden path regression evidence on record (actual runs against §G's ten questions) + guide current surface updated (incl. supersession facts) -> asset feedback backlog updated; consumer migration obligations handed to each consuming project's normal chain
`



**完成不意味着**：all-consumers-migrated, asset-exit-lifecycle-complete, consumer-project-current-updated, asset-carried-professional-semantics-revised

## 回退路径（发现问题去哪）

- asset modification reveals a material design problem → SP-05 (asset architecture / interface redesign)
- breaking change with no feasible migration path → reopen version strategy (new major / dual-track transition); consult SP-07 migration semantics as needed
- golden path regression fails → repair the asset (back to SP-06) — no shipping broken with "fix in the next version"
- consumer migration overdue / unowned → register asset debt (SP-20 maintenance-priority face); old-version support windows never silently extended
- asset obsolescence traced to a downstream SP revision → spec evolution input -> the corresponding SP's revision change; this procedure never edits professional semantics
- guide drift repair spans parts → GI-12 process (resolve owner by concern + scope -> repair -> cross-part regression); no intra-part private settlement
- emergency asset fix (template broken on a production path) → SP-21 same compressed model + mandatory reconciliation; this procedure invents no bypass

## 证据义务

- 自然证据：['asset registry entries (seven elements + version events)', 'asset change records (trigger facts + impact face + modification content)', 'compatibility judgments and consumer migration plans', 'asset version release and rollout records (version pin facts)', 'guide current surface state (incl. registry verification time)', 'guide drift registration and repair records', 'golden path regression run evidence']
- 额外证据（仅当）：['gate-zeroing-classification-rationale', 'breaking-judgment-rationale', 'supersession-decision', 'migration-deadline-decision']
- 证据规则：all other evidence emerges naturally from the work
- Current 更新：writesCurrent = False
  

## 所属 Journey

（通用规程）

## 理论回溯

- **part1**：GI-03, GI-06, GI-11, GI-12, GI-13, GI-14, GI-17, p1-4.5-guide-current-surface, p1-10.1-asset-classes, p1-10.2-guide-current-surface-five-questions
- **part2**：p2-ch1-2-engineering-foundation, p2-ch1-4.3-minimum-engineering-requirements, p2-ch1-16.3-long-term-drift-protection, p2-ch12-maintenance-assets-as-maintained-objects
- **part3**：p3-ch5-source-build-structure, p3-ch8-current-structure-drift
- **part4**：ch1-change-execution-general-principles, ch2-establishment-baseline-binding, ch8-58-superseded-is-not-a-note-link, ch9-closure-current

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
