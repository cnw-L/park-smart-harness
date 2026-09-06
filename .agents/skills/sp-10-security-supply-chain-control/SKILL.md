---
name: sp-10-security-supply-chain-control
description: 'SP 规程 SP-10 Security / Supply Chain Control｜安全/供应链控制（软件项目开发工程规范指南·第五篇）：Run controlled professional security control for a change touching the security surface: early security requirement recognition, enforcement points truly effective at trusted boundaries, third-party / supply-chain risk disposition, secret security disposition, risk-tiered artifact integrity / … 适用触发：change touches security surface；third party security disposition；secret security event；release artifact supply chain。'
metadata:
  spec.part5.sp-id: SP-10
  spec.part5.name: Security / Supply Chain Control
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP10-SecuritySupplyChainControl-正式操作规程.md
---

# SP-10 Security / Supply Chain Control｜安全/供应链控制

> 《软件项目开发工程规范指南》第五篇执行规程 SP-10 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Run controlled professional security control for a change touching the security surface: early security requirement recognition, enforcement points truly effective at trusted boundaries, third-party / supply-chain risk disposition, secret security disposition, risk-tiered artifact integrity / provenance / SBOM and release-permission control, and security evidence organization. Security is not a pre-launch scan; UI hide and client validation are not enforcement; dependency identity belongs to SP-09, security disposition to this procedure — never mutually covering.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- change touches security surface
- third party security disposition
- secret security event
- release artifact supply chain

## 操作步骤

### A1 · Confirm entry and security touch surface
控制模式：automation-assisted

- enumerate touched security surfaces per §18 ten concern classes; identify trust boundary changes
- B1 re-challenge: upstream internal-tool-no-security / no-trust-boundary / N-A classifications without resolvable rationale return to SP-04

### A2 · Security requirement recognition and verifiabilization
控制模式：engineering-decision

- verifiable expression per applicable concern (§18); testable, reviewable
- safety domain judgment (§25): systems controlling personal-risk domains register explicitly and stack dedicated safety standards — this spec never replaces them; "not applicable" for ordinary business systems carries rationale (B1)
- recognition completes before code completion; security requirements discovered after code completion are handled as new impact

### A3 · Enforcement point and validation boundary design
控制模式：engineering-decision

- each security requirement gets an enforcement point at a trusted boundary (§40, §67.6 [MUST][BASELINE]); frontend / client measures may be UX, never enforcement
- external input validation boundary and rule ownership explicit (§41): validated per contract (type / range / format / size / allowed value / authorization context); single rule ownership, no multi-layer conflicts
- design hands to SP-05 (when material), implementation to SP-06

### A4 · Third-party / supply chain disposition
控制模式：engineering-decision

- taking over SP-09 dependency facts (or directly identified), assess trustworthiness / maintainability / known risk (§24); disposition = adopt / replace / remove / mitigate with rationale recorded
- known vulnerability -> vulnerability response (impact scope / fix version / temporary mitigation / verification); emergency-level response via Ch8 + SP-21 pending-definition (group-5) compressed path, disposition records never exempted

### A5 · Secret security disposition
控制模式：engineering-decision + guardrail

- secret in version history / logs / artifact / errors (Ch9 §20): never fixed by deleting the file — credential rotation + impact assessment + follow-up controls (scan rules / injection redesign) + record
- SP-09 registers the fact; this procedure executes the disposition

### A6 · Supply chain control tiering
控制模式：engineering-decision

- by risk (§49-51): baseline = artifact integrity verifiable; enhanced (high-security / external distribution / regulated / large dependency surface / supplier-acquirer requirement) = + signing / signed provenance / attestation / SBOM (auto-generated) / release archive
- tier judgment carries rationale (B1); provenance / attestation build-time production hands to SP-14; this procedure defines requirements and consumes evidence

### A7 · Release permission and separation of duties
控制模式：engineering-decision

- define / adjust build / promote / deploy / override-gate / rollback permissions (§56: authentication / authorization / least privilege / audit)
- SoD by risk (§57: no forced CAB; release authority and exception authority traceable — non-negotiable)
- execution and recording = SP-15 / SP-17; this procedure defines the permission face requirements

### A8 · Security verification obligation definition
控制模式：engineering-decision

- per security requirement / enforcement / disposition define verification obligations (which boundary, which evidence), handed to SP-11 / SP-12 / SP-13 for execution and binding
- never accepts "the scanner reported nothing" in place of requirement-level verification

### A9 · Security evidence organization
控制模式：automation-assisted

- aggregate security evidence bound to change revision for SP-13 evidence binding and later audits
- evidence by work: only tier judgment rationale / disposition rationale / safety judgment / B1 classifications must be explicitly written

### A10 · Handoff boundary summary
控制模式：engineering-decision

- material security design -> SP-05; implementation -> SP-06
- verification execution -> SP-11 / SP-12 / SP-13
- provenance production -> SP-14; release execution -> SP-15 / SP-17
- dependency facts <-> SP-09 (never mutually covering)
- emergency -> Ch8 + SP-21 pending-definition (group-5)
- current updates -> SP-19

## 硬门禁（不可跳过）

- **G-SP10-01**：security-requirement-enforced-at-trusted-boundary
- **G-SP10-02**：security-quality-requirements-recognized-before-code-complete
- **G-SP10-03**：artifact-integrity-verifiable
- **G-SP10-04**：deployment-release-permission-controlled
- **G-SP10-05**：release-and-exception-authority-traceable
- **G-SP10-06**：external-input-validated-at-correct-boundary-per-contract
- **G-SP10-07**：secret-incident-requires-rotation-impact-followup
- **G-SP10-08**：no-sp09-sp10-mutual-coverage
- **G-SP10-09**：personal-risk-systems-stack-dedicated-safety-standards
- **G-SP10-10**：gate-zeroing-classification-requires-resolvable-rationale

## 通过出口（什么算完成）

`passExit = Security Control Plan established (bound to change revision): applicable security concerns recognized and verifiable (before code completion) + enforcement point at trusted boundary per security requirement + supply chain / third-party / secret dispositions completed or controlledly in flight (owner + deadline) + control tier and permission face defined with rationale + security verification obligations handed to SP-11 / SP-12 / SP-13 -> handoff to SP-05 / SP-06 / SP-14 / SP-15 execution chains
`



**完成不意味着**：security-verification-passed, vulnerabilities-fixed-live, provenance-produced, release-permissions-effective

## 回退路径（发现问题去哪）

- security requirement discovered after code completion → handle as new impact (SP-04); never patch in place
- enforcement cannot be effective at trusted boundary → back to SP-05 redesign; client measures never impersonate enforcement
- third-party risk unacceptable with no alternative → escalate decision (owner / organization); never silently accept
- emergency vulnerability response → Ch8 + SP-21 pending-definition (group-5) compressed path; disposition records never exempted
- verification obligation cannot define evidence → back to A2 / A3 to verifiabilize; otherwise the requirement itself does not stand (Ch4 §18 chain)

## 证据义务

- 自然证据：['security requirement record (concern + verifiable expression)', 'enforcement design (enforcement point per requirement)', 'supply chain disposition / vulnerability response records', 'secret disposition record (rotation / impact / follow-up controls)', 'control tier judgment + permission face facts', 'security verification obligation list (handoff record)']
- 额外证据（仅当）：['tier-judgment-rationale', 'disposition-rationale', 'safety-judgment', 'b1-gate-zeroing-classifications']
- 证据规则：all other evidence emerges naturally from the work
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-01 新项目从 0 到第一条正常 Change（按需）
- JG-02 开发一个新能力 / 修改现有能力（按需）
- JG-05 新增或升级 Dependency / Toolchain / Config

## 理论回溯

- **part1**：GI-03, GI-05
- **part2**：p2-ch4-18-security-privacy-concerns, p2-ch4-25-safety-vs-security, p2-ch9-20-secret, p2-ch9-24-ssdf-third-party-sp09-division, p2-ch9-40-41-enforcement-input-validation, p2-ch9-42-ssdf-sdlc, p2-ch9-67.6-trusted-boundary-must, p2-ch11-11-provenance-slsa, p2-ch11-49-integrity-floor, p2-ch11-50-secure-release, p2-ch11-51-sbom, p2-ch11-56-deployment-permission, p2-ch11-57-sod-traceability, p2-ch11-86.1-86.2-build-minimum-must
- **part3**：source-build-runtime-mappings
- **part4**：ch5-enforcement-implementation, ch6-security-verification-evidence, ch7-integrity-provenance-permission-at-release, ch8-emergency-security-response

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
