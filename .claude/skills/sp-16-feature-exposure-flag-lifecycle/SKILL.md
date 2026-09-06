---
name: sp-16-feature-exposure-flag-lifecycle
description: 'SP 规程 SP-16 Feature Exposure / Flag Lifecycle｜暴露控制/Flag 生命周期（软件项目开发工程规范指南·第五篇）：Decouple capability exposure (launch) from binary deployment as two controlled facts: govern the exposure asset and its lifecycle (flag / rollout config owner / purpose / default / launch plan / cleanup condition), maintain exposure state expressed at truthful granularity, and guarantee exposure … 适用触发：launch new capability gated；exposure change material；flag lifecycle governance；flag debt。'
metadata:
  spec.part5.sp-id: SP-16
  spec.part5.name: Feature Exposure / Flag Lifecycle
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP16-FeatureExposureFlag-正式操作规程.md
---

# SP-16 Feature Exposure / Flag Lifecycle｜暴露控制/Flag 生命周期

> 《软件项目开发工程规范指南》第五篇执行规程 SP-16 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Decouple capability exposure (launch) from binary deployment as two controlled facts: govern the exposure asset and its lifecycle (flag / rollout config owner / purpose / default / launch plan / cleanup condition), maintain exposure state expressed at truthful granularity, and guarantee exposure changes are delivered as target-changing actions. Code 100% deployed with the flag off is not a launch; a feature flag is not a free eliminator of release risk, and a temporary flag without the five-element registration is future config drift and old code path.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- launch new capability gated
- exposure change material
- flag lifecycle governance
- flag debt

## 操作步骤

### A1 · Confirm entry and exposure object
控制模式：automation-assisted

- confirm exposure-face change (from delivery facts, SP-15 input), which feature/capability is exposed, whether flag-gated, exposure dimension (instance / traffic / region / tenant / cohort / feature exposure, Ch7 §48)
- B1 re-challenge: launch-directly-without-flag / not-material / internal-tool-no-exposure classifications without resolvable rationale return to SP-04 / SP-05

### A2 · Exposure strategy and launch plan design
控制模式：engineering-decision

- strategy by risk (Ch11 §36: all-at-once / canary / tenant-by-tenant / flag-progressive; progressive not mandatory for low-impact internals)
- launch plan = progressive stages (e.g. 0%->5%->20%->100%) + per-stage stop conditions (error / latency / critical business failure / data inconsistency, §39 — thresholds from service requirement / baseline, not uniformly prescribed) + per-stage observation signals (Ch7 §51; high-risk exposure evidence attributable to release revision and rollout slice, §53)
- launch plan is the main body of the SP-15 execution handoff

### A3 · Flag asset registration (five elements)
控制模式：automation

- every temporary flag registered: owner / purpose / default / launch plan / cleanup condition (Ch11 §41; EA-14 state + owner + cleanup)
- default-value policy explicit (esp. fail-safe OFF default); a flag without the five elements never enters exposure execution

### A4 · Exposure state fact and observation face definition
控制模式：automation-assisted + engineering-decision

- define expression granularity and observation face: per-target / per-tenant / per-cohort flag state, current percentage, artifact version distribution, stop/pause state (P2 Ch11 §70)
- exposure state is part of environment current runtime state; fact commits orchestrated by SP-15 at execution time (Ch7 §60-62, mixed state recorded truthfully); this procedure guarantees the semantic granularity is never flattened (GI-05)
- no-server forms use distribution record / channel / cohort / installation / adoption / version exposure for the same semantics (Ch7 §88, SP-15 §11)

### A5 · Exposure change execution handoff
控制模式：engineering-decision

- flag flips, exposure expansion, emergency disable all hand to SP-15 as target-changing actions (§86-87: authority token check, observation, rollout slice control; §114: feature disable and traffic revert equally constrained)
- this procedure provides launch plan, exposure semantics, recovery intent; post-exposure behavioral validation concern = SP-17
- "exposure change not material, no control needed" is a gate-zeroing judgment and carries rationale (B1)

### A6 · Flag cleanup and long-term disposition
控制模式：engineering-decision

- cleanup condition triggered -> removal plan: flag removal + old code path deletion + test combination shrink, as a normal controlled change via SP-03 and downstream procedures
- long-term disposition explicit: genuinely long-lived business switch -> formal configuration contract (§41; definition/publication SP-09, cross-boundary evolution SP-07); kill-switch / safety flags judged permanent assets (owner + periodic drill) — explicitly registered, not counted as debt
- "temporary flag one more release" without rationale is treated as debt

### A7 · Flag debt governance
控制模式：engineering-decision

- inspect flag registry (maintenance planning input, Ch12 §7): unowned / no-cleanup / permanently-on temporary flags / old code path piles
- register flag debt: risk + owner + cleanup condition (against landfilling, Ch12 §37 analogy); design-grade removal paths (old code path load-bearing) hand to SP-05

### A8 · Client / no-server form adaptation
控制模式：engineering-decision

- client / device exposure = version exposure via distribution channel / cohort (staged rollout channels), launch semantics via installation / adoption observation (Ch7 §88)
- never fabricate server-side environment deployment records; distribution execution = SP-15, this procedure owns exposure semantics and adoption facts

## 硬门禁（不可跳过）

- **G-SP16-01**：100-percent-deployed-with-flag-off-is-not-launched
- **G-SP16-02**：material-exposure-change-goes-through-sp15-target-changing-control
- **G-SP16-03**：temporary-flag-requires-five-element-registration
- **G-SP16-04**：flag-existence-never-exempts-verification-or-exposure-control
- **G-SP16-05**：exposure-state-recorded-at-truthful-granularity
- **G-SP16-06**：flag-permanentization-requires-explicit-disposition-and-handoff
- **G-SP16-07**：never-bypass-sp15-to-execute-exposure-changes
- **G-SP16-08**：no-sp16-sp05-sp09-mutual-coverage
- **G-SP16-09**：gate-zeroing-classification-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = Exposure / launch plan established (bound to feature and delivery facts): exposure strategy tailored by risk (B1 rationale holds) + when applicable: flag five-element registration complete, progressive stages and stop conditions explicit + exposure state fact granularity and observation face defined + execution handoff to SP-15 (launch plan + exposure semantics + recovery intent) + when applicable: cleanup / long-term / debt dispositions in writing -> handoff to SP-15 (exposure execution) / SP-17 (post-exposure validation)
`



**完成不意味着**：feature-fully-exposed, target-validation-passed, exposure-incident-recovered, flag-cleaned-up, current-updated

## 回退路径（发现问题去哪）

- exposure change judged to need re-authorization by SP-15 (basis invalid) → update launch plan and re-handoff (Ch7 §29-30 revalidation)
- post-exposure validation FAIL / NOT_READY → SP-17 path; recovery actions needed -> SP-18
- fix requiring new software content during exposure → SP-18 recovery (forward fix producing new software content returns to normal procedures); kill-switch-style immediate disable execution still goes through SP-15
- cleanup condition unsatisfiable (old code path still load-bearing) → register flag debt + hand to SP-05 for removal path design; never silently shelve
- long-term disposition triggers cross-boundary commitment evolution → hand to SP-07 (with fact input)
- material design problem (exposure strategy unsound) → SP-05

## 证据义务

- 自然证据：['exposure / launch plan (stages and stop conditions)', 'flag registry entries (five elements)', 'exposure state observation face definitions and collected facts (produced under SP-15 orchestration)', 'exposure execution handoff records (launch plan version)', 'cleanup / long-term / debt disposition records']
- 额外证据（仅当）：['gate-zeroing-classification-rationale', 'long-term-disposition-rationale', 'permanent-kill-switch-registration']
- 证据规则：all other evidence emerges naturally from the work
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力（按需）
- JG-07 部署后验证、扩大暴露或恢复

## 理论回溯

- **part1**：GI-03, GI-05, GI-13
- **part2**：p2-ch11-2.5-launch-enable-four-way-separation, p2-ch11-3-why-deploy-release-distinct, p2-ch11-36-42-rollout-canary-flag-not-free, p2-ch11-68-70-complex-rollout-status-partial-observability, p2-ch12-14-additive-maintenance-context
- **part3**：p3-ch3-31-flag-runtime-behavior-determinant, p3-ch3-42-44-mixed-target-transition-runtime-structure, p3-ch3-71.7-defers-to-p2-build-release-baseline, p3-ch6-49-flag-platform-external-capability, p3-drift-61-flag-as-observation-mismatch-explanation
- **part4**：ch7-46-59-rollout-slice-attribution-proceed-pause, ch7-86-87-launch-exposure-separate, ch7-88-client-equivalent-semantics, ch7-114-116-authority-token-constrains-disable-revert, ch7-137-feature-flag-counterexample, ch7-139-minimum-requirements-exposure-items

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
