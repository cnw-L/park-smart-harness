---
name: sp-01-current-authority-navigation
description: SP 规程 SP-01 Current / Authority Navigation｜Current / Authority 导航（软件项目开发工程规范指南·第五篇）：Resolve a truthful, scope-partitioned, authority-resolvable Current Context for any engineering task. Read/resolve only — never writes Current, never approves anything. 适用触发：enter existing project；before change establishment；before impact design implementation；incident emergency；suspected drift。
metadata:
  spec.part5.sp-id: SP-01
  spec.part5.name: Current / Authority Navigation
  spec.part5.version: 1.0.0
  spec.part5.normative-source: 第五篇-SP01-CurrentAuthorityNavigation-正式操作规程.md
---

# SP-01 Current / Authority Navigation｜Current / Authority 导航

> 《软件项目开发工程规范指南》第五篇执行规程 SP-01 v1.0.0（sealed）的可执行投影。
> 完整规程原文（权威源）见 [references/PROCEDURE.md](references/PROCEDURE.md)；本文件为操作骨架。

## 职责（单一句）

Resolve a truthful, scope-partitioned, authority-resolvable Current Context for any engineering task. Read/resolve only — never writes Current, never approves anything.


## 边界（本规程不做的事）

（见完整规程）

## 触发

- enter existing project
- before change establishment
- before impact design implementation
- incident emergency
- suspected drift
- authority unclear
- before review verification release

## 操作步骤

### A1 · Determine scope and concern list
控制模式：engineering-decision


### A2 · Enter via Authoritative Navigation Surface
控制模式：guidance


### A3 · Resolve per-concern Current references to revision granularity
控制模式：automation


### A4 · Resolve Authority / Owner per concern+scope
控制模式：automation-assisted


### A5 · Resolve evidence pointers
控制模式：automation


### A6 · Compare Accepted vs Observed; classify findings
控制模式：automation

- the compared concern+scope set and its evidence must be enumerated explicitly; an empty comparison set is itself a reasoned declaration — "no known divergence" must never result from "no comparison performed"
- finding severity and disposition remain engineering decisions

### A7 · Tag truth status per item
控制模式：automation-assisted

- **判定词汇**：
  - fact
  - unknown-gap
  - absent
  - target

### A8 · Emit Current Context
控制模式：automation


## 硬门禁（不可跳过）

- **G-SP01-01**：no-change-on-undeclared-unknown
- **G-SP01-02**：tool-output-not-authority

## 通过出口（什么算完成）

`passExit = `



**完成不意味着**：current-is-healthy, current-is-latest-observed, change-authorized

## 回退路径（发现问题去哪）

- navigation entry missing or broken → ['SP-02 revalidation', 'remediation change']
- dangling reference or duplicate identity → part3 finding disposition
- missing authority → governance designates authority before semantic acceptance
- authority conflict → designated owner rules per concern+scope
- accepted != observed → ['calibration change', 'SP-19']

## 证据义务

- 自然证据：['navigation query / path record', 'pinned reference+revision in change record', 'observed evidence pointers (CI, deploy, telemetry)', 'health finding records']
- 额外证据（仅当）：['decision', 'rationale']
- 证据规则：
- Current 更新：writesCurrent = False
  

## 所属 Journey

- JG-00 进入已有项目并找到 Current
- JG-01 新项目从 0 到第一条正常 Change
- JG-02 开发一个新能力 / 修改现有能力
- JG-03 修改公共 API / Event / Contract
- JG-04 修改数据库 / Schema / Durable Data
- JG-05 新增或升级 Dependency / Toolchain / Config

## 理论回溯

- **part1**：GI-02, GI-04, GI-05, GI-07, GI-11
- **part2**：project, architecture, module, contract, data
- **part3**：ch1, ch2, ch7, ch8-accepted-vs-observed, ch8-authority-distributed, ch8-navigation-surface, ch8-health-finding
- **part4**：ch1-starting-working-baseline, ch1-context-reconciliation, ch2-change-establishment

详细章节映射见 [references/THEORY-TRACE.md](references/THEORY-TRACE.md)。

## 深入阅读

- [references/PROCEDURE.md](references/PROCEDURE.md) — 完整操作规程（权威源 Markdown 原文）
- [references/THEORY-TRACE.md](references/THEORY-TRACE.md) — 回溯到第一~四篇章节
- [assets/contract.yaml](assets/contract.yaml) — OperationContract 本体（EA-18 冻结 schema）
