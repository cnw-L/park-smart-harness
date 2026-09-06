---
name: sp-14-build-artifact-provenance
description: 'SP 规程 SP-14 Build / Artifact / Provenance｜构建/工件/出处（软件项目开发工程规范指南·第五篇）：Produce and vouch for canonical build artifact identity: pin the build baseline (source + dependency + build definition + build environment), run reproducible canonical builds, establish digest-level artifact identity, emit provenance at a risk-appropriate depth, execute same-artifact promotion, … 适用触发：candidate needs artifact；release formation；materialization；build failure or nonreproducible；provenance depth required。 边界：Never decides candidate membership or evidence applicability (SP-13), release formation / decision / authorization or deployment (SP-15), …'
metadata:
  spec.part5.sp-id: SP-14
  spec.part5.name: Build / Artifact / Provenance
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP14-BuildArtifactProvenance-正式操作规程.md
---

# SP-14 Build / Artifact / Provenance｜构建/工件/出处

> 《软件项目开发工程规范指南》第五篇执行规程 SP-14 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Produce and vouch for canonical build artifact identity: pin the build baseline (source + dependency + build definition + build environment), run reproducible canonical builds, establish digest-level artifact identity, emit provenance at a risk-appropriate depth, execute same-artifact promotion, and evaluate release materialization deltas explicitly. SP-14 produces identity and provenance; SP-13 binds artifacts as candidate members and judges evidence; SP-15 references identities in release formation. "Just packaging" is never a risk-free assumption.


## 边界（本规程不做的事）

Never decides candidate membership or evidence applicability (SP-13), release formation / decision / authorization or deployment (SP-15), feedback builds (SP-11), or any current update (SP-19). Provenance proves artifact-from-inputs/ builder only; it never substitutes requirement / performance / migration / user verification.


## 触发

- candidate needs artifact
- release formation
- materialization
- build failure or nonreproducible
- provenance depth required
- no artifact change

## 操作步骤

### A1 · Judge build level and purpose
控制模式：guardrail

- level claim written into the build record
- upstream promotion claims checked against identity / input traceability / context stability (Ch5 §72 three conditions + B1); unmet -> rebuild at the candidate / release level

### A2 · Pin the build baseline
控制模式：automation + guardrail


### A3 · Execute the canonical build
控制模式：automation

- record the build run identity (CI run / builder)
- same baseline re-run must yield the same digest or an explained, enumerated difference list
- unexplained non-reproducibility is a build mechanism defect — classify and fix, never converge by repeated runs
- build failures classified via the SP-11 nine-class vocabulary and routed

### A4 · Establish artifact identity
控制模式：automation

- digest per artifact; multi-platform / multi-arch enumerated, never collapsed under one label over differing content
- identity freezes once referenced by SP-13 / SP-15; content change produces a new identity and explicit re-binding

### A5 · Emit provenance
控制模式：automation + policy


### A6 · Execute same-artifact promotion
控制模式：guardrail + engineering-decision

- every promotion step references the same artifact identity
- {'promotion record': 'identity, source candidate revision, promotion target'}
- "rebuild a similar one" attempts rejected: either reference the verified identity or route the new artifact through SP-13 as a new candidate member

### A7 · Evaluate the release materialization delta
控制模式：engineering-decision

- content identity unchanged (pure signature envelope) -> record the inheritance basis, hand to SP-15
- new identity -> materialization delta record to SP-13 for evidence applicability re-evaluation (new candidate / supplementary verification as needed)

### A8 · Hand off build facts
控制模式：automation + guardrail

- **移交**：
  - → SP-13：artifact identity + build baseline + provenance; delta records
  - → SP-15：referenceable identity list + promotion records + delta disposition
  - → SP-11：build-level feedback needs; build failure classifications close in-layer

## 硬门禁（不可跳过）

- **G-SP14-01**：feedback-build-output-never-masquerades-as-candidate-or-release-grade
- **G-SP14-02**：candidate-release-builds-pin-re-resolvable-baselines; no-mutable-alias-inputs
- **G-SP14-03**：digest-level-identity; published-identities-never-repointed
- **G-SP14-04**：no-rebuild-a-similar-artifact-and-claim-it-verified
- **G-SP14-05**：new-materialized-identity-requires-delta-record-and-sp13-reevaluation
- **G-SP14-06**：provenance-depth-matches-risk; slsa-never-substitutes-non-build-verification
- **G-SP14-07**：no-converging-unexplained-nonreproducibility-by-repetition
- **G-SP14-08**：same-artifact-claims-carry-digest-evidence-and-stay-rechallengeable

## 通过出口（什么算完成）

`passExit = artifact-identity-truthfully-established`

- build level consistent with a pinned, re-resolvable baseline
- canonical build succeeded; reproducibility fact recorded
- artifact identity list complete per platform; no silent repointing
- provenance depth matches risk; coverage boundary annotated
- promotion chain traceable (candidate identity -> release reference)
- materialization deltas evaluated, handed off, and SP-13 conclusions recorded

**完成不意味着**：candidate-accepted, evidence-applies-to-new-identity, release-formed-or-authorized, any-current-updated

## 回退路径（发现问题去哪）

- build failure → SP-11 nine-class routing — source -> SP-06; dependency -> SP-09 domain; toolchain / infra -> fix the mechanism; external -> isolate; unknown -> retain
- unexplained non-reproducibility → build mechanism defect; fix build definition / toolchain (EA-10 governance)
- materialization produced new identity → SP-13 re-evaluation; new candidate revision + supplementary verification as needed
- promotion chain broken (identity mismatch) → halt release formation; return to SP-13 or rebuild

## 证据义务

- 自然证据：['CI / build system records, digests, lockfiles, artifact registry entries']
- 额外证据（仅当）：['build-baseline-record', 'reproducibility-fact', 'promotion-record', 'materialization-delta-record', 'provenance-coverage-boundary']
- 证据规则：identity claims rest on digest comparison, not narration
- Current 更新：writesCurrent = False
  Build / artifact / provenance work produces facts; it updates no current. Entry into candidate, release and target environments is decided by SP-13 / SP-15 / SP-17 respectively; current commits go through SP-19.


## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力
- JG-05 新增或升级 Dependency / Toolchain / Config
- JG-06 构建并发布一个版本

## 理论回溯

- **part1**：GI-05, GI-13
- **part2**：build-what, release-what-boundary
- **part3**：source-build-artifact-where
- **part4**：ch5-three-build-levels-68-72, ch5-requirements-277-296-304, ch6-108-109-provenance-depth, ch6-139-140-baseline-requirements, ch7-release-formation-8-17, ch7-minimum-requirements-139-shoulds, ch8-emergency

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
