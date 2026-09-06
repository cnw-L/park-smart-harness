---
name: sp-02-project-bootstrap-initialization-procedure
description: 'SP 规程 SP-02 Project Bootstrap / Initialization Procedure｜Project Bootstrap（软件项目开发工程规范指南·第五篇）：Establish / re-validate Project Engineering Foundation Readiness at the R0 / R1 / R2 / R3 Checkpoints. Not a project state machine (不是项目状态机): R0-R3 express Readiness only, never Project Lifecycle State, and never replace Part IV Change / Candidate / Release / Closure. 适用触发：greenfield project creation；prototype to formal governance；existing project foundation gap assessment；first change reaching r1 r2 r3 checkpoint；foundation context materially changed。 边界：Not a project state machine; may be invoked at R0 / R1 / R2 / R3 independently.'
metadata:
  spec.part5.sp-id: SP-02
  spec.part5.name: Project Bootstrap / Initialization Procedure
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP02-ProjectBootstrapInitializationProcedure-正式操作规程.md
---

# SP-02 Project Bootstrap / Initialization Procedure｜Project Bootstrap

> 《软件项目开发工程规范指南》第五篇执行规程 SP-02 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Establish / re-validate Project Engineering Foundation Readiness at the R0 / R1 / R2 / R3 Checkpoints. Not a project state machine (不是项目状态机): R0-R3 express Readiness only, never Project Lifecycle State, and never replace Part IV Change / Candidate / Release / Closure. Callable separately at each checkpoint.


## 边界（本规程不做的事）

Not a project state machine; may be invoked at R0 / R1 / R2 / R3 independently. Readiness only: R0-R3 do not represent Project Lifecycle State and do not substitute for Part IV Change, Candidate, Release or Closure (MD header + §18).


## 触发

- greenfield project creation
- prototype to formal governance
- existing project foundation gap assessment
- first change reaching r1 r2 r3 checkpoint
- foundation context materially changed

## 操作步骤

### A1 · R0 — establish governance bootstrap facts
控制模式：engineering-decision

- Must establish: Stable Project Identity; Project / Technical Owner; Engineering Scope; Repository / Source location; Technical Entry; Truthful Bootstrap Current / Reality; Foundation Applicability Profile; Requirement / Trigger Authority navigation

### A2 · R0 — clean-environment proof
控制模式：automation

- At minimum: fresh clone -> open technical entry -> locate setup/run/test/build commands -> resolve current/change navigation
- greenfield may verify only the Bootstrap Technical Shell (§4.2, also E1)

### A3 · Record Engineering Governance Cutover
控制模式：engineering-decision

- After R0 PASS record: effective_at; decision / owner; bootstrap baseline refs
- after cutover, Material Current Change goes through Part IV Engineering Change
- bootstrap privilege may only create initial controlled facts; it cannot be indefinitely deferred

### A4 · R1 — determine applicability
控制模式：engineering-decision

- applicability decided by: Accepted Requirement; Impact; Accepted Design / Design Direction; Delivery Shape; Risk

### A5 · R1 — check minimum concerns
控制模式：engineering-decision

- repeatable local environment; controlled dependency resolution; configuration rule; secret rule; test / verify entry; relevant source / boundary navigation; security/toolchain access; migration mechanism if persistent schema is introduced; contract source if public contract is introduced

### A6 · R1 — readiness proof
控制模式：automation

- execute applicable commands in a clean/reproducible environment, e.g. dependency sync; unit test; integration harness startup; migration empty-db smoke (if applicable); application technical shell startup (if applicable)
- NOT_READY must not pass merely because files exist or docs say ready

### A7 · R2 — verify shared integration foundation
控制模式：engineering-decision

- must have: Shared Source Authority; Controlled Integration Path; Required Fast Verification; CI / equivalent automation; Repeatable Build; Visible Check Result; Broken Baseline handling; Execution Asset Version Binding

### A8 · R2 — staged control activation
控制模式：automation-assisted

- recommended order: create verify/CI -> run successfully -> stabilize check identity -> configure Hard Gate -> intentionally prove a failing change is blocked -> record control evidence
- the tool need not be GitHub

### A9 · R3 — verify delivery foundation
控制模式：engineering-decision

- must have: Output / Artifact Identity; Target / Channel / Environment Identity; Config / Secret Injection; Delivery / Distribution Entry; Migration Execution (if applicable); Observation / Diagnostics; Target Validation Entry; Recovery / Withdrawal Direction; Delivery Authority
- online service face (§8.2), typically: version; logs; health/readiness as applicable; critical error visibility; metrics/traces by risk
- CLI / library face (§8.3) may be: package/binary identity; release channel; checksum / artifact; install/run smoke; diagnostic exit/error; withdraw / replace direction — server health not required

### A10 · Dispose foundation applicability per concern
控制模式：engineering-decision

- **判定词汇**：
  - Applicable
  - Deferred
  - N/A
- Deferred must carry an Activation Trigger and an Owner
- e.g. Migration: Deferred / Trigger: first persistent schema introduced

### A11 · Bind execution asset versions
控制模式：automation-assisted

- version-identifiable assets: Starter; Reusable Workflow; Action; Build Image; Policy; Migration Template; Deployment Adapter
- allowed policies: immutable SHA; versioned tag; controlled stable channel — but consumer / compatibility / upgrade / rollback must be explicit

### A12 · Verify execution command contract
控制模式：automation

- each profile provides at least the logical capabilities: setup/sync; run; test; verify; build/package; migrate; smoke/validate — exact platform wording need not match
- developer path and CI path must be semantically aligned

### A13 · Enforce secret / target rules
控制模式：automation + guardrail

- template MAY contain: .env.example; secret names; schema / sample non-secret values
- template MUST NOT contain: production secrets; private keys; real tokens
- profile default name is not the real project target authority

### A14 · Trigger readiness revalidation on material changes
控制模式：automation-assisted

- revalidate on: dependency tool changed; CI workflow replaced; build platform changed; repository control removed; runtime packaging changed; deployment mechanism changed; secret model changed; new DB introduced; public contract introduced
- readiness is not a permanent certificate

### A15 · Tailor to small team profile
控制模式：engineering-decision

- minimum may be: README; repository; simple scripts; version control; automated tests; simple CI; package/build
- {'not required': 'IDP; Backstage; Kubernetes; CAB; multi-reviewer'}

## 硬门禁（不可跳过）

- **G-SP02-01**：r0-must-establish-facts-present
- **G-SP02-02**：r0-clean-environment-proof-executed
- **G-SP02-03**：r0-pass-means-normal-change-establishable-without-inventing-current
- **G-SP02-04**：governance-cutover-recorded-and-bootstrap-privilege-bounded
- **G-SP02-05**：r1-pass-requires-clean-environment-proof
- **G-SP02-06**：r2-shared-baseline-entry-requires-integration-control-must-haves
- **G-SP02-07**：r3-pass-does-not-mean-release-deployment-validation-success
- **G-SP02-08**：deferred-concern-requires-activation-trigger-and-owner
- **G-SP02-09**：execution-assets-version-identifiable-with-consumer-compat-upgrade-rollback
- **G-SP02-10**：developer-and-ci-paths-semantically-aligned
- **G-SP02-11**：no-production-secrets-private-keys-real-tokens-in-template
- **G-SP02-12**：readiness-revalidation-on-material-foundation-changes

提示级：
- G-SP02-13：r2-staged-control-activation-is-recommended-not-mandatory

## 通过出口（什么算完成）

`passExit = For the invoked checkpoint, every applicable concern has passed its readiness proof with evidence on record; inapplicable concerns are dispositioned N/A; deferred concerns carry activation trigger + owner. R0 -> Governance Bootstrap Ready; R1 -> Development Foundation Ready; R2 -> Shared Integration Foundation Ready; R3 -> Delivery Foundation Ready.
`

- R0
- R1
- R2
- R3

**完成不意味着**：project-lifecycle-state, release-authorized, deployment-succeeded, target-validation-passed, candidate-accepted, change-closed

## 回退路径（发现问题去哪）

- R0 NOT_READY → fix bootstrap truth / owner / navigation
- R1 NOT_READY → establish missing dev/test/migration/config foundation
- R2 NOT_READY → repair CI / build / integration control
- R3 NOT_READY → establish artifact/target/deploy/observe/recovery foundation
- material design changes applicability → Ch3 / Ch4 reconcile

## 证据义务

- 自然证据：['clean-environment proof run records (R0/R1/R3 readiness evidence)', 'governance cutover record (effective_at / decision-owner / bootstrap baseline refs)', 'foundation applicability profile per concern (Applicable / Deferred / N/A)', 'deferred obligation records (activation trigger + owner)', 'R2 control evidence (incl. failing-change-blocked proof when staged activation is followed)', 'revalidation records after §14 material changes']
- 额外证据（仅当）：['applicability-judgment-rationale', 'deferred-decision', 'r2-lightweight-classification']
- 证据规则：readiness evidence emerges naturally from the executed proof runs
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-01 新项目从 0 到第一条正常 Change

## 理论回溯

- **part2**：project-engineering
- **part3**：scope, source, runtime, current
- **part4**：ch1, ch2

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
