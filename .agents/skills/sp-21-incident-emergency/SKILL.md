---
name: sp-21-incident-emergency
description: 'SP 规程 SP-21 Incident / Emergency｜事件/应急（软件项目开发工程规范指南·第五篇）：Organize a live incident / high-urgency event into controlled emergency engineering facts: open the incident record and make the emergency determination (real harm ongoing or expanding), establish the emergency mitigation objective, record the emergency compression profile (which obligations … 适用触发：incident received；emergency compressed execution；emergency reconciliation；incident follow up。'
metadata:
  spec.part5.sp-id: SP-21
  spec.part5.name: Incident / Emergency
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP21-IncidentEmergency-正式操作规程.md
---

# SP-21 Incident / Emergency｜事件/应急

> 《软件项目开发工程规范指南》第五篇执行规程 SP-21 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Organize a live incident / high-urgency event into controlled emergency engineering facts: open the incident record and make the emergency determination (real harm ongoing or expanding), establish the emergency mitigation objective, record the emergency compression profile (which obligations compressed / substituted / deferred, accepted by whom), fixate the minimum non-disappearing facts and action trace, form the emergency stabilization fact, and after stabilization execute the emergency reconciliation (item-by-item deferred-obligation disposition, successor determination, Ch9 input preparation). Core fact: the Emergency Record.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- incident received
- emergency compressed execution
- emergency reconciliation
- incident follow up

## 操作步骤

### A1 · Incident receipt and emergency determination
控制模式：engineering-decision

- open the incident record (INC + trigger facts + timeline); separate severity (how bad the consequence) from priority (how fast to act — shaped by customer impact / security / workaround / frequency / cost of delay; high severity does not automatically mean immediate code change, P2 §21)
- triage looks at user impact / data / security / blast radius / workaround / recovery cost at minimum (P2 §22)
- emergency determination written against the §8 criterion; if it fails, route to the normal change chain (SP-03 onward) — the incident record still stands

### A2 · Mitigation objective establishment
控制模式：engineering-decision

- state what danger must stop first (stop duplicate charge / stop data loss / restore login / disable vulnerable endpoint, §9)
- separate symptom / immediate cause / contributing factor / latent design problem (P2 §23) — mitigation faces the objective, not the permanent design; causal layering waits for reconciliation and follow-up

### A3 · Compression profile recording
控制模式：automation-assisted

- record per the seven elements: which normal obligations satisfied / compressed / why / with what temporary substitute / risk accepted by whom / what must be done after stabilization / owner (§11)
- "emergency, skip tests"-style records are violations — the profile exists to separate temporarily-deferred from permanently-waived (§12)

### A4 · Stabilization action execution routing
控制模式：engineering-decision

- recovery-class means (rollback / rollforward / disable feature / restore / compensation / traffic shift) route to SP-18 (JG-08); no-software-change operational mitigation splits by behavioral impact — restart / rate-limit style actions that do not change user-visible behavior run under existing operations-domain rules and enter the action trace (A5); traffic cut / flag-off style actions that materially change user behavior are target-changing actions under SP-15 control with SP-16 asset semantics (Ch7 §87, §114); urgent fixes needing new software content go the compressed change path — implementation SP-06 / verification SP-13 at compressed timing with mandatory post-completion (the obligation held by reconciliation)
- a hotfix must know which release it is based on (affected release / fix source / target release / forward-port or backport / compatibility, P2 §20) — cherry-picking from main without this creates new drift
- target-changing actions remain constrained by the SP-15 authority token

### A5 · Action trace and minimum-fact fixation
控制模式：automation

- every material emergency action answers §15's eight questions (who / when / which target / what action / which artifact·config·command / pre-action observation / post-action observation / persistent side effect); immutable audit logs may be referenced rather than copied
- act-first-record-later: operational trace kept contemporaneously, bound to a stable change identity as soon as feasible (§13-14)

### A6 · Stabilization fact formation and state semantics
控制模式：automation-assisted + engineering-decision

- mitigation objective achieved via applicable immediate evidence (duplicate stops / core flow works / error rate stable) -> emergency stabilization fact (§16)
- state expressed truthfully: stabilized != fixed (§17), change stays OPEN + ACTIVE / PAUSED; evidence gaps expressed as NOT_READY / deferred, never rewritten as PASS (§21)
- recovery-action validation facts collected by SP-18, verdicted by SP-17

### A7 · Emergency reconciliation
控制模式：engineering-decision

- execute §22's ten items after stabilization, ending in identifying calibration / current-update obligations and preparing the Ch9 input (never writing "calibration complete" in advance)
- reconciliation barrier check (§24) + the five minimum pre-closure questions (§25) pass before handoff to SP-19
- successor path (§23): what is complete / what transfers / who the successor is / whether it accepts — transfer must be traceably accepted by the successor

### A8 · Postmortem and follow-up
控制模式：engineering-decision

- postmortem size tailored to impact (P2 §25); action items carry owner + priority + verifiable end state (P2 §24) — "be more careful / test more / monitor more" is not an action
- blameless analysis targets system conditions rather than blaming individuals, while retaining accountability (P2 §26)
- recurring-incident cumulative cost enters maintenance priority signals (P2 §62, SP-20 domain); follow-up ledger entries handed to SP-20; the permanent-fix change opens via SP-03

## 硬门禁（不可跳过）

- **G-SP21-01**：emergency-continues-same-change-identity-baseline-evidence-authority-model
- **G-SP21-02**：emergency-determination-requires-section-8-criterion
- **G-SP21-03**：emergency-compression-explicitly-recorded
- **G-SP21-04**：act-first-record-later-preserves-reconstructable-operational-trace
- **G-SP21-05**：stabilization-is-not-permanent-fix-verification-or-closure
- **G-SP21-06**：deferred-obligations-never-waived-by-emergency-alone
- **G-SP21-07**：evidence-gaps-never-rewritten-as-pass
- **G-SP21-08**：reconciliation-complete-or-obligations-transferred-to-accepted-successor
- **G-SP21-09**：gate-zeroing-classification-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = Incident / emergency obligation completed (bound to the INC and the emergency change): mitigation objective achieved with stabilization fact and immediate evidence on record + compression profile and action trace complete (or bound to a stable identity) + reconciliation complete: deferred obligations each completed / transferred (successor accepted) / formally disposed; temporary exceptions exited or handed to governance + follow-up action items in writing (owner + priority + verifiable end state), maintenance-side ledger entries handed to SP-20 + Ch9 input ready -> handoff to SP-19 (calibration / closure)
`



**完成不意味着**：permanent-fix-delivered, recovery-executed, validation-verified, change-closed, follow-up-actions-all-complete

## 回退路径（发现问题去哪）

- mitigation actions cannot achieve the objective → switch means (SP-18 candidate re-selection) / escalate incident level and response face
- post-stabilization validation fails → SP-17 path + new recovery attempt (SP-18); evidence gap recorded truthfully, never rewritten as PASS
- deferred obligations unclaimed → escalate to project owner; never silently waived
- permanent fix evolves into new architecture / long-term scope → successor change (§23); transfer traceably accepted by the successor
- root cause points to a material design problem → SP-05 (via the permanent-fix change)
- root cause points to maintenance-risk face (dependency / EOL / debt) → SP-20 (ledger and capacity disposition)
- recovery material basis missing (anchor invalid / no backup) → SP-18 forward-fix path + SP-20 retention-improvement registration
- reconciliation finds actual modification diverging from records → reconstruct the facts first (§22), divergence enters evidence-gap disposition

## 证据义务

- 自然证据：['incident record (trigger facts + timeline + severity / priority)', 'emergency determination rationale (§8 criterion in writing)', 'emergency compression profile (seven elements)', 'emergency action trace (§15 eight questions / audit-log references)', 'emergency stabilization fact (immediate evidence)', 'deferred-obligation list and item-by-item disposition records', 'temporary-exception registration and exit records', 'emergency reconciliation artifacts (incl. successor transfer and acceptance facts)', 'postmortem / incident note + action items (owner + priority + verifiable end state)']
- 额外证据（仅当）：['gate-zeroing-classification-rationale', 'waiver-decision', 'successor-transfer-decision']
- 证据规则：all other evidence emerges naturally from the work
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-08 处理线上 Incident / Emergency

## 理论回溯

- **part1**：GI-03, GI-05, GI-06, GI-13
- **part2**：p2-ch12-3-incident-mitigation-emergency-boundaries, p2-ch12-18-26-emergency-maintenance-hotfix-severity-postmortem, p2-ch12-56-57-workaround-temporary-mitigation, p2-ch12-62-repeated-incident
- **part3**：p3-ch3-42-60-64-mixed-recovering-state-truthful, p3-ch3-67-recovery-runbook-antipattern, p3-ch8-61-current-drift-anchor
- **part4**：ch8-7-25-emergency-core-semantics, ch8-105-110-workorder-inc77-emergency-example, ch8-131-134-minimum-requirements-and-fields, ch9-closure-interface

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
