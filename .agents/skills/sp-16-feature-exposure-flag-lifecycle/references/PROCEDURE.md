# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-16 Feature Exposure / Flag Lifecycle

> 类型：Specialized Procedure  
> 状态：SEALED（2026-09-01：组5 Independent Concept Audit PASS AFTER REPAIR（P1×2 已修复）+ 横向回归全量引用核验 PASS；证据见组5 审计报告与横向回归报告）  
> 单一职责：把能力的暴露（Launch / Exposure）与 Binary Deployment 解耦成两个受控事实——治理暴露资产与生命周期（Flag / Rollout Config 的 Owner / Purpose / Default / Launch Plan / Cleanup Condition），维护按真实粒度表达的 Exposure State，并保证暴露变化作为 Target-changing Action 交付。  
> 代码 100% Deployed 而 Feature Flag OFF 时，Feature 没有 Launch；Flag 不是 Release 风险的免费消除器，Temporary Flag 没有五要素登记就是未来的 Config Drift 与 Old Code Path。  
> 结构化镜像：`第五篇-SP16-FeatureExposureFlag-OperationContract.yaml`

---

# 1. Trigger

```text
A. 已部署代码包含尚未暴露的新 Feature / 能力，需要设计或执行 Launch
   （flag off→on、exposure 0%→5%→100% 渐进扩大）——JG-07 主线：
   SP-15 Delivery → SP-16（适用）→ SP-17 Target Validation
B. Exposure 状态变化会 materially 改变用户行为（流量切换、Tenant / Cohort
   扩大、Region 打开——Ch7 §87）
C. Flag 生命周期治理：Temporary Flag 登记、Cleanup Condition 触发清理、
   长期化判定（Ch11 §41）
D. Flag 债务：无 Owner / 无 Cleanup Condition / 永久 ON 的 Temporary Flag、
   Old Code Path 堆积、Test Combination 失控（Ch11 §41）
```

红线：**代码已 100% Deployed 且 Flag OFF ≠ Feature 已 Launch**（Ch7 §137）；"有 Flag 可以随时关"不构成跳过验证或暴露控制的理由（Ch11 §41）。

不触发本规程的情形：

```text
Transition 设计（Flag 作为 Transition 机制的选择、Migration ≠ Transition ≠
Rollout 的设计侧）                → SP-05（SP-05 §Transition 机制清单含
                                   Feature Flag / Shadow Path）
暴露变化的交付执行控制（Authority Token / Observation / Rollout Slice
Proceed·Pause）                   → SP-15（§86-87：暴露变化是 Target-changing
                                   Delivery / Rollout Action）
Target Validation 判定            → SP-17（暴露状态只是其验证 Concern 之一，
                                   Ch7 §70）
Recovery 执行                     → SP-18
Flag / Rollout Config 作为受控工程事实的单次发布（Config Change Record
五要素）                          → SP-09（Ch11 §42）；本规程管跨 Change 的
                                   生命周期，不重复其发布要素
长期业务配置成为跨边界承诺后的兼容演进 → SP-07
实现执行（Flag 代码路径）          → SP-06
Environment Current Runtime State 事实提交 → SP-15（执行期）；项目级 Current
                                   → SP-19（本规程不更新 Current）
```

---

# 2. 输入

```text
影响面事实                         SP-04：Confirmed Affected Scope 与 Concern
                                   ——触及哪些 Feature / 能力（Additive
                                   Maintenance 类交付后新增 Feature 适用，
                                   Ch12 §14）；"是否有暴露面变化"由本规程 A1
                                   基于交付事实判定，不是 SP-04 的输出
Transition / Rollout 设计          SP-05：Flag 是否作为 Transition 机制、
                                   Rollout 三分离（Migration ≠ Transition ≠
                                   Rollout）中的位置
交付与部署事实                     SP-15：哪些 Artifact 已部署到哪些 Target、
                                   Rollout Slice 现状
当前 Flag 资产现状                 Flag Registry：现存 Flag 清单、Owner /
                                   Default / Cleanup Condition 状态（Ch11 §41）
观察信号定义                       暴露面可用的 Signal：error / latency /
                                   business metric / migration progress
                                   （Ch7 §51、P2 Ch11 §70）
```

入口再挑战义务（B1 系统性规则）：上游使 Gate 归零的归类——"不需要 Flag 直接上线"、"暴露变化不 material 无需受控"、"内部工具无暴露面"——必须携带可解析理由；没有理由或理由不成立的，退回 SP-04 / SP-05 处置。

---

# 3. 输出

```text
Exposure / Launch Plan            暴露策略（All-at-once / Canary / Tenant-by-
                                   tenant / Flag 渐进，按风险裁剪 Ch11 §36）+
                                   渐进阶段与停止条件（§39）+ 各阶段观察信号
Flag Registry 条目（新增 / 更新）  Temporary Flag 五要素：Owner / Purpose /
                                   Default / Launch Plan / Cleanup Condition
                                   （Ch11 §41）；EA-14 证据面 = state + owner +
                                   cleanup
Exposure State 事实定义           按真实粒度（Target / Tenant / Cohort /
                                   percentage）的暴露状态表达与所需观察面
                                   （P2 Ch11 §70、Ch7 §53 归因要求）——事实
                                   提交由 SP-15 编排执行
暴露执行移交包                    移交 SP-15：暴露变化作为 Target-changing
                                   Action 的 Launch Plan、暴露语义、恢复意图
                                   （含紧急 disable 的意图表达）
Flag 清理 / 长期化判定            Cleanup Condition 触发的移除计划（含 Old
                                   Code Path）；长期业务配置 → 正式
                                   Configuration Contract 的移交判定（§41）
Flag Debt 登记                    无 Owner / 无 Cleanup / 永久 ON——Risk +
                                   Owner + Cleanup Condition
```

本规程**不输出**：

```text
暴露变化的执行与 Authority 控制    → SP-15
Target Validation 结论            → SP-17
Recovery 执行                     → SP-18
Flag Config 单次发布的 Config Change Record → SP-09
跨边界承诺的兼容演进               → SP-07
Current 任何更新                   → SP-15（执行期 Environment Current
                                   Runtime State 编排）/ SP-19（项目级）
```

---

# 4. 核心语义

**Deployment 与 Launch 是两个事实（Ch11 §2.5、§3、Ch7 §86）**：Build ≠ Deploy ≠ Release ≠ Feature Launch。Binary 已 Deploy 而 Flag OFF 时，Deployment 已发生、Feature Launch 还没发生——"什么时候开始产生用户影响"、"出问题应该回滚 Binary 还是关闭 Flag"、"哪个动作属于 Release Evidence"因此可回答（Ch11 §3）。暴露可以经 Flag 渐进（0%→5%→50%→100%），把 Feature Launch 与 Binary Release 分离（Ch11 §40）。

**暴露变化是 Target-changing Action（Ch7 §87、§114）**：flag off→on、流量 0%→100% 会 materially 改变用户行为的，作为 Target-changing Delivery / Rollout Action 获得相应 Observation / Validation / Recovery——执行控制（Authority Token 确认、Rollout Slice、Proceed / Pause）归 SP-15；**feature disable、traffic revert 这类反向动作同样受 Target Change Authority Token 约束**（§114-115），旧 Intent 的异步 disable 不得覆盖被新 Intent 接管的 Target。本规程定义暴露语义与生命周期，不绕过 SP-15 直接执行。

**Flag 不是免费消除器（Ch11 §41）**：Flag 增加 ON/OFF State、Tenant Difference、Config Drift、Old Code Path、Test Combination、Cleanup Cost。所以 Temporary Flag 必须有五要素：**Owner / Purpose / Default / Launch Plan / Cleanup Condition**。真正长期业务配置应进入正式 Configuration Contract（定义归 SP-09，演进归 SP-07）——Flag 是暴露控制手段，不是永久架构。

**Exposure State 按真实粒度表达（P2 Ch11 §70、GI-05）**：渐进暴露期间系统真实处于 Partial Exposure——per-Target / per-Tenant / per-Cohort 的 Flag State、当前 percentage、Artifact version distribution、Stop / Pause 状态必须可观察；不得把渐进过程压扁成"已上线 / 未上线"的单一 Boolean。Flag 是 Runtime Behavior 的决定因素之一（第三篇 Ch3 §31），Runtime / Deployment Mapping 应能追到重要 Flag Reference；同时 Flag 也是 Observation 误判的解释来源之一（第三篇 Drift 章 §61：看到不匹配先查是不是 Flag 差异，再谈 Drift）。

**暴露策略按风险裁剪（Ch11 §36）**：本规范不规定所有能力都必须渐进暴露——内部低影响能力可以 All-at-once；高影响 / 面向外部 Consumer 的能力用 Flag / Canary / Tenant-by-tenant 限制 Blast Radius。裁剪判断携带理由（B1）。

---

# 5. Engineering Actions

## A1 — 确认入口与暴露对象

从 SP-04 移交 Affected Scope 与 Concern、从 SP-05 移交 Transition / Rollout 设计出发，由本规程确认：是否有暴露面变化（基于交付事实，SP-15 输入）、哪个 Feature / 能力待暴露、是否 Flag 门控、暴露维度（instance / traffic / region / tenant / cohort / feature exposure，Ch7 §48）。执行 B1 再挑战："直接上线无需 Flag"、"不 material"的归类没有理由的，退回 SP-04 / SP-05。

## A2 — 暴露策略与 Launch Plan 设计

按风险选择暴露策略（Ch11 §36）并形成 Launch Plan：渐进阶段（如 0%→5%→20%→100%）、每阶段停止条件（error / latency / critical business failure / data inconsistency，§39——阈值来自服务 Requirement / Baseline，不由本规程统一规定）、每阶段观察信号（Ch7 §51；高风险暴露的证据必须能归因到 Release Revision 与 Rollout Slice，§53）。Launch Plan 作为暴露执行移交包的主体交 SP-15。

## A3 — Flag 资产登记（五要素）

每个 Temporary Flag 在 Flag Registry 登记：**Owner / Purpose / Default / Launch Plan / Cleanup Condition**（Ch11 §41；EA-14 的 state + owner + cleanup 证据面）。Default 值策略显式（尤其 OFF 为默认的 fail-safe 设计）；无五要素的 Flag 不得进入暴露执行。

## A4 — Exposure State 事实与观察面定义

定义暴露状态的表达粒度与观察面：per-Target / per-Tenant / per-Cohort 的 Flag State、当前 percentage、Artifact version distribution、Stop / Pause 状态（P2 Ch11 §70）。暴露状态事实是 Environment Current Runtime State 的一部分，**提交由 SP-15 在执行期编排**（Ch7 §60-62：Mixed State 如实记录）；本规程保证语义粒度不被压扁（GI-05）。无服务端形态用 Distribution Record / Channel / Cohort / Installation / Adoption / Version Exposure 实现同类语义（Ch7 §88、SP-15 §11）。

## A5 — 暴露变化执行移交

flag 翻转、exposure 扩大、紧急 disable 等暴露变化**全部移交 SP-15** 作为 Target-changing Action 执行（§86-87：Authority Token 确认、Observation、Rollout Slice 控制；§114：feature disable / traffic revert 同受约束）。本规程提供 Launch Plan、暴露语义与恢复意图；Target Validation Concern（含暴露后的行为验证）归 SP-17。"暴露变化不 material 无需受控"是 gate-zeroing 判断，携带理由（B1）。

## A6 — Flag 清理与长期化判定

Cleanup Condition 触发时执行移除计划：Flag 移除 + Old Code Path 删除 + Test Combination 收缩，作为正常受控 Change 走 SP-03 及后续规程。长期化显式判定：确实长期存在的业务开关 → 进入正式 Configuration Contract（§41；定义与发布归 SP-09、成为跨边界承诺后演进归 SP-07）；Kill switch / 安全开关类长期 Flag 判定为 permanent 资产（Owner + 定期演练），不算债务但显式登记。"临时 Flag 再挂一个版本"没有理由的，按债务处置。

## A7 — Flag 债务治理

巡检 Flag Registry（作为 Maintenance Input，Ch12 §7 的 Maintenance Planning 面）：无 Owner / 无 Cleanup Condition / 永久 ON 的 Temporary Flag / Old Code Path 堆积——登记 Flag Debt：Risk + Owner + Cleanup Condition（防垃圾场化，Ch12 §37 同理）。需要设计性移除路径（Old Code Path 已成依赖）→ 移交 SP-05 设计。

## A8 — Client / 无服务端形态适配

客户端 / 设备软件的暴露 = Version Exposure：经 Distribution Channel / Cohort 控制（灰度渠道、分阶段推送），Launch 语义用 Installation / Adoption Observation 表达（Ch7 §88）。不伪造服务端 Environment Deployment Record；分发执行归 SP-15，本规程管暴露语义与采用度事实。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Flag Registry 登记 / 状态维护 | Automation |
| 暴露状态事实采集与记录 | Automation（经 SP-15 编排） |
| 暴露策略 / Launch Plan / 渐进阶段设计 | Engineering Decision |
| 长期化 / 清理 / 债务判定 | Engineering Decision（判定携带理由） |
| 暴露变化执行（Authority / Observation / Proceed·Pause） | 归 SP-15 |
| 验证判定 | 归 SP-17 |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP16-01 代码 100% Deployed 且 Flag OFF 不得报告为
                     Feature 已 Launch——Deploy ≠ Release ≠ Launch 四分离
                     不得混用（Ch11 §2.5/§3、Ch7 §86、§137）
[MUST][BASELINE]    G-SP16-02 会 materially 改变用户行为的暴露变化（含扩大、
                     收缩、紧急 disable）必须作为 Target-changing Action 走
                     SP-15 的 Authority / Observation / Recovery 控制
                     （Ch7 §87、§114、§139）
[MUST][BASELINE]    G-SP16-03 Temporary Flag 必须有 Owner / Purpose /
                     Default / Launch Plan / Cleanup Condition 五要素登记
                     （Ch11 §41）
[MUST][BASELINE]    G-SP16-04 Flag 的存在不豁免验证与暴露控制——"可以随时
                     关掉"不构成跳过 Target Validation 或渐进暴露的理由
                     （Ch11 §41）
[MUST][BASELINE]    G-SP16-05 Exposure State 按真实粒度记录（per-Target /
                     Tenant / Cohort 的 State、percentage、distribution、
                     Stop 状态），Partial Exposure 不得压扁成单一 Boolean
                     （P2 Ch11 §70、GI-05）
[MUST][BASELINE]    G-SP16-06 Temporary Flag 的长期化必须显式判定并移交
                     （长期业务配置 → Configuration Contract：SP-09 定义 /
                     SP-07 演进；Kill switch → permanent 资产登记）——不得
                     无声永久化（Ch11 §41）
[MUST NOT][BASELINE] G-SP16-07 绕过 SP-15 直接执行暴露变化——本规程定义
                     语义与计划，执行控制（Authority Token / Slice /
                     Observation）归 SP-15（Ch7 §86-87、§114）
[MUST NOT][BASELINE] G-SP16-08 与 SP-05 / SP-09 互相覆盖——Flag 机制选择与
                     Transition 设计归 SP-05，Flag Config 单次发布要素归
                     SP-09，本规程管跨 Change 的暴露生命周期
[MUST NOT][BASELINE] G-SP16-09 无依据的 gate-zeroing——"无需 Flag 直接上线"、
                     "暴露变化不 material"、"内部工具无暴露面"归类必须
                     携带可解析理由，并可被 SP-05 / SP-13 / 组级审计再挑战
                     （B1）
```

---

# 7. PASS Exit

```text
Exposure / Launch Plan 成立（绑定 Feature 与交付事实）：
  暴露策略按风险裁剪（B1 理由成立）
+ 适用时：Flag 五要素登记齐全、渐进阶段与停止条件明确
+ Exposure State 事实粒度与观察面定义完整
+ 暴露执行移交 SP-15（Launch Plan + 暴露语义 + 恢复意图）
+ 适用时：清理 / 长期化 / 债务判定成文
→ 移交 SP-15（暴露执行）/ SP-17（暴露后验证）
```

完成**不代表**：Feature 已全量暴露 / Target Validation 通过（SP-17）/ 暴露过程中异常已恢复（SP-18）/ Flag 已清理 / Current 已更新（SP-19）。

---

# 8. Evidence

Evidence by Work：

```text
Exposure / Launch Plan（含渐进阶段与停止条件）
Flag Registry 条目（五要素）
Exposure State 观察面定义与采集事实（随 SP-15 编排产生）
暴露执行移交记录（Launch Plan 版本）
清理 / 长期化 / 债务判定记录
```

只有 gate-zeroing 归类理由（直接上线 / 不 material / 无暴露面）、长期化判定理由、永久 Kill switch 登记必须显式成文；其余证据随工作自然产生。

---

# 9. Current Update Obligation

本规程**不更新 Current**。Exposure State 是 Environment Current Runtime State 的组成部分，事实提交由 **SP-15** 在执行期编排（Authority 背书下随真实暴露事实更新，Ch7 §60-62）；Accepted Current Release 面归 SP-17；项目级 Current（含 Flag 清理带来的 Design / Structure 变化）归 **SP-19**，任何 Current Baseline 的正式迁移显式走 SP-19。

---

# 10. FAIL / Return Path

```text
暴露变化被 SP-15 判定需重授权（Basis 失效）→ 更新 Launch Plan 后重新移交
                                        （Ch7 §29-30 Revalidation）
暴露后验证 FAIL / NOT_READY           → SP-17 路径；需要恢复动作 → SP-18
暴露中需要新软件内容的修复            → SP-18 Recovery（Forward Fix 产生
                                        新软件内容回正常规程）；Kill switch
                                        类即时 disable 的执行仍走 SP-15
Cleanup Condition 无法满足（Old Code
Path 仍被依赖）                       → Flag Debt 登记 + 移交 SP-05 设计
                                        移除路径；不得无声搁置
长期化触发跨边界承诺演进              → 移交 SP-07（携带事实输入）
Material 设计问题（暴露策略无法成立） → SP-05
```

---

# 11. Exception / Alternative Path

## 11.1 无 Flag 基础设施

没有 Feature Flag Platform 的项目（第三篇 Ch6 §49：Flag Platform 只是外部能力承载，不改变语义），暴露控制可用版本化 Config 值 / 发布通道 / 环境级开关实现；五要素登记与"何时开始产生用户影响"的可回答性不豁免。全部 All-at-once 暴露的归类携带理由（B1）。

## 11.2 永久 Kill Switch / 安全开关

长期存在的 Kill switch / Safety Flag 是合法 permanent 资产：显式判定为 permanent（Owner + 触发条件 + 定期演练），登记于 Flag Registry，不算 Flag Debt，也不得伪装成 Temporary Flag 逃避登记（§41 的长期化判定同样适用——它不是长期业务配置，是运行安全控制；演练归 SP-18 Recovery 演练面）。

## 11.3 事故中的紧急 Disable

事故中紧急关闭 Flag 的执行仍走 SP-15 Target-changing Action 控制（Authority Token 约束 feature disable，Ch7 §114）；Emergency Change 语义（压缩执行与事后对账）归 SP-21 / Ch8 正文。本规程提供 Kill switch 资产与意图，不在本规程内发明绕过通道。

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05 / GI-13；Deployed ≠ Launched 是 GI-05 的直接应用

Part II:
Ch11 §2.5（Launch / Enable 与四分离）、§3（为什么区分 Deploy 与 Release）、
  §36-42（Rollout 策略按风险 / Canary / 渐进停止条件 / Feature Flag §40 /
  Flag 非免费消除器 §41 / Config Change 是 Release §42）、
  §68-70（复杂 Rollout 状态 / Partial 识别 / Canary 可观察）
Ch12 §14（Additive Maintenance：交付后新增 Feature 的暴露语境）

Part III:
Ch3 §31（Flag 是 Runtime Behavior 决定因素，Mapping 追到 Flag Reference）、
  §42-44（Mixed / Target / Transition Runtime Structure）、
  §71.7（服从第二篇 Build / Release 基线，不重定义交付语义）
Ch6 §49（Feature Flag Platform 是外部能力承载，不入结构主模型）
Drift 章 §61（Flag 是 Observation 误判的解释来源之一）

Part IV:
Ch7 §46-59（Rollout / Slice / Signal Attribution / Representativeness /
  Proceed / Pause / Concurrent）、§86-87（Launch / Feature Exposure 分离、
  Feature Exposure Change）、§88（Client 同类语义）、§114-116（Authority
  Token 约束 feature disable / traffic revert / Outdated Attempt）、
  §137（Feature Flag 反例）、§139（Minimum Requirements 暴露相关条）

Journey:
JG-07 部署后验证、扩大暴露或恢复（SP-15 → SP-16 → SP-17；异常 SP-18；
完成 SP-19）
```

---

# 13. Executable Asset References

```text
EA-14 Feature Exposure       flag config / rollout config 的 state + owner +
                             cleanup 证据面
EA-15 Observability          暴露面信号 instrumentation（percentage /
                             distribution / business signal 按 Slice 归因）
```

工具适合：Flag Registry 维护、暴露状态采集、percentage / distribution 观察面板、Cleanup Condition 到期提醒。
工具不适合：暴露策略选择、materially 判定、长期化判定、债务处置——"Flag 平台显示已 ON"不是 Launch 语义判定器（GI-07）。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Flag = 版本化 Config 定义的 flag 项 + 平台注入（Reference 可追踪）；
  暴露变化走 SP-15 受控链（与 Binary Release 同链）；观察面 = per-slice
  metrics（error / latency / business signal）

RP-B-CLI（pending-definition，组6）:
  无服务端 Flag——Launch = Distribution 到达（Channel / Cohort 分阶段）；
  Version Exposure / Adoption Observation 承载暴露语义；Kill switch 能力
  受限（安装后无远程开关的形态显式登记）

RP-C-SDK（pending-definition，组6）:
  无运行时 Flag——Launch = Consumer 升级采用；暴露面 = Adoption /
  版本分布观察；兼容策略（Old Consumer 必须工作）在发布前由 SP-07 /
  SP-05 保证
```

---

# 15. Example

**CHG-WO-142（工单转派能力升级）的暴露面——reason 能力的 Launch。**（承接组3 SP-15 / SP-17 示例与组4 SP-07 / SP-08 / SP-09 / SP-10 示例：WO-1.9.0 已含 reason 代码并完成 canary 验证（SP-15 D1 / SP-17 示例）；C9 Event 加 reason 为 optional（SP-07 判定）、V203 Migration 已执行（SP-08）、Config Schema 允许值清单已定（SP-09 A7）。本例覆盖 Flag 门控 Launch 的暴露生命周期。）

```text
A1 入口：reason 能力已随 WO-1.9.0 部署但默认不暴露——交付事实（SP-15）：
   Production 100% 运行新代码，旧行为路径仍为默认。暴露对象 = TransferReason
   能力；暴露维度 = Partner + Tenant（面向外部 Consumer，Ch7 §48）
A2 暴露策略：高影响（Partner-facing Event 变化）→ Progressive Exposure
   0%→5%→20%→100%（Ch11 §40 原生例子）；各阶段停止条件 = Event 发布成功率
   阈值 / Partner 消费错误率 / 消息积压；观察信号按 Slice 归因（Ch7 §53）
   ——Launch Plan 成文
A3 Flag 登记：flag = workorder.transfer_reason，五要素——Owner =
   work-order-service 团队；Purpose = 解耦 Binary 部署与 reason Launch、
   限制 Partner 侧消化风险；Default = OFF（fail-safe）；Launch Plan =
   A2 阶段表；Cleanup Condition = 100% 暴露 + Partner 确认消费正常 +
   一个 Release 周期后移除 Flag 与无 reason 旧代码路径
A4 Exposure State：per-Partner / per-Tenant 的 Flag State + 当前 percentage
   入 Environment Current Runtime State（SP-15 执行期提交）；观察面板 =
   reason 载荷发布率 / Partner 消费错误率按 Slice 维度（EA-15）
A5 执行移交：0%→5% 首次翻转作为 Target-changing Action 移交 SP-15
   （Authority Token 确认 + Rollout Slice S + Observation）；紧急 disable
   的意图（触发条件）随移交包登记——执行仍受 Authority Token 约束
   （Ch7 §114）；暴露后行为验证 Concern 归 SP-17
A6 长期化判定：reason 的 category 允许值清单已是 Config Schema（SP-09 A7
   移交 SP-07 的事实），但 Flag 本身判为 Temporary——不长期化；Cleanup
   Condition 触发后走正常 Change（SP-03）移除 Flag 与旧路径。若后续判定
   需要长期业务开关 → 进入正式 Configuration Contract（SP-09 定义 /
   SP-07 演进）
A7 债务巡检：Registry 中另发现 flag workorder.bulk_export 已 8 个月无
   Owner 且永久 ON（历史 Change 遗留）→ 登记 Flag Debt（Risk = Old Code
   Path + Test Combination / Owner = 待认领 / Cleanup Condition = 下一
   维护周期评估移除路径，必要时移交 SP-05）——与 Ch12 §7 Maintenance
   Input 巡检衔接
```

---

# 16. 最终原则

> **Deployment 是工程事实，Launch 是用户事实：代码上线的那一刻用户什么都没得到，Flag 打开的那一刻工程才开始承担用户影响。Flag 的价值不是让发布不需要勇气，而是让暴露可以一寸一寸地给；它的代价是每一个 ON 都是一份没有还清的债——有 Owner、有退出条件，Flag 才是控制；没有，它只是延迟爆炸的配置漂移。**
