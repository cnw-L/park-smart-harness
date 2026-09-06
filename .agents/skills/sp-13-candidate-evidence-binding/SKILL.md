---
name: sp-13-candidate-evidence-binding
description: SP 规程 SP-13 Candidate / Evidence Binding｜候选与证据绑定（软件项目开发工程规范指南·第五篇）：Organize implementation output into an unambiguous, immutable-for-evidence Candidate Baseline; define a versioned Required Verification Set; bind every piece of evidence to an explicit subject / context / definition revision; judge reuse via candidate-delta intersect evidence-dependency-set; 适用触发：candidate scope ready；evidence arrives；candidate material change；verification basis change；revalidation trigger。 边界：Never produces release baselines, release decisions, delivery authorization (SP-15), target validation conclusions (SP-17), or any current …
metadata:
  spec.part5.sp-id: SP-13
  spec.part5.name: Candidate / Evidence Binding
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP13-CandidateEvidenceBinding-正式操作规程.md
---

# SP-13 Candidate / Evidence Binding｜候选与证据绑定

> 《软件项目开发工程规范指南》第五篇执行规程 SP-13 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Organize implementation output into an unambiguous, immutable-for-evidence Candidate Baseline; define a versioned Required Verification Set; bind every piece of evidence to an explicit subject / context / definition revision; judge reuse via candidate-delta intersect evidence-dependency-set; maintain a coverage map that honestly separates FAIL / evidence gap / exception; and produce a scope-bound candidate acceptance decision. Candidate is not the change, not the release baseline, not the implementation revision set; coverage complete is not verification satisfied; accept is not release authorization; reject never closes the change.


## 边界（本规程不做的事）

Never produces release baselines, release decisions, delivery authorization (SP-15), target validation conclusions (SP-17), or any current update (SP-19). Pass is not valid evidence; skipped / quarantined / platform-success is never automatically required-evidence pass; a required check is never silently deleted after a test fail.


## 触发

- candidate scope ready
- evidence arrives
- candidate material change
- verification basis change
- revalidation trigger
- assessment and decision
- sp14 build facts arrive

## 操作步骤

### A1 · Confirm candidate formation entry
控制模式：guardrail

- ch5 handoff complete per the formal interface; partial candidates legal but never masquerade as the whole change
- re-challenge upstream gate-zeroing dispositions (B1)

### A2 · Define candidate scope
控制模式：engineering-decision


### A3 · Compose candidate manifest and member binding
控制模式：automation-assisted + guardrail

- members bound to unambiguous revision / digest / version or a time anchor that re-resolves the real content later
- mutable aliases (latest / current / bare branch) never carry identity alone
- dynamic config / feature state bound at effective state; no secret values
- manifest digest risk-conditional (P4 Ch6 §16 — mandated at high supply-chain / audit risk, not for small teams); candidate id / revision issued
- artifact identity / provenance come from SP-14 outputs; this procedure binds and verifies resolvability

### A4 · Establish immutable-for-evidence and coherence
控制模式：guardrail

- from the first material evidence binding, content freezes; material change forms a new candidate revision; accepted manifests stay historically stable
- member coherence verified (e.g. code needing a new field is matched by an in-manifest migration)

### A5 · Define the required verification set
控制模式：engineering-decision

- derived from requirement / impact / obligation / design / policy
- obligation is not a test case and not a fixed test-type checklist

### A6 · Version the verification basis
控制模式：guardrail + authority

- the set is versioned before verification starts — the standard for judging the candidate is known in advance
- material basis change records reason + authority / decision + revision
- legitimate evolution path exists (re-impact -> obligation updated -> set expanded); silently weakening after a FAIL is a red-line violation

### A7 · Bind evidence
控制模式：automation

- subject is explicit to a candidate member; not limited to artifact digests
- context records the actually resolved environment / config / workload / dependency / tool-rule revision or fingerprint; mutable context aliases never substitute
- evidence types span test / analysis / review / inspection / observation
- non-representative contexts are annotated with their representativeness limits

### A8 · Judge validity, applicability and reuse
控制模式：engineering-decision

- validity (subject / context / definition match + trustworthy execution) is judged apart from result; applicability to the current candidate revision is judged apart from validity
- reuse = candidate-delta intersect evidence-dependency-set: material effect on objective / assumption -> rerun / re-evaluate; none -> reuse with basis
- neither blanket rerun on any change nor blanket inherit on unchanged artifact
- performance evidence defaults context-sensitive; stable unit evidence reusable
- revalidation triggers route through the same judgement

### A9 · Maintain coverage map; separate fail / gap / not-ready
控制模式：guardrail

- coverage map spans every applicable obligation; foldable into CI / PR
- valid FAIL -> FAILED; environment / tool failure, skipped, quarantined, wrong subject / context, unresolved definition -> NOT_READY / evidence gap
- tool UI green (incl. skipped-but-success) never counts as evidence coverage

### A10 · Dispose verification exceptions
控制模式：authority + engineering-decision

- never rewrites the underlying evidence result
- exception applicability judged per obligation; non-waivable obligations are never waived by this procedure
- exceptions never auto-inherit into a new candidate revision

### A11 · Form the candidate verification assessment
控制模式：guardrail

- dispositions preserve underlying evidence results
- satisfied with exceptions exposes them separately — never a fake clean pass
- FAILED and NOT_READY stay separate; their return paths differ
- coverage complete (every obligation disposed) stated apart from verification satisfied; a FAIL can be coverage complete

### A12 · Make the candidate acceptance decision
控制模式：decision-point

- reuses Ch1 decision point / record / gate / authority / exception machinery
- accept-with-exception exposes known exceptions to Ch7 / release decision
- all known material findings disposed before deciding
- emit the verification progress fact (candidate id / revision + acceptance scope + basis revision + evidence set ref + observed / decided at)
- reject routes per finding and leaves the change open / active

## 硬门禁（不可跳过）

- **G-SP13-01**：explicit-candidate-scope-and-unambiguous-manifest
- **G-SP13-02**：no-mutable-alias-as-candidate-or-evidence-identity
- **G-SP13-03**：no-in-place-mutation-after-evidence-binding
- **G-SP13-04**：revision-set-never-masquerades-as-candidate-baseline
- **G-SP13-05**：versioned-required-set-before-acceptance; no-silent-obligation-deletion
- **G-SP13-06**：no-pass-acceptance-on-mismatched-subject-context-definition
- **G-SP13-07**：no-blanket-rerun-no-blanket-inherit
- **G-SP13-08**：skipped-quarantined-platform-success-never-auto-pass
- **G-SP13-09**：exception-never-rewrites-result; non-waivable-never-waived-here
- **G-SP13-10**：satisfied-failed-not-ready-distinct; gap-is-not-fail
- **G-SP13-11**：known-material-findings-disposed-before-decision
- **G-SP13-12**：accept-scope-bound; reject-never-closes-change

## 通过出口（什么算完成）

`passExit = acceptance-decision-truthfully-made`

- manifest fully bound, coherent, immutable-for-evidence
- required verification set versioned; coverage map spans applicable obligations
- every obligation has an explicit disposition preserving underlying results
- assessment semantically correct (exceptions exposed; failed / not-ready separate)
- known material findings disposed; exceptions complete and visible to Ch7
- decision bound to revision / scope / basis / evidence set; progress fact emitted

**完成不意味着**：release-authorized, deployed, production-validated, change-closed, any-current-updated

## 回退路径（发现问题去哪）

- assessment FAILED → route by finding — implementation defect -> SP-06; design -> SP-05; new impact -> SP-04; requirement gap -> requirement authority
- assessment NOT_READY → add evidence / fix verification infrastructure / wait / block; environment not ready never proves the candidate wrong
- REJECT → change stays open / active; new candidate reuses evidence only after applicability judgement
- basis needs weakening → explicit verification basis change; silent weakening is a red line

## 证据义务

- 自然证据：['CI required checks + PR / test reports (coverage / evidence carriers)', 'manifest files, decision records']
- 额外证据（仅当）：['manifest-digest-and-context-snapshots', 'basis-change-records', 'reuse-applicability-rationale', 'exception-records', 'known-finding-dispositions', 'acceptance-decision-record']
- 证据规则：small teams need no dedicated platform; semantic records never waived
- Current 更新：writesCurrent = False
  Candidate acceptance is a scope-bound fact that the candidate revision may enter the next delivery / release preparation decision — it updates no current. Accepted candidates become target-environment facts via SP-15 / SP-17; current commits go through SP-19. The evidence set and progress fact are candidate Actual Evidence Refs for SP-19 calibration.


## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data
- JG-05 新增或升级 Dependency / Toolchain / Config
- JG-06 构建并发布一个版本

## 理论回溯

- **part1**：GI-03, GI-05, GI-13, ch1-decision-point-gate-authority-exception
- **part2**：testing-verification-what, build-release-what-boundary, release-candidate-boundary
- **part3**：build-runtime-refs-as-evidence-context
- **part4**：ch6-full, ch6-minimum-requirements-137, ch6-baseline-requirements-139-140, ch5-explicit-artifact-selection-72-304, ch6-ch5-interface-141, ch6-ch7-interface-142, ch7-ch6-interface-143, ch8-emergency

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
