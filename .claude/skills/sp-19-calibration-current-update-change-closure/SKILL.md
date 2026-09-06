---
name: sp-19-calibration-current-update-change-closure
description: 'SP 规程 SP-19 Calibration / Current Update / Change Closure｜校准/Current/收口（软件项目开发工程规范指南·第五篇）：Calibrate a change''s actual results into truthful Current: disposition every material Actual-vs-Accepted delta, commit each applicable Current Transition Obligation to its real authority (or confirm unchanged / controlled transition / transfer / no-longer-applicable), prove Scoped Current Update … 适用触发：change path complete needs closure；ch8 special lifecycle prerequisites done；standalone calibration；closure revalidation material change。'
metadata:
  spec.part5.sp-id: SP-19
  spec.part5.name: Calibration / Current Update / Change Closure
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP19-CalibrationCurrentUpdateChangeClosure-正式操作规程.md
---

# SP-19 Calibration / Current Update / Change Closure｜校准/Current/收口

> 《软件项目开发工程规范指南》第五篇执行规程 SP-19 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Calibrate a change's actual results into truthful Current: disposition every material Actual-vs-Accepted delta, commit each applicable Current Transition Obligation to its real authority (or confirm unchanged / controlled transition / transfer / no-longer-applicable), prove Scoped Current Update Completeness, and issue the Closure Decision while the Closure Basis is still applicable. SP-19 is the sole calibration/closure procedure and the executor of most Current commits; release/runtime transitions committed earlier under Ch7 authority are verified here, never re-faked.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- change path complete needs closure
- ch8 special lifecycle prerequisites done
- standalone calibration
- closure revalidation material change

## 操作步骤

### A1 · Confirm closure entry prerequisites; form Closure Accountability Scope
控制模式：automation-assisted

- ch8 prerequisites verified when applicable; missing -> return Ch8 path, never mask with a closure checklist
- history (starting scope / initial impact / old design scope) preserved
- reconciliation barrier sweeps: data, config, migration, external side effect, feature flag, runtime mapping, partial delivery, cleanup

### A2 · Form Applicable Current Transition Obligation Set
控制模式：engineering-decision


### A3 · Establish Calibration Subject Set
控制模式：automation


### A4 · Execute controlled Actual-vs-Accepted comparison
控制模式：automation-assisted


### A5 · Classify delta; issue Calibration Disposition
控制模式：engineering-decision

- **判定词汇**：
  - aligned
  - permitted-variance
  - controlled-transition
  - valid-exception
  - fix-reality-rework
  - update-accepted-authority
  - evidence-gap-not-ready
  - context-reconciliation-required
- material delta must not be masked as implementation detail
- fix-reality returns by cause: new-impact->SP-04, invalid-target-design->SP-05, implementation-defect->SP-06, candidate-evidence->SP-13, delivery-runtime->SP-15/17, special-lifecycle-residual->Ch8
- update-accepted-authority must pass the concern's real authority decision plus applicable impact/verification before any current update; no actual->current shortcut

### A6 · Authority-backed Current Commit (Commit Guard + Commit Barrier)
控制模式：automation


### A7 · Record Current Baseline Transition Ledger
控制模式：automation


### A8 · Truthful Current and cross-baseline coherence check
控制模式：guardrail + engineering-decision

- unexplained material actual-vs-expressed conflict blocks completeness
- health-affected current is legal but navigation must show finding, owner, disposition, successor/exit
- same-scope currents materially coherent or explicitly explained
- cross-scope differences legal when scope and responsibility are clear

### A9 · Judge Scoped Current Update Completeness
控制模式：guardrail + engineering-decision


### A10 · Form Closure Obligation Set and Closure Basis
控制模式：engineering-decision

- closure basis references evidence sets; it does not copy all logs
- findings/debt need not be zero, but each is judged: violates accepted obligation? still owned by this change? affects current truth? gate-relevant? has independent accepted follow-up?
- unmet requirement/contract/data/security/transition obligations must not be renamed technical debt to bypass closure

### A11 · Closure Revalidation and Closure Decision
控制模式：guardrail + engineering-decision

- completed != zero-bug / zero-debt / no-future-change
- candidate reject is a Ch6 candidate fact, never auto change-rejected
- terminal rejected with persistent side effects requires reconciliation first
- cancelled/superseded keep Ch8 prerequisites; SP-19 never redoes fence/transfer

### A12 · Post-closure obligations
控制模式：engineering-decision

- closure is a point-in-time decision; later current changes do not falsify it
- post-closure discoveries produce new finding/incident/change referencing the closure; history is never silently rewritten

## 硬门禁（不可跳过）

- **G-SP19-01**：no-closure-scope-limited-to-initial-intent
- **G-SP19-02**：observed-reality-never-auto-becomes-current-authority
- **G-SP19-03**：no-current-commit-without-commit-guard
- **G-SP19-04**：failed-unknown-conflicted-authority-write-is-not-committed
- **G-SP19-05**：no-completeness-with-unexplained-material-cross-baseline-conflict
- **G-SP19-06**：no-closure-while-transition-exit-responsibility-retained
- **G-SP19-07**：no-unmet-obligation-renamed-as-technical-debt
- **G-SP19-08**：gate-zeroing-disposition-requires-resolvable-rationale-evidence
- **G-SP19-09**：no-open-to-closed-without-closure-revalidation
- **G-SP19-10**：candidate-reject-never-auto-change-terminal-rejected
- **G-SP19-11**：no-ch8-prerequisite-bypass
- **G-SP19-12**：closure-and-current-transition-history-never-rewritten

## 通过出口（什么算完成）

`passExit = `



**完成不意味着**：system-zero-bug-or-debt, all-baselines-globally-same-version, candidate-accepted, future-evolution-frozen, history-rewritable

## 回退路径（发现问题去哪）

- ch8 prerequisite missing → ch8 path; SP-21 / SP-20 pending-definition (group-5); until then follow Ch8 body
- fix-reality by cause → ['SP-04 new impact', 'SP-05 invalid target/design', 'SP-06 implementation defect', 'SP-13 candidate/evidence', 'SP-15 / SP-17 delivery/runtime']
- evidence gap / not ready → complete evidence / reconciliation; never assume-aligned
- stale current (material concurrent change) → context reconciliation; update calibration basis; new revision or confirm current
- transition exit responsibility unresolved → complete exit, or transfer to traceably accepting successor/maintenance owner; current navigation must show active transition + new owner
- closure basis stale at revalidation → reconcile and re-decide

## 证据义务

- 自然证据：['calibration records (subject + delta + disposition + evidence ref)', 'authority-backed commit facts (§47 fields, in the real authority source)', 'transition ledger entries (references to facts)', 'closure basis reference set', 'closure decision record']
- 额外证据（仅当）：['disposition rationale', 'transfer acceptance', 'exception terms']
- 证据规则：small teams may fold into one issue; semantics never skippable
- Current 更新：writesCurrent = True
  

## 所属 Journey

- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data
- JG-05 新增或升级 Dependency / Toolchain / Config
- JG-06 构建并发布一个版本
- JG-07 部署后验证、扩大暴露或恢复（按需）
- JG-08 处理线上 Incident / Emergency
- JG-09 维护、弃用、替换或 Retirement

## 理论回溯

- **part1**：GI-02, GI-03, GI-05, GI-07, GI-11, GI-12
- **part2**：what-authorities-consumed-as-accepted-basis
- **part3**：ch8-calibration-direction, observed-evidence-not-authority, structure-finding-not-auto-update, health-affected-current
- **part4**：ch1-record-state-terminal-disposition-ledger, ch9-full, ch9-minimum-requirements-checklist, ch2-ch8-return-interfaces

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
