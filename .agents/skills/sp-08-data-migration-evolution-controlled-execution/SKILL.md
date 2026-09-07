---
name: sp-08-data-migration-evolution-controlled-execution
description: 'SP 规程 SP-08 Data / Migration Evolution & Controlled Execution｜Data / Migration Evolution（软件项目开发工程规范指南·第五篇）：Run the professional evolution and controlled execution of a change touching persisted data (schema / representation / reference data / change-driven transformation / backfill / production data fix): establish data meaning and ownership facts, design Current -> Target (via Transition when needed) … 适用触发：change touches persisted data；schema constraint index reference data evolution；transformation backfill production fix；data side compatibility evolution。'
metadata:
  spec.part5.sp-id: SP-08
  spec.part5.name: Data / Migration Evolution & Controlled Execution
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP08-DataMigrationEvolution-正式操作规程.md
---

# SP-08 Data / Migration Evolution & Controlled Execution｜Data / Migration Evolution

> 《软件项目开发工程规范指南》第五篇执行规程 SP-08 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Run the professional evolution and controlled execution of a change touching persisted data (schema / representation / reference data / change-driven transformation / backfill / production data fix): establish data meaning and ownership facts, design Current -> Target (via Transition when needed) evolution, manage versioned migration / backfill with execution control, define compatibility combinations and recovery, and organize verification. Code can be redeployed; produced data cannot simply be regenerated. Migration success (no error) != data change correctly completed; rollback != recovery.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- change touches persisted data
- schema constraint index reference data evolution
- transformation backfill production fix
- data side compatibility evolution

## 操作步骤

### A1 · Confirm entry and data touch surface
控制模式：automation-assisted

- locate the change on the data chain (§3); enumerate touched persisted surfaces (schema / constraint / index / reference data / transformation / backfill / production fix, §17, §41-42)
- B1 re-challenge: upstream no-data-impact / additive-zero-risk / low-risk-pure-DDL classifications without resolvable rationale return to SP-04

### A2 · Establish data meaning and ownership facts
控制模式：engineering-decision

- per surface (§65.1 [MUST][BASELINE]): meaning / owner / write authority / invariant; authoritative source and derived positioning (§6-7); null / default semantics (§12-13); identifier stability (§14); time / unit / encoding (§15)
- semantic gaps or unclear owner are filled before evolution design; never design migration on semantic void

### A3 · Define Current / Target / Transition
控制模式：engineering-decision

- start from scoped current data baseline (§59-60); define target; define transition schema when non-atomic compatibility needed (§20)
- explicitly recognize additive / destructive (§22-23); destructive answers five questions: old app? old data? consumer reads? rollback? backup?
- identify direct readers / shared database risk (§44-45)

### A4 · Design migration / backfill
控制模式：engineering-decision

- versioned migration artifact with identity / dependency / order (§16-18, §65.2 [MUST][BASELINE]); externally-controlled schema at least versions external contract / expected schema / compatibility assumption / integration change (§65.2)
- backfill decision explicit (§25, §65.3 [MUST][BASELINE]): allow null / derivable / default / manual fix / unrecoverable
- large backfill designed as production workload: batch / rate limit / pause-resume / checkpoint / observability (§27, §53-54)
- understand the target database's real runtime behavior — lock level / transactional DDL / online index (§50-51); never generalize one database's behavior
- high-risk changes define preconditions by risk (§35)

### A5 · Define compatibility combinations and release coupling
控制模式：engineering-decision

- non-atomic release must define supported combinations on the real release path (§28, §65.4 [MUST][BASELINE]): old-app+new-schema / new-app+old-or-transition-schema / rollback-app+new-data; N-A combos carry rationale (B1)
- decouple from application release to a reasonable degree (§55); no forced five-release split for simple changes
- zero-downtime requirement comes from availability / business requirement, never a default hard target (§56)
- never change production before code, never ship code depending on an unexecuted new schema (§21)

### A6 · Design transition mechanism (when applicable)
控制模式：engineering-decision

- EMC phases (§29) or dual read / dual write / fallback read / shadow write (§30-31) chosen per real plan — never a default template
- dual write must answer four questions (atomic? one fails? divergence detection? authoritative source?) and register owner / exit condition / verification / cleanup + conflict source-of-truth
- every transition mechanism carries an exit condition; an EMC contract phase left uncompleted makes the system worse (§29)

### A7 · Design recovery and verification
控制模式：engineering-decision

- recovery design (§65.5 [MUST][BASELINE] for high risk): pick from §33 means plus failure detection; restart / recovery for long migrations (§34)
- verification plan: postcondition (§36) + risk-scaled independent checks (§37; low-risk pure DDL may suffice with applied state + integration test, classification carries rationale — B1)
- high risk verified on scrubbed production-like data (§52); backup / restore readiness confirmed when applicable (§35, §49)
- verification execution hands off to SP-11 / SP-13; this procedure defines what must be proven

### A8 · Controlled execution of migration / backfill
控制模式：automation + guardrail

- chain: precondition check (block when unmet, §35) -> controlled execution (versioned artifact; no unrecorded manual change, §65.2) -> runtime observability (§53) -> stop/resume with data state legal after stop (§54) -> postcondition proof (§36) -> independent verification (§37) -> migration evidence (§62)
- execution window aligned with SP-15 release-path orchestration; this procedure owns professional responsibility for correct execution and verification of the migration

### A9 · Owner / review organization
控制模式：engineering-decision

- four-role coordination (§57): data meaning owner / application owner / migration executor-operator / reviewer; small teams may combine; high risk adds DBA-platform / security / operations
- review checks §58 fifteen items by risk; checklist per §66 applicability with N-A items carrying rationale (B1); review execution = SP-12

### A10 · Handoff boundaries and registration
控制模式：engineering-decision

- material design layer -> SP-05 (migration / backfill / recovery plans as design input)
- code and migration artifact implementation -> SP-06
- verification execution and candidate conclusion -> SP-11 / SP-12 / SP-13
- release orchestration and target validation -> SP-15 / SP-17 (migration window orchestrated there; execution control stays here)
- production data fix follows the §42 controlled chain; fix artifact is a change artifact, never ad-hoc SQL
- emergency data repair -> Ch8 + SP-21 pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕 (group-5); professional actions and true data state / recovery evidence never exempted (§43)
- transition mechanisms / dual writes / temp compatibility structures registered with exit conditions against permanentization (§29-30)

## 硬门禁（不可跳过）

- **G-SP08-01**：core-data-meaning-owner-write-authority-invariant-explicit
- **G-SP08-02**：schema-out-of-band-data-change-versioned
- **G-SP08-03**：data-change-must-consider-existing-data
- **G-SP08-04**：non-atomic-release-requires-defined-verified-app-schema-combinations
- **G-SP08-05**：high-risk-data-change-requires-recovery-design
- **G-SP08-06**：migration-requires-verification-beyond-exit-code
- **G-SP08-07**：target-never-precovers-current-data-baseline
- **G-SP08-08**：no-dual-write-without-owner-exit-verification-cleanup-and-conflict-sot
- **G-SP08-09**：never-production-first-or-code-depending-on-unexecuted-schema
- **G-SP08-10**：gate-zeroing-judgment-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = `



**完成不意味着**：verification-passed, release-completed, current-data-baseline-updated, derived-data-rebuilt

## 回退路径（发现问题去哪）

- precondition unmet → block execution; back to A4 to fix prerequisites or adjust plan; never gamble on (§35)
- postcondition / independent verification failed → dispose per recovery design (§33); never enter delivery with unexplained inconsistency
- semantic / owner void → back to A2 to fill; never proceed on semantic void
- compatibility combination unsupportable (rollback / old app) → back to A5 to redefine combinations or adjust release orchestration (§28, §55)
- material design problem → SP-05
- dual-write divergence without conflict source-of-truth → stop dual-write progression; back to A6 to define (§31)
- emergency data repair → Ch8 + SP-21 pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕 (group-5) compressed path; §43 record chain and this procedure's evidence never exempted

## 证据义务

- 自然证据：['data evolution record (semantics / ownership / judgment basis)', 'versioned migration artifact + applied state records', 'backfill decision record', 'compatibility combinations with verification status', 'recovery design + (when applicable) restore verification fact', 'migration evidence (§62 ten items)', 'review record (SP-12, revision-bound)']
- 额外证据（仅当）：['backfill-decision', 'na-combination-rationale', 'low-risk-classification-rationale', 'destructive-five-questions', 'dual-write-four-questions-and-exit', 'emergency-repair-record']
- 证据规则：all other evidence emerges naturally from the work
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-01 新项目从 0 到第一条正常 Change（按需）
- JG-02 开发一个新能力 / 修改现有能力（按需）
- JG-04 修改数据库 / Schema / Durable Data

## 理论回溯

- **part1**：GI-03, GI-05
- **part2**：p2-ch8-data-full-chapter, p2-ch7-13-data-contract-boundary-prerequisite
- **part3**：data-shared-infra-runtime-mapping
- **part4**：ch3-data-migration-impact-deepening, ch4-transition-design-handoff, ch5-migration-artifact-implementation, ch7-migration-window-in-release, ch8-emergency-data-repair-path

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
