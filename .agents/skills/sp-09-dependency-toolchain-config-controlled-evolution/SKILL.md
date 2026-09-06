---
name: sp-09-dependency-toolchain-config-controlled-evolution
description: 'SP 规程 SP-09 Dependency / Toolchain / Config Controlled Evolution｜依赖/工具链/配置受控变更（软件项目开发工程规范指南·第五篇）：Run the controlled professional evolution of a change touching dependencies / toolchain / configuration: establish dependency identity and resolution facts (why introduced / which version / who owns / transitive / risk), guarantee version determinism and build-input completeness, manage the code / … 适用触发：dependency add upgrade remove；toolchain build generator change；config secret surface change；dependency config debt governance。'
metadata:
  spec.part5.sp-id: SP-09
  spec.part5.name: Dependency / Toolchain / Config Controlled Evolution
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP09-DependencyToolchainConfig-正式操作规程.md
---

# SP-09 Dependency / Toolchain / Config Controlled Evolution｜依赖/工具链/配置受控变更

> 《软件项目开发工程规范指南》第五篇执行规程 SP-09 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Run the controlled professional evolution of a change touching dependencies / toolchain / configuration: establish dependency identity and resolution facts (why introduced / which version / who owns / transitive / risk), guarantee version determinism and build-input completeness, manage the code / config / secret separation with traceable injection, and treat important config changes as controlled changes. The same source baseline must determine the actually used dependency version — never re-resolve randomly per build; config is itself a controlled engineering fact; a secret is never ordinary source code.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- dependency add upgrade remove
- toolchain build generator change
- config secret surface change
- dependency config debt governance

## 操作步骤

### A1 · Confirm entry and touch surface
控制模式：automation-assisted

- enumerate touched surfaces: dependency (add / upgrade / remove / resolution mechanism) / toolchain (compiler / build tool / generator) / config-secret (items / injection / config-artifact relation)
- B1 re-challenge: upstream dev-only-no-risk / toolchain-need-not-be-pinned / not-a-release classifications without resolvable rationale return to SP-04

### A2 · Dependency add / upgrade / remove decision
控制模式：engineering-decision

- five questions registered (Ch9 §21) + benefit vs long-term cost (§23: security surface / upgrade cost / build cost / conflict)
- assess third-party trustworthiness / maintainability / known-risk face (§24); security disposition needs hand off to SP-10 — never executed here; identity / resolution facts stay here

### A3 · Version determinism and build input
控制模式：guardrail + engineering-decision

- establish determinism mechanism (Ch9 §22, Ch1 §7.2: lock / resolved version / manifest / repository / checksum by ecosystem; goal = same source baseline resolves deterministically)
- dependency / base image / compiler-toolchain (by risk) enter build baseline (Ch11 §6); formal build satisfies §86.2 [MUST][BASELINE] — build definition / dependency-base image / output-affecting build parameters determinable, never relying on untraceable local state
- "toolchain need not be pinned by risk" is a gate-zeroing judgment and carries rationale (B1)

### A4 · Toolchain / generator governance
控制模式：engineering-decision

- register toolchain versions and upgrade paths (by risk, Ch11 §6)
- generated code five elements (Ch9 §25): source artifact / generator+ version / generated output / commit-or-not (by build / tooling choice) / how to regenerate; output traceable to generator input and process; hand-edited generated files identified and corrected

### A5 · Config / secret separation and injection governance
控制模式：engineering-decision + guardrail

- land code / config / secret separation (Ch9 §19): source env branches / hard-coded values identified and migrated to controlled config
- config itself managed as controlled engineering fact (Ch11 §16: never an unmanaged manual input for the sake of artifact immutability)
- secret face (Ch9 §20, Ch11 §17, §26): never in source / artifact / logs / errors; secret reference / required secret schema / injection mechanism traceable; developers know local / CI / production acquisition and injection (Ch1 §7.3)
- secret found in version history -> hand to SP-10 for rotation and security disposition; this procedure registers the fact

### A6 · Config change as controlled change
控制模式：engineering-decision

- important config / flag change establishes §42 five elements: identity-revision / change reason / authorization / verification / target state
- "this config change is not a release" is a gate-zeroing judgment and carries rationale (B1); importance judged by runtime behavior impact (binary unchanged != unchanged)
- release orchestration hands off to SP-15 / SP-17; this procedure guarantees controlled elements complete
- further flag lifecycle governance hands to SP-16 pending-definition (group-5); until then covered by SP-15 §11.3 target-changing action

### A7 · Compatibility and cross-boundary judgment
控制模式：engineering-decision

- judge whether the dependency / config change touches cross-boundary commitments: config schema / externally exposed dependency surface already a contract -> compatibility evolution hands off to SP-07 (this procedure provides fact input); purely internal evolution stays here
- judgment carries rationale (B1)

### A8 · Review / verification handoff and debt registration
控制模式：engineering-decision

- review = SP-12 (dependency decision record as review material); behavior verification = SP-11 / SP-13; determinism may be verified via reproducible-build spot checks with SP-14 build / provenance face
- register dependency / config debt: stale dependencies / permanent pins / unowned dependencies / hidden environment divergence — risk + owner + cleanup condition, against permanentization

## 硬门禁（不可跳过）

- **G-SP09-01**：same-source-baseline-determines-dependency-version
- **G-SP09-02**：formal-build-determines-definition-dependency-parameters
- **G-SP09-03**：secret-never-hardcoded-committed-baked-logged
- **G-SP09-04**：env-divergence-never-hidden-in-source; config-secret-injection-traceable
- **G-SP09-05**：important-config-flag-change-is-controlled-change
- **G-SP09-06**：important-dependency-change-requires-five-questions
- **G-SP09-07**：generated-output-never-detached-from-source
- **G-SP09-08**：no-sp09-sp10-mutual-coverage
- **G-SP09-09**：gate-zeroing-classification-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = Dependency / Toolchain / Config Evolution Plan established (bound to source baseline): five-question record and version determinism mechanism per touched dependency + build input face complete (dependency / base image / toolchain by risk) + code-config-secret separation landed with traceable injection + when applicable: config change controlled elements complete, generator five elements explicit, cross-boundary judgment with rationale -> handoff to SP-06 (implementation) / SP-10 (security disposition) / SP-15 (config release orchestration)
`



**完成不意味着**：vulnerabilities-disposed, verification-passed, config-change-released, current-updated

## 回退路径（发现问题去哪）

- version determinism cannot be established (ecosystem / mechanism limits) → select an equivalent determinism mechanism or upgrade the toolchain; never give up with "the ecosystem is like this" (Ch1 §7.2 requires deterministic results, not specific tools)
- dependency risk unacceptable → alternative / small in-house tool / removal; security-face disputes hand to SP-10
- touches cross-boundary commitment → compatibility evolution hands to SP-07 (with fact input)
- secret already in version history → hand to SP-10 for rotation and security disposition; this procedure registers the fact, never deletes history to mask
- material design problem → SP-05
- config change release orchestration failed → SP-15 / SP-17 path

## 证据义务

- 自然证据：['dependency decision record (five questions + cost assessment)', 'lock / manifest / resolved version facts (in version control)', 'build baseline dependency / toolchain face', 'config definitions and secret reference / schema / injection registry', 'config change record (§42 five elements)', 'review record (SP-12, revision-bound)']
- 额外证据（仅当）：['gate-zeroing-classification-rationale', 'cross-boundary-judgment-rationale', 'sp10-handoff-facts']
- 证据规则：all other evidence emerges naturally from the work
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-01 新项目从 0 到第一条正常 Change（按需）
- JG-02 开发一个新能力 / 修改现有能力（按需）
- JG-05 新增或升级 Dependency / Toolchain / Config

## 理论回溯

- **part1**：GI-03, GI-05
- **part2**：p2-ch1-7.2-dependency-lock, p2-ch1-7.3-config-secret-separation, p2-ch9-19-25-what-authority, p2-ch11-5-6-build-definition-dependency-input, p2-ch11-16-17-config-artifact-secret, p2-ch11-26-environment-rebuildable, p2-ch11-42-config-change-is-release, p2-ch11-86.1-86.2-build-minimum-must
- **part3**：source-build-runtime-mapping
- **part4**：ch3-dependency-config-impact-deepening, ch5-implementation-time-dependency-generated-code

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
