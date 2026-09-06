# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-20 Maintenance / Debt / Deprecation / Retirement

> 类型：Specialized Procedure  
> 状态：SEALED（2026-09-01：组5 Independent Concept Audit PASS AFTER REPAIR（P1×2 已修复）+ 横向回归全量引用核验 PASS；证据见组5 审计报告与横向回归报告）  
> 单一职责：把长期维护期的一切受控修改组织回**同一 Change Loop**（Maintenance Request 是 Maintenance 语境的 Change Request，不另建第二流程），治理 Tech Debt / Workaround / Dependency EOL 等长期负担的记录与优先级，管理多版本 Support 与 Backport，并执行 Deprecation → EOL → Retirement 的受控退出生命周期（含 Data Retirement、Zombie Resource 防护与 Final Baseline / Archive）。核心事实为 Maintenance Change。  
> Maintenance 不存在"因为只是维护所以可以少测"；退役不是删除——没有 Consumer Impact、数据处置与 Shutdown Evidence 的下线是违规；不能把未完成 Requirement 改名 Technical Debt 来关闭 Change。  
> 结构化镜像：`第五篇-SP20-MaintenanceDebtRetirement-OperationContract.yaml`

---

# 1. Trigger

```text
A. Maintenance Request 接收：缺陷（Corrective）/ 潜在故障（Preventive）/
   环境变化（Adaptive：Runtime / OS / Database / External API / 平台 / 法规）/
   交付后新增能力（Additive）/ 质量改善（Perfective）/ Emergency 后续义务
   （Ch12 §11-17、§18）——JG-09 主线：SP-20 → SP-03 → applicable SPs → SP-19
B. Tech Debt / Workaround 治理：债务记录与优先级、Backlog 卫生、
   Workaround 与 Temporary Mitigation 的退出（§33-40、§56-57）
C. 长期风险输入：Security Vulnerability、Dependency / Platform EOL、
   Compatibility Debt（§27-32）——必须转成明确 Maintenance Risk
D. 退出生命周期：Deprecation / EOL / Retirement 决策与执行、
   Data Retirement、Zombie Resource 处置、Final Baseline / Archive
   （§67-73、第三篇 Ch6 §61）
```

红线：**Maintenance Change 必须走受控 Change Loop**（Need / Impact / Implementation / Verification / Release / Current Update 可追，§76.1 [MUST][BASELINE]）；**Deprecation / EOL / Retirement 是三个不同的受控状态**（§68）——"老系统没人用了直接下线"不是退出，是事故源头。

不触发本规程的情形：

```text
Incident 稳定与 Emergency 压缩执行             → SP-21 / Ch8（本规程只管
                                                 Emergency 后续义务，§76.2）
Change Loop 自身的执行（Establishment / Impact /
Design / Implementation / Verification /
Delivery / Current Update）                → SP-03 及后续各规程——MR 不另建
                                                 流程（§17），本规程管语境、
                                                 入口与维护期特有义务
依赖与工具链变更的工具执行面（Manifest / Lock /
Toolchain Decision / Config Change）       → SP-09（本规程管依赖作为长期
                                                 Maintenance Risk 的规划面）
Flag 债务的暴露语义与清理执行               → SP-16 A6/A7（本规程的 Debt
                                                 六字段框架接纳其登记）
Contract 演进 / 兼容承诺                     → SP-07；Migration / Backfill → SP-08
Recovery 执行                               → SP-18；Target Validation → SP-17
项目级 Current Baseline 正式迁移 / Closure
  判定（含 Debt vs Closure 边界 §78-81）    → SP-19（本规程提供 Debt 记录
                                                 事实与维护侧输入）
执行资产（Guide / Template / Workflow）自身
  的治理                                   → SP-22
```

---

# 2. 输入

```text
维护期输入源                       Defect 报告 / Finding / Vulnerability
                                   Advisory / Dependency 与 Platform EOL
                                   公告 / 性能与健康信号 / 用户能力请求
                                   （§1-9、§27-32）
当前 Baseline Scope                SP-19：scoped Current（明确 Scope 下的
                                   Contract / Data / Structure / Deployment
                                   事实，第三篇 Ch1 §D）
现存 Debt / Workaround / Flag 资产 Debt Registry（六字段记录）、Temporary
                                   Mitigation 清单、Flag Registry 债务面
                                   （SP-16 A7 移交）
支持面事实                         现行 Support Policy（支持的 Scope / Version /
                                   期限）、Consumer 清单与依赖面（§45、§69）
维护容量与优先级现状               Capacity 分配、Recurring Incident /
                                   Defect Escape / EOL Risk 等信号（§60-64）
```

入口再挑战义务（B1 系统性规则）：使 Gate 归零的归类——"只是维护不用走完整流程"、"内部工具不需要 Support Policy"、"这个债务以后再说"、"没人用的服务直接下线"——必须携带可解析理由；没有理由或理由不成立的，按对应 Trigger 处置，不得归零。

---

# 3. 输出

```text
Maintenance Request（MR）          Maintenance 语境的 Change Request：分类
                                   （六类，可多重）+ Need / Impact 事实 +
                                   优先级依据 → 走 SP-03 开立（§17、§76.1）
长期风险登记                       Dependency / Platform EOL / Vulnerability
                                   → 明确 Maintenance Risk：Deadline + Impact +
                                   Upgrade/Replace Plan + Verification（§30、§76.3-4）
Debt Registry 记录                 六字段：Problem / Why accepted / Current
                                   Cost-Risk / Owner / Trigger-Cleanup
                                   Condition / Affected Boundary（§35）+
                                   优先级判定与 Backlog 卫生处置（§36-37）
Workaround / Temporary Mitigation
  治理决定                         Owner + Exit Condition + Risk；Workaround
                                   ≠ Permanent Fix 的追踪决定（§56-57）
Support / Backport 决定            Support Policy 修订建议、Backport 独立
                                   Change 开立（重评而非机械 cherry-pick，§46）、
                                   Patch 完整性要求（Contract / Data / Docs，
                                   §44）
退出生命周期产物                   Deprecation 决定 + 通知、Retirement Plan
                                   （§70 十四项）、Data Retirement 处置、
                                   Zombie Resource 清单、Final Baseline /
                                   Archive（§71-73）
Maintenance Metrics                Recurring Incident / EOL Risk / Debt Age /
                                   Emergency Change Rate 等信号面（§60-62）
```

本规程**不输出**：

```text
Change Loop 各环节执行产物          → SP-03 及后续规程
Emergency 压缩执行与事后对账        → SP-21 / Ch8
Current Baseline 正式迁移 / Closure 判定 → SP-19
依赖变更的工具链执行面              → SP-09
Contract / Migration 设计           → SP-07 / SP-08
```

---

# 4. 核心语义

**Maintenance 走同一 Change Loop（§4-9、§17、§76.1）**：Maintenance Request 是 Maintenance 语境的 Change Request；六类 Type（Corrective / Preventive / Adaptive / Additive / Perfective，加 Emergency 后续）只用于理解、报告、优先级与规划，**不建立五套流程**——一切 Change 回到 Impact → Design → Implementation → Verification → Release（§17）。规模大到 System Boundary 重构 / 架构替换 / 独立新产品的，作为新 Development Effort 管理（§15）——边界服从工程管理语境，不为分类争论。

**维护期三类易混动作的边界（§1-9）**：Incident Response / Operational Mitigation（用既有运行能力处置，是 Operation）≠ Emergency Maintenance（改变 Maintained Software 的紧急受控修改，走压缩 Change Loop）≠ 正常 Maintenance（同 Loop 正常时点）。Workaround / 重启 / 限流不改变软件，不是 Maintenance Change；一旦修改软件（哪怕一行配置默认值）就是 Change，就进 Loop。

**Tech Debt 是记录不是污点（§33-40）**：Debt 是"已知的、为换取当时收益而接受的、抬高未来 Change / Reliability / Security / Ops 成本的负担"——不是道德失败，也不必全部偿还。每笔 Debt 六字段可追；优先级按 Change Frequency / Incident Risk / Security / 维护成本 / 预期存续期 / 业务价值裁剪；Backlog 定期卫生（Close 过时 / Merge / 重排 / 提级 / 显式接受）。**Toil ≠ Maintenance**：Toil 的目标是消除 Toil 自身的 Engineering Change。**Debt 不自动阻断 Closure**（P4 Ch9 §78、§81）：不违反有效 Accepted Obligation 且有独立 Owner / Tracking 的 non-blocking debt 可独立跟踪；但**未完成的 Requirement / Contract / Data / Security / Transition Obligation 不得改名 Technical Debt 来绕过关闭条件**（§79、§81）。

**Dependency 是长期风险面（§27-32）**：业务代码不改，依赖仍是风险——Library / Runtime / Base Image / OS / External API 各有 Version / Support Window / EOL / Breaking Change。不追求永远 Latest，也不永远不升：按 Support Status / Security Risk / Breaking Delta / Upgrade Cost / 测试能力形成 risk-based update cadence。**Critical Dependency / Platform EOL 必须转成明确 Maintenance Risk**（MR + Deadline + Plan，§30）——记在个人邮箱里不算。

**Support 与 Backport（§43-47）**：维护多版本的必须有显式 Support Policy（支持哪些 Scope / Version、到什么时候）；Patch 必须完整更新对应 Contract / Data / Docs，不只是 Code（§44）；**Backport 是独立 Change，按目标版本上下文重新评估**，不是机械 cherry-pick（§46）；Maintenance Branch 是可选手段不是义务（§47）。维护完成必须更新对应 **scoped Current Baseline Scope**——不引入新的 Current 模型，复用 Baseline Scope + Runtime Fact 表达（§43、§76.5）。

**Deprecation / EOL / Retirement 三分离（§67-73）**：**Deprecation**（仍可用、明确要求迁移）≠ **EOL**（明确 Scope / Version 自约定日期不再获 Support——必须给出自身 Support Policy 的明确表述，不能只写含糊的"EOL 日期"）≠ **Retirement**（真正停止运行 / 停止提供 / 移除）。序列 Deprecation → Migration / 通知 → EOS → Retirement；Consumer 同 Team 控制 / 可原子迁移 / Critical Security Emergency 时可缩短 / 重叠 / 跳过，但 Impact / Communication / Final State 必须显式（§68）。先知道 Consumer 是谁（§69），再谈下线。

**退役是受控 Change（§70-73、§76.6）**：Retirement Plan 十四项；Data Retirement 十项考虑（Legal Retention / Audit / Customer Export / Backup Copy / Derived Data / Search Index / Cache / Analytics / Secret / Encryption Key——备份与派生物也含退役义务，§71）；Zombie Resource（Old Topic / Queue / Bucket / Index / Credential / Replica）在 Consumer discovery / 成本 / 安全三个维度持续清理（第三篇 Ch6 §61）；Final Baseline / Archive 八项，保留期限由 Business / Legal / Security / Contract 决定（§73）。Shutdown Evidence：Command SUCCESS ≠ Complete（GI-06）——"服务已停"要验证到流量为零、访问已撤、数据已处置。

---

# 5. Engineering Actions

## A1 — 入口分类与 MR 开立

把维护期输入按六类归类（可多重，§17）并判定边界：操作类处置（重启 / 限流 / 配置调整不改软件）留在运行域并按 A4 治理 Workaround；修改软件的（含 Emergency 后续修复）开立 MR → **SP-03** 走同一 Change Loop。规模判定：System Boundary 重构 / 新独立产品 → 新 Development Effort（§15，归类理由成文）。

## A2 — 长期风险输入转登记

Vulnerability / Dependency EOL / Platform Change / Compatibility Debt 不停留在告警与邮件：逐项转成明确 Maintenance Risk（MR + Deadline + Impact + Upgrade / Replace Plan + Verification，§30-32）进入维护规划。Quality Drift 与 Engineering Health 信号（§41-42）同属维护规划输入——复发 Incident、逃逸缺陷等健康指标恶化即长期风险的早期形态。Vulnerability 响应环（Assess → Mitigate / Fix → Verify → Release → Follow-up + Root Cause / Similar Vulnerability 检查，§27、§76.4）的 Follow-up 义在此挂账。工具执行面移交 SP-09。

## A3 — Debt Registry 记录与优先级

每笔 Tech Debt 六字段登记（Problem / Why accepted / Current Cost-Risk / Owner / Trigger-Cleanup Condition / Affected Boundary）；按 §36 维度定优先级；定期 Backlog 卫生（Close / Merge / Re-prioritize / Promote / Accept——显式接受也是合法处置，成文即可）。接纳 SP-16 移交的 Flag Debt 等专项债务面，统一进入本 Registry。Closure 语境的 Debt 边界判定（是否违反有效 Obligation / 是否仍属本 Change）事实由本规程供给，判定在 SP-19 域（P4 §78-81）。

## A4 — Workaround / Temporary Mitigation 治理

每个 Workaround / Temporary Mitigation（Feature Disabled / Compatibility Flag / Manual Runbook / Temporary Capacity / Emergency Config / Legacy Adapter）登记 **Why / Owner / Risk / Exit Condition**（§57）；Workaround 不关闭根因——对应 MR 保持 Open 直到 Root Cause Fixed 或 Risk 显式接受（§56），否则 Workaround 滑向 Toil。重复 Incident 的累计成本（Frequency / Cumulative Cost / Trend）进入优先级信号（§62）；Root Cause Action 不止于恢复原状（§63）。

## A5 — Support Policy 与 Backport

维护多版本的显式维护 Support Policy（Scope / Version / 期限）；Backport 按目标版本上下文重评并作为**独立 Change** 开立（SP-03）；Patch 完整性要求随 MR 附带：对应 Contract / Data / Docs 同步更新（§44），Verification 按 Risk 裁剪但**不存在"维护豁免"**（§58），Release 服从正常 Release Baseline——Hotfix 不是不可追踪 Release 的理由（§59）。

## A6 — 退出生命周期执行

Deprecation 决定成文并通知（仍可用 + 迁移要求）；EOL 表述绑定自身 Support Policy（明确 Scope / Version / 日期）；Retirement Plan 十四项（§70）——先做 Consumer discovery（§69），再按序执行。时间线压缩 / 重叠 / 跳过的（§68 三条件）归类理由成文；Impact / Communication / Final State 必须显式。退役执行本身是 Change：走 SP-03 及后续，交付面归 SP-15，验证归 SP-13 / SP-17。

## A7 — Data Retirement 与 Zombie Resource 处置

按 §71 十项处置数据退役：Legal Retention / Audit / Customer Export / Backup Copy / Derived Data / Search Index / Cache / Analytics 聚合 / Secret / Encryption Key——派生物同担退役义务。Zombie Resource 清单（第三篇 Ch6 §61：Old Database / Topic / Queue / Namespace / Bucket / Index / Credential / Backup / Replica）随 Retirement Plan 清理；重大 Data / Resource Change 后按第三篇 §62 校准 Current Mapping。Final Baseline / Archive 八项归档，保留期限判定（Business / Legal / Security / Contract）成文（§73）；Shutdown Evidence（流量为零 / 访问已撤 / 数据已处置的验证事实）齐备才 PASS。

## A8 — Legacy 修改与现代化路径

改 Legacy 前先建 Characterization Evidence（Characterization Test / Observed Contract / Data Snapshot / Runtime Baseline）区分 Current Behavior 与 Target Behavior（§49）；Rewrite 必须由 Benefit / Risk / Lifetime 支撑而不是代码旧（§48）；大型现代化优先可迁移路径（Current → Boundary → Incremental Replacement → Compatibility → Data Migration → Retire Old，§50），Pattern 选择归 SP-05 设计。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Debt Registry / Risk 登记与提醒 | Automation |
| Maintenance Metrics 采集 | Automation（EA-15） |
| MR 分类 / 优先级 / 容量分配 | Engineering Decision |
| Backlog 卫生 / 显式接受 / Rewrite 判定 | Engineering Decision（判定携带理由） |
| Deprecation / EOL / Retirement 决策 | Engineering Decision |
| Change Loop 各环节执行 | 归 SP-03 及后续规程 |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP20-01 Maintenance Change 必须走受控 Change Loop
                     （SP-03 起），Need / Impact / Implementation /
                     Verification / Release / Current Update 可追——
                     不建第二流程，"只是维护"不豁免（§17、§76.1）
[MUST][BASELINE]    G-SP20-02 Maintenance Verification 只按 Risk 裁剪，不存在
                     "维护可以少测"；Patch Release 服从正常 Release Baseline，
                     Hotfix 不得成为不可追踪 Release（§58-59）
[MUST][BASELINE]    G-SP20-03 Emergency Maintenance 必须有 Follow-up Owner /
                     Permanent Resolution / Cleanup Condition / Evidence
                     （§18、§76.2）——压缩执行归 SP-21 / Ch8，义务不消失
[MUST][BASELINE]    G-SP20-04 Critical Dependency / Platform EOL 必须转成明确
                     Maintenance Risk（MR + Deadline + Plan），不得只记在
                     个人记忆 / 邮箱（§30、§76.3）
[MUST][BASELINE]    G-SP20-05 Vulnerability 响应必须走 Assess / Mitigate-Fix /
                     Verify / Release / Follow-up 环，含 Root Cause 与
                     Similar Vulnerability 检查（§27、§76.4）
[MUST][BASELINE]    G-SP20-06 Tech Debt 六字段登记（Problem / Why accepted /
                     Current Cost-Risk / Owner / Trigger-Cleanup Condition /
                     Affected Boundary）；未完成 Requirement / Contract / Data /
                     Security / Transition Obligation 不得改名 Technical Debt
                     关闭 Change（§35、P4 Ch9 §79/§81）
[MUST][BASELINE]    G-SP20-07 维护完成必须更新对应 scoped Current Baseline
                     Scope（Contract / Data / Docs 同步，不只 Code）（§43-44、
                     §76.5；正式迁移经 SP-19）
[MUST][BASELINE]    G-SP20-08 Retirement 必须受控：Consumer Impact /
                     Migration-Replication / Data Handling / Access Removal /
                     Shutdown Evidence 齐备；Deprecation / EOL / Retirement
                     三分离，EOL 必须绑定自身 Support Policy 表述（§68、§70-73、
                     §76.6）
[MUST NOT][BASELINE] G-SP20-09 无依据的 gate-zeroing——"只是维护"、"内部工具
                     不需要 Support Policy"、"债务以后再说"、"没人用直接
                     下线"归类必须携带可解析理由，并可被 SP-05 / SP-13 / 组级
                     审计再挑战（B1）
```

---

# 7. PASS Exit

```text
维护周期 / 单项维护义务完成（绑定 MR 或治理对象）：
  MR 走完 Change Loop 且 scoped Current Baseline Scope 已更新（经 SP-19）
+ 适用时：长期风险登记成文（Deadline + Plan）、Debt 六字段 / Workaround
  治理决定在案、Support / Backport 决定在案
+ 适用时（退出生命周期）：Consumer Impact / Data Retirement / Zombie
  清单 / Final Baseline / Shutdown Evidence 齐备
+ Maintenance Metrics 信号面持续可用
→ 移交 SP-03（后续 Change）/ SP-19（Current / Closure）/ SP-21
  （Emergency 对账，适用时）
```

完成**不代表**：Change Loop 各环节已执行（SP-03 及后续）/ 全部 Debt 已偿还（显式接受也是处置）/ Incident 已关闭（SP-21）/ 执行资产已治理（SP-22）。

---

# 8. Evidence

Evidence by Work：

```text
MR 记录（分类 + 优先级依据）
长期风险登记（EOL / Vulnerability：Deadline + Plan + Follow-up）
Debt Registry 条目（六字段）与 Backlog 卫生记录
Workaround / Temporary Mitigation 治理记录（Owner + Exit Condition）
Support Policy 与 Backport 重评记录
Deprecation 通知 / Retirement Plan / Data Retirement 处置 /
  Zombie 清理 / Final Baseline / Shutdown Evidence
Maintenance Metrics 信号（EA-15）
```

只有 gate-zeroing 归类理由（只是维护 / 内部工具 / 债务以后再说 / 直接下线）、显式接受 Debt、时间线压缩、Rewrite / 新 Development Effort 判定、保留期限判定必须显式成文；其余证据随工作自然产生。

---

# 9. Current Update Obligation

本规程**不直接写 Current**。维护完成对应的 scoped Current Baseline Scope 更新是 Change Loop 的一环，**正式迁移经 SP-19**（§43、§76.5）；维护期新增的 Runtime State 事实按 SP-15（执行期）/ SP-17（Accepted 面）既有通道提交。本规程保证维护侧输入（Debt 事实、Support Policy、Retirement Final State）可供 SP-19 消费（EA-17 可发现性）。

---

# 10. FAIL / Return Path

```text
MR 缺 Need / Impact 事实            → 补齐后再入 Loop（SP-03 入口退回）
Emergency 后续义务无人认领          → 升级项目 Owner 决策；不得静默挂账
Debt 无法归 Owner                   → 登记为无主债务并进入容量 /
                                         优先级 trade-off 议题（§64）
Backport 在目标版本不可行           → 如实关闭该 Backport MR 并记录原因；
                                         不得强行 cherry-pick
Consumer 无法在 EOL 前迁移          → Support Policy 调整或延期决策成文
                                         （Requirement Authority 决定）
Retirement 阻断（数据 / 法律 / 合同）→ 转 Data / Legal / Contract 域处置
                                         （SP-08 / SP-07 交界），Final State
                                         延后但显式
Material 设计问题（退役路径 / 现代化
  路径不成立）                      → SP-05
Closure 边界争议（是否可改名 Debt）  → SP-19 域判定（P4 §78-81）
```

---

# 11. Exception / Alternative Path

## 11.1 Legacy 无测试保护

修改前先建 Characterization Evidence（§49）作为 Change 的 Verification 基线；这不是宣称旧 Behavior 永远正确，而是先分开 Current Behavior 与 Target Behavior 再安全修改。

## 11.2 大型新增 / Rewrite

规模达到 System Boundary 重构 / 架构替换 / 独立新产品的，按新 Development Effort 管理（§15）；Rewrite 由 Benefit / Risk / Lifetime 支撑（§48）——"代码旧"不是理由，归类成文。

## 11.3 退出时间线压缩

Consumer 同 Team 控制 / 可原子迁移 / Critical Security Emergency 时可缩短 / 重叠 / 跳过序列阶段（§68），但 Impact / Communication / Final State 三项必须显式——压缩的是时间线，不是义务。

## 11.4 Emergency Maintenance 交界

紧急修改软件 = Emergency Maintenance，压缩执行归 SP-21 / Ch8；本规程持有其不可压缩的后续义务：Follow-up Owner / Permanent Resolution / Cleanup Condition / Evidence（§76.2）。

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05 / GI-06 / GI-13（Shutdown Evidence 与"系统重新可用"
  同为 GI-06 应用；Debt 记录是 GI-05 真实状态义务的长期面）

Part II:
Ch12 全章——§1-9（Maintenance 范围与 Operation / Emergency 边界、同一
  Change Loop、MR=CR、PR≠MR）、§10-17（六类 Type 与"不建五套流程"）、
  §18-26（Emergency / Triage / Security 交界，执行归 SP-21）、§27-32
  （Vulnerability 环 / Dependency 长期风险 / EOL 转登记 / Platform /
  Compatibility Debt）、§33-42（Debt 六字段 / 优先级 / Backlog 卫生 /
  Toil≠Maintenance / Quality Drift / Engineering Health）、§43-47（scoped Current / Patch 完整性 / Support
  Policy / Backport / Maintenance Branch）、§48-50（Legacy / Rewrite /
  Characterization / 可迁移路径）、§51-55（Documentation / Knowledge /
  Handover / Owner / Service Level——Current 与 History 双保存）、
  §56-66（Workaround / Mitigation / Verification / Release / Metrics /
  容量 / Window）、§67-73（Deprecation-EOL-Retirement / Plan / Data /
  Zombie / Final Archive）、§76.1-76.6（全部 [MUST][BASELINE]）

Part III:
Ch1 §D（Current Structure 带 Baseline Scope——维护期 scoped Current 的
  结构面）、Ch6 §61-62（Zombie Data / Infrastructure Resource、
  Data / Infrastructure Calibration）、Drift 章（Debt / EOL / Old Path
  是 Drift 的长期来源）

Part IV:
Ch7（MR 作为 Change 走同一 Loop 的执行语境；Recovery / Rollout 交界归
  SP-18 / SP-15）、Ch8 §7+（Emergency 压缩路径交界——压缩义务时点不压缩
  义务本身）、Ch9 §77-83（CANCELLED/SUPERSEDED 仍走 Ch8；Debt 不自动阻断
  Closure / 未完成 Requirement 不得改名 Debt / Finding 不要求全 0 /
  Closure 不冻结 Current / Closure 后新问题）

Journey:
JG-09 维护、弃用、替换或 Retirement：SP-20 → SP-03 → applicable SPs →
  SP-19 Current / Closure
```

---

# 13. Executable Asset References

```text
EA-15 Observability          maintenance metrics 信号面（Recurring
                             Incident / Defect Escape / Security Finding
                             Age / Unsupported Dependency Count / EOL
                             Risk / Debt Age / Emergency Change Rate）
EA-17 Current Navigation    Debt Registry / Support Policy / Retirement
                             Final Baseline 的可发现性与 Authority 解析
```

工具适合：Debt Registry 维护、EOL / Cleanup Condition 到期提醒、Maintenance Metrics 采集、Consumer discovery 辅助扫描、Zombie Resource 清单比对。
工具不适合：优先级判定、显式接受 / Rewrite / 退出决策、Closure 边界判定（SP-19 域）、"扫描器没报警 = 无风险"式判断——工具输出是 Signal 不是判定器（GI-07）。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Maintenance = 同一 Change Loop + CI/CD 正常链（Patch 也是可追踪
  Release）；Debt Registry = issue tracker 标签体系 + EOL 到期提醒；
  Retirement = 流量摘除验证（Shutdown Evidence = 健康检查摘除 + 流量
  归零观察）+ 资源清理清单

RP-B-CLI（pending-definition，组6）:
  维护 = 版本分发；Backport 受分发成本约束显式判定；Retirement =
  停止分发 + 版本公告（已安装副本无法强制回收——Final State 表达为
  "不再支持"而非"已移除"，Support Policy 表述承担实义）

RP-C-SDK（pending-definition，组6）:
  Retirement = major 版本 EOL 公告 + Consumer 迁移指引；已发布版本
  不可撤回（Yanking 只是分发面动作）；Compatibility 承诺期内 Old
  Consumer 必须工作的义务由 SP-07 域保证
```

---

# 15. Example

**CHG-WO-142（工单转派能力升级）之后的维护周期——MR 三连与一次 Retirement。**（承接组5 SP-16 示例：reason 能力已 Launch，flag workorder.bulk_export 已登记为无主债务。本例覆盖 JG-09 主线的维护、债务与退出。）

```text
A1 入口：季度维护周期接收三类输入——(1) WO-1.9.1 缺陷报告：CLOSED
   工单在 bulk export 开启时仍可 Transfer（Corrective，§11 原生例子）；
   (2) psycopg 驱动依赖官方 EOL 公告（Adaptive + 安全面，§13/§30）；
   (3) reason 能力已 100% 暴露满一个 Release 周期 → SP-16 Cleanup
   Condition 触发（Additive 维护期的清理面）——各自开立 MR 走 SP-03
A2 长期风险：psycopg EOL → Maintenance Risk 登记（Deadline = 官方支持
   终止日；Impact = WO-1.8/1.9 全版本；Plan = 升级到受支持主版本并按
   §58 做 Compatibility / Integration 验证；工具执行面移交 SP-09）
A3 债务：flag workorder.transfer_reason 清理 MR（移除 Flag + 无 reason
   旧代码路径，SP-16 A6 移交）；flag workorder.bulk_export 认领 Owner =
   work-order-service；六字段补齐（Problem = 8 个月无主 Old Code Path /
   Why accepted = 历史 Change 遗留未登记 / Current Cost-Risk = Test
   Combination + 未知行为面 / Trigger-Cleanup = 本周期缺陷修复后评估
   移除 / Affected Boundary = export 模块）
A4 Workaround：(1) 缺陷的临时缓解 = 运行侧对 CLOSED 工单 bulk export
   加过滤（不改软件，Operation 域）→ 登记 Owner + Exit Condition =
   MR-1 修复发布；MR-1 保持 Open 直到 Root Cause Fixed（§56）
A5 Support：WO-1.8 仍在 Support Policy 支持期 → 缺陷修复 Backport 到
   1.8.1：独立 MR、按 1.8 上下文重评（V203 expand 已在 1.8 生效的
   事实核对）——不机械 cherry-pick；Patch 完整性 = 更新 transfer
   Contract 文档与 CLOSED 状态机说明（不只 Code）
A6 退出：旧 SOAP transfer v1 接口 Deprecation 满 6 个月（Consumer
   迁移通知已有回执确认）→ Retirement Plan 十四项执行：Consumer
   discovery 确认仅剩 1 个内部 Consumer（同 Team 控制 → §68 压缩条件
   成立，理由成文）；Final State = v1 端点移除 + v2 REST 全量承接
A7 数据与僵尸资源：v1 退役数据处置——SOAP 请求日志归档（保留期限按
   合同判定）、派生的 v1 统计视图同批退役、v1 专用凭据撤销；Zombie
   清单核对（旧 Topic / Index / Credential 清理）；Shutdown Evidence =
   端点摘除后流量归零观察 + 访问撤销验证（GI-06）
A8 Legacy 面：缺陷修复触碰无测试的旧分配逻辑 → 先补 Characterization
   Test 固定 Current Behavior（CLOSED 不可 Transfer 的既有语义），
   再修 Target Behavior——Verification 基线先行（§49）
```

---

# 16. 最终原则

> **维护不是开发的余晖，是软件真实生命周期的大部分：它不配第二套流程，只配同一条被认真走的流程。债务不是耻辱，无主的债务才是；退役不是删除，是把"谁还在用、数据去哪里、凭什么说停了"回答清楚之后再关灯。一个系统老了不是从代码旧开始的，是从登记簿上第一笔"以后再说"开始的。**
