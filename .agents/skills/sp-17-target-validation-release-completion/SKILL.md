---
name: sp-17-target-validation-release-completion
description: SP 规程 SP-17 Target Validation / Release Completion｜目标验证/可观测（软件项目开发工程规范指南·第五篇）：On an explicit delivery target / deployment attempt / rollout slice, validate whether the software state actually present in the target environment — runtime behavior, dependencies, data / migration, transition invariants, applicable business / quality requirements — meets the conditions this … 适用触发：attempt done or slice in place；evidence arrives or gap visible；maturity event；completion decision point；post recovery。 边界：Never re-runs the Ch6 required verification set (SP-13), never controls deployment / rollout execution (SP-15), never owns feature exposure …
metadata:
  spec.part5.sp-id: SP-17
  spec.part5.name: Target Validation / Release Completion
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP17-TargetValidation-正式操作规程.md
---

# SP-17 Target Validation / Release Completion｜目标验证/可观测

> 《软件项目开发工程规范指南》第五篇执行规程 SP-17 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

On an explicit delivery target / deployment attempt / rollout slice, validate whether the software state actually present in the target environment — runtime behavior, dependencies, data / migration, transition invariants, applicable business / quality requirements — meets the conditions this delivery / release acceptance requires; render per-target-scope SATISFIED / FAILED / NOT_READY assessments and the target release completion decision; and migrate the accepted current release through the Ch1 ledger after completion. Target validation is not a Ch6 rerun, pass is not deployment success, evidence gaps are NOT_READY not FAIL, and unmet validation maturity stays NOT_READY regardless of smoke / deploy green.


## 边界（本规程不做的事）

Never re-runs the Ch6 required verification set (SP-13), never controls deployment / rollout execution (SP-15), never owns feature exposure strategy (SP-16 — pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕, group-5) or recovery execution detail (SP-18 — pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕, group-5; until it lands, recovery execution follows P4 Ch7 §89-102 directly and SP-15 keeps the execution records), and never performs change closure or project-level current updates (SP-19). Its only current write is the per-target-scope accepted current release ledger transition after target release completion.


## 触发

- attempt done or slice in place
- evidence arrives or gap visible
- maturity event
- completion decision point
- post recovery
- validation evidence gap

## 操作步骤

### A1 · Derive the required target validation set
控制模式：engineering-decision + guardrail

- per release baseline + delivery target + rollout / transition scope
- concerns picked by applicability from the twelve-item list; N-A items carry rationale (B1)
- never a Ch6 full-set rerun — answers "did it become the expected runtime fact in this target"

### A2 · Declare validation maturity conditions
控制模式：engineering-decision

- per obligation where needed: representative traffic floor / required background cycle / reconciliation complete / queue settled / no new invariant violation during the observation condition
- risk / behavior drives maturity; a global fixed soak time never substitutes the semantics; undeclared-never-missing
- obligations with no maturity need record the instant-evidence judgement

### A3 · Bind target evidence
控制模式：automation + guardrail

- six elements bound at production time; subject explicit to attempt / slice / target state; context records actual resolution
- signals must decompose by version / cohort to this slice / attempt; under-attributed evidence gets an applicability limitation

### A4 · Execute validation and record results truthfully
控制模式：automation + guardrail

- valid evidence proves satisfaction = PASS
- only valid evidence explicitly proving non-satisfaction = FAIL
- unavailable evidence / environment / window / unknown outcome = NOT_READY + gap record
- deployment tool success is never a PASS basis

### A5 · Judge maturity satisfaction
控制模式：guardrail


### A6 · Form the target validation assessment
控制模式：guardrail

- all applicable obligations satisfied -> SATISFIED; any valid FAIL -> FAILED; undisposed gap / unmatured obligation -> NOT_READY
- always per explicit target scope

### A7 · Dispose gaps and findings
控制模式：engineering-decision + authority

- **处置选项**：
  - alternative-evidence
  - controlled-exception
  - block-decision
- high-risk scenarios never proceed on "looks fine" under an evidence gap
- candidate-defect evidence routes to SP-15 A11 as candidate-defect-in-target
- target environment defects route to SP-15 / platform domain without touching candidate disposition

### A8 · Decide target release completion
控制模式：decision-point

- satisfied -> issue the completion record with explicit target scope
- otherwise stay and record the gap
- completion is a decision / progress fact, never change closure

### A9 · Migrate accepted current release via the ledger
控制模式：automation + guardrail

- after completion, register the target scope's accepted current release transition through the Ch1 baseline transition ledger
- never edit a global current-release pointer; never wait on other scopes; never wait on change closure
- multi-target partial acceptance is legal

### A10 · Recovery validation and post-recovery judgement
控制模式：guardrail + engineering-decision

- confirm the target actually entered the expected safe state — old artifact truly running, data readable, critical flows restored, migration / traffic safe
- recovery command success never counts; execution detail stays with SP-18

## 硬门禁（不可跳过）

- **G-SP17-01**：validation-set-environment-specific-and-fully-disposed-before-acceptance
- **G-SP17-02**：no-ch6-rerun-as-target-validation; deployment-success-never-validation-pass
- **G-SP17-03**：fail-only-on-valid-evidence; gaps-are-not-ready
- **G-SP17-04**：unmatured-obligation-stays-not-ready; smoke-deploy-health-never-trigger- completion-alone
- **G-SP17-05**：no-global-fixed-soak-time-as-maturity-semantics
- **G-SP17-06**：every-verdict-and-completion-carries-explicit-target-scope
- **G-SP17-07**：accepted-current-release-migrates-only-via-ledger-after-completion
- **G-SP17-08**：completion-not-closure; runtime-facts-never-delayed-for-closure
- **G-SP17-09**：high-risk-never-proceeds-on-looks-fine-under-evidence-gap
- **G-SP17-10**：recovery-validation-confirms-actual-safe-state
- **G-SP17-11**：na-maturity-waiver-exception-carry-rationale-and-stay-rechallengeable

## 通过出口（什么算完成）

`passExit = target-validation-truthfully-assessed-and-completion-honestly-decided`

- validation set derived, environment-specific, no ungrounded N-A
- every obligation has PASS (valid evidence) / FAIL (valid evidence) / NOT_READY (gap record)
- maturity conditions verified; unmatured obligations stay NOT_READY
- assessment formed per target scope, no extrapolation
- completion conditions checked item by item; completion record carries scope
- accepted current release migrated via ledger (or honestly unchanged)
- gaps / findings disposed and routed; candidate-defect evidence returned to the SP-15 / SP-13 chain

**完成不意味着**：candidate-reverified, other-scopes-complete, feature-exposed, change-closed, current-design-updated, incident-resolved

## 回退路径（发现问题去哪）

- target validation FAILED on valid evidence → finding classification via SP-15 A11 — candidate defect -> SP-13 / SP-06 chain; environment / dependency defect -> platform domain
- target validation NOT_READY → add evidence / fix observability / await maturity / controlled exception / block; never relabel as PASS or FAIL
- maturity durably unreachable → re-review condition design (risk change) or escalate; silently deleting the condition forbidden
- completion conditions unmet → hold and expose the gap; rollout side returns to SP-15 A8 (pause / reverse direction)
- recovery validation not reached → stay NOT_READY -> SP-18 (pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕, group-5; until then P4 Ch7 §89-102 body with SP-15 keeping execution records) further recovery / incident; never rewrite the accepted current release to fake recovery

## 证据义务

- 自然证据：['observability systems, verification jobs, platform records', 'SP-15 slice-level observation records']
- 额外证据（仅当）：['required-target-validation-set-with-source-pointers', 'maturity-condition-declarations-and-facts', 'not-ready-gap-dispositions', 'completion-records', 'ledger-transition-records', 'recovery-validation-conclusions']
- 证据规则：the carrier folds into existing systems; semantic records never waived
- Current 更新：writesCurrent = accepted-current-release-ledger-only
  The procedure's only current write is the per-target-scope accepted current release ledger transition after target release completion — a Ch7-domain target environment fact it registers itself. Project-level currents (design / structure / calibration / change closure) all go through SP-19; this procedure's validation conclusions and runtime facts are SP-19 calibration's actual evidence sources.


## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data
- JG-05 新增或升级 Dependency / Toolchain / Config
- JG-06 构建并发布一个版本
- JG-07 部署后验证、扩大暴露或恢复
- JG-08 处理线上 Incident / Emergency

## 理论回溯

- **part1**：GI-03, GI-05, GI-13, ch1-baseline-transition-ledger-decision
- **part2**：deploy-not-release-not-launch, testing-verification-what-boundary
- **part3**：runtime-where-as-validation-subject
- **part4**：ch5-unreliable-feedback-gap-semantics-88-94, ch6-evidence-semantics-38-55, ch6-coverage-gap-not-ready-66-75, ch7-deployment-result-not-validation-37, ch7-rollout-observation-attribution-46-59, ch7-runtime-state-observation-record-60-65, ch7-target-validation-set-results-maturity-completion-66-85, ch7-recovery-validation-99-101, ch7-evidence-gap-high-risk-110, ch7-minimum-requirements-139, ch7-maturity-completion-141, ch7-ch6-interface-143, ch8-emergency-144, ch9-interface-145

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
