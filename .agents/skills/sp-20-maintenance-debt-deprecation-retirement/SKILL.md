---
name: sp-20-maintenance-debt-deprecation-retirement
description: SP 规程 SP-20 Maintenance / Debt / Deprecation / Retirement｜维护/弃用/退役（软件项目开发工程规范指南·第五篇）：Organize every controlled modification of the long-term maintenance phase back into the same change loop (a maintenance request is a change request in maintenance context — no second process), govern the recording and prioritization of long-term burdens (technical debt / workarounds / dependency … 适用触发：maintenance request；debt workaround governance；long term risk input；exit lifecycle。
metadata:
  spec.part5.sp-id: SP-20
  spec.part5.name: Maintenance / Debt / Deprecation / Retirement
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP20-MaintenanceDebtRetirement-正式操作规程.md
---

# SP-20 Maintenance / Debt / Deprecation / Retirement｜维护/弃用/退役

> 《软件项目开发工程规范指南》第五篇执行规程 SP-20 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Organize every controlled modification of the long-term maintenance phase back into the same change loop (a maintenance request is a change request in maintenance context — no second process), govern the recording and prioritization of long-term burdens (technical debt / workarounds / dependency EOL), manage multi-version support and backport, and execute the controlled exit lifecycle deprecation -> EOL -> retirement (including data retirement, zombie-resource prevention, and the final baseline / archive). Core fact: the Maintenance Change.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- maintenance request
- debt workaround governance
- long term risk input
- exit lifecycle

## 操作步骤

### A1 · Entry classification and MR opening
控制模式：engineering-decision

- classify maintenance inputs into the six types (multiple allowed, §17) and settle the boundary: operational handling (restart / rate-limit / config adjustment that changes no software) stays in the operations domain with its workaround governed by A4; anything that modifies software (including emergency follow-up fixes) opens an MR via SP-03 in the same change loop
- scale judgment: system-boundary restructuring / new independent product -> new development effort (§15), classification rationale in writing

### A2 · Long-term risk input conversion
控制模式：engineering-decision

- vulnerability / dependency EOL / platform change / compatibility debt never stops at alerts and inboxes: each converts to an explicit maintenance risk (MR + deadline + impact + upgrade-or-replace plan + verification, §30-32) entering maintenance planning
- quality drift and engineering health signals (§41-42) are equally maintenance planning inputs — deteriorating health metrics (recurrent incidents, escaped defects) are the early form of long-term risk
- vulnerability response loop (assess -> mitigate/fix -> verify -> release -> follow-up, plus root cause and similar-vulnerability check, §27, §76.4) has its follow-up obligation tracked here; the toolchain execution face hands to SP-09

### A3 · Debt registry recording and prioritization
控制模式：engineering-decision

- every technical-debt item registered with six fields (problem / why accepted / current cost-risk / owner / trigger-cleanup condition / affected boundary, §35); priority set per §36 dimensions
- periodic backlog hygiene (close / merge / re-prioritize / promote / explicitly accept — explicit acceptance is a legitimate disposition when in writing, §37)
- absorb specialized debt faces (e.g. SP-16 flag debt) into this single registry
- closure-context debt boundary facts (violates live obligation? still this change's?) are supplied here; the verdict itself belongs to SP-19 (P4 Ch9 §78-81)

### A4 · Workaround / temporary mitigation governance
控制模式：engineering-decision

- each workaround / temporary mitigation (feature disabled / compatibility flag / manual runbook / temporary capacity / emergency config / legacy adapter) registered with why / owner / risk / exit condition (§57)
- a workaround never closes the root cause — its MR stays open until root cause fixed or risk explicitly accepted (§56), else the workaround slides into toil
- recurring-incident cumulative cost (frequency / cumulative cost / trend) feeds the priority signal (§62); root-cause action goes beyond restoring the previous state (§63)

### A5 · Support policy and backport
控制模式：engineering-decision

- multi-version maintenance requires an explicit support policy (scope / versions / horizon)
- a backport is re-assessed in target-version context and opened as an independent change (SP-03); patch completeness rides with the MR — contract / data / docs updated in sync with code (§44)
- verification tailored by risk but never maintenance-exempt (§58); patch releases obey the normal release baseline — "hotfix" is never a reason for an untraceable release (§59)

### A6 · Exit lifecycle execution
控制模式：engineering-decision

- deprecation decision recorded and notified (still usable + migration required); EOL wording bound to the project's own support policy (explicit scope / versions / dates); retirement plan per §70's fourteen items — consumer discovery first (§69), then sequenced execution
- timeline compression / overlap / skipping (three §68 conditions) carries written rationale; impact / communication / final state must stay explicit
- the retirement execution itself is a change: via SP-03 and downstream; delivery face = SP-15, verification = SP-13 / SP-17

### A7 · Data retirement and zombie-resource disposal
控制模式：engineering-decision

- data retirement per §71's ten considerations: legal retention / audit / customer export / backup copy / derived data / search index / cache / analytics aggregates / secrets / encryption keys — derivatives share the retirement obligation
- zombie-resource list (P3 Ch6 §61: old database / topic / queue / namespace / bucket / index / credential / backup / replica) cleaned with the retirement plan; current mapping recalibrated after major data / resource changes (P3 Ch6 §62)
- final baseline / archive per §73's eight items; retention decision (business / legal / security / contract) in writing; shutdown evidence (traffic-zero / access-revoked / data-disposed verification facts) complete before PASS

### A8 · Legacy modification and modernization path
控制模式：engineering-decision

- build characterization evidence (characterization test / observed contract / data snapshot / runtime baseline) before modifying legacy, separating current behavior from target behavior (§49)
- rewrite must be supported by benefit / risk / lifetime — not "the code is old" (§48); large modernization prefers a migratable path (current -> boundary -> incremental replacement -> compatibility -> data migration -> retire old, §50); pattern choice = SP-05 design

## 硬门禁（不可跳过）

- **G-SP20-01**：maintenance-changes-walk-the-controlled-change-loop
- **G-SP20-02**：maintenance-verification-risk-tailored-only
- **G-SP20-03**：emergency-maintenance-requires-follow-up-owner-resolution-cleanup-evidence
- **G-SP20-04**：critical-dependency-platform-eol-becomes-explicit-maintenance-risk
- **G-SP20-05**：vulnerability-response-walks-assess-fix-verify-release-followup-loop
- **G-SP20-06**：debt-six-field-registration-and-no-requirement-renaming
- **G-SP20-07**：maintenance-completion-updates-scoped-current-baseline-scope
- **G-SP20-08**：retirement-controlled-with-consumer-impact-data-handling-shutdown-evidence
- **G-SP20-09**：gate-zeroing-classification-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = Maintenance cycle / single maintenance obligation completed (bound to an MR or governance object): the MR has walked the change loop and the scoped current baseline scope is updated (via SP-19) + when applicable: long-term risk registration in writing (deadline + plan), debt six-field records / workaround governance decisions on file, support / backport decisions on file + when applicable (exit lifecycle): consumer impact / data retirement / zombie list / final baseline / shutdown evidence complete + maintenance metrics signal face continuously available -> handoff to SP-03 (subsequent changes) / SP-19 (current / closure) / SP-21 (emergency reconciliation, when applicable)
`



**完成不意味着**：change-loop-stages-executed, all-debt-repaid, incident-closed, execution-assets-governed

## 回退路径（发现问题去哪）

- MR lacking need / impact facts → complete the facts before entering the loop (returned at SP-03 entry)
- emergency follow-up obligation unclaimed → escalate to project owner for decision; never silently parked
- debt item cannot get an owner → register as unowned debt and raise as a capacity / priority trade-off topic (§64)
- backport infeasible in target version → close that backport MR honestly with recorded reason; never force a cherry-pick
- consumer cannot migrate before EOL → support-policy adjustment or deferral decision in writing (requirement authority decides)
- retirement blocked (data / legal / contract) → route to data / legal / contract handling (SP-08 / SP-07 interfaces); final state deferred but explicit
- material design problem (exit path / modernization path unsound) → SP-05
- closure-boundary dispute (renamable as debt?) → SP-19-domain verdict (P4 §78-81)

## 证据义务

- 自然证据：['MR records (classification + priority basis)', 'long-term risk registrations (EOL / vulnerability: deadline + plan + follow-up)', 'debt registry entries (six fields) and backlog-hygiene records', 'workaround / temporary mitigation governance records (owner + exit condition)', 'support policy and backport re-assessment records', 'deprecation notice / retirement plan / data retirement disposition / zombie cleanup / final baseline / shutdown evidence', 'maintenance metrics signals (EA-15)']
- 额外证据（仅当）：['gate-zeroing-classification-rationale', 'explicit-debt-acceptance', 'timeline-compression-rationale', 'rewrite-or-new-effort-judgment', 'retention-period-decision']
- 证据规则：all other evidence emerges naturally from the work
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-09 维护、弃用、替换或 Retirement

## 理论回溯

- **part1**：GI-03, GI-05, GI-06, GI-13
- **part2**：p2-ch12-1-9-maintenance-scope-and-boundaries, p2-ch12-10-17-six-types-no-second-process, p2-ch12-18-26-emergency-triage-security-interface, p2-ch12-27-32-vulnerability-dependency-eol-risk, p2-ch12-33-40-debt-six-fields-priority-backlog-toil, p2-ch12-43-47-scoped-current-support-backport, p2-ch12-48-50-legacy-rewrite-characterization, p2-ch12-51-57-knowledge-handover-workaround, p2-ch12-58-66-verification-release-metrics-capacity, p2-ch12-67-73-retirement-lifecycle, p2-ch12-76-minimum-requirements
- **part3**：p3-ch1-D-current-structure-baseline-scope, p3-ch6-61-zombie-resource, p3-ch6-62-data-infrastructure-calibration, p3-drift-debt-eol-as-drift-source
- **part4**：ch7-mr-in-same-change-loop-execution-context, ch8-emergency-compression-interface, ch9-77-83-debt-closure-boundary-and-post-closure

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
