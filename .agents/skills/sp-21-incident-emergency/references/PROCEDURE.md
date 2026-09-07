# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-21 Incident / Emergency

> 类型：Specialized Procedure  
> 状态：SEALED（2026-09-01：组5 Independent Concept Audit PASS AFTER REPAIR（P1×2 已修复）+ 横向回归全量引用核验 PASS；证据见组5 审计报告与横向回归报告）  
> 单一职责：把一次线上 Incident / 高紧迫事件组织成受控的 Emergency 工程事实——开立 Incident Record 并判定 Emergency（真实损害正在持续或扩大），确立 Emergency Mitigation Objective，记录 Emergency Compression Profile（哪些义务被压缩 / 替代 / 延后、被谁接受），固化最小不可消失事实与 Action Trace，形成 Emergency Stabilization Fact，并在稳定后执行 Emergency Reconciliation（Deferred Obligation 逐项处置、Successor 判定、Ch9 输入准备）。核心事实为 Emergency Record。  
> Emergency = 同一 Change Model + 压缩的前置深度 + 强制的事后对账；Stabilized ≠ Fixed；Deferred ≠ Waived；Evidence Gap 不得改写成 PASS。  
> 结构化镜像：`第五篇-SP21-IncidentEmergency-OperationContract.yaml`

---

# 1. Trigger

```text
A. Incident 发生 / 接收：告警、用户报告、安全漏洞发现、数据问题、
   依赖断裂等高紧迫事件 → 开立 Incident Record 并作 Emergency 判定
   （P4 Ch8 §8 判定标准；P2 Ch12 §3 三类动作边界）
B. Emergency Change 压缩执行：Mitigation Objective 确立、Compression
   Profile 记录、极端事故下先行动后补 Record（§9-16）
C. Emergency Reconciliation：稳定后的补充核查与正式处置——Deferred
   Obligation 逐项处置、Temporary Exception 退出、Successor 判定、
   Ch9 / SP-19 输入准备（§22-25）
D. Incident Follow-up：Postmortem（按影响规模裁剪）、可执行 Action
   Item、复发风险与学习保留（P2 §24-26）
   ——JG-08 主线：SP-21 → SP-18 Recovery / Stabilization → SP-17
   Validation → SP-19 Reconciliation / Current；永久修复 → SP-03
```

红线：**Emergency 不是"高优先级需求"的别名**（§8）——判断标准只有一条：继续等待完整正常前置流程，会让当前真实损害、风险或关键不可用状态显著持续或扩大；**Emergency Compression 必须显式记录**（§11 [BASELINE]）——"当时很急"几周后不能成为义务消失的理由。

不触发本规程的情形：

```text
Recovery / Stabilization 动作的执行（Rollback / Rollforward /
  Disable / Restore / Compensation / Traffic Shift）→ SP-18
  （本规程定义 Mitigation Objective 并移交执行）
Target Validation 判定                    → SP-17
Emergency 动作的执行控制（Authority Token /
  Target-changing Action）                → SP-15（本规程在其框架内
  组织压缩 Change）
Emergency 中的 Flag / Kill switch 资产语义 → SP-16（disable feature 的
  资产与意图；执行走 SP-15 + SP-18）
永久修复的实现与验证                      → SP-06 / SP-13（正常链），
  经本规程 Reconciliation 路由
维护期语境的 Emergency 后续义务挂账
  （Follow-up Owner / 容量 / 优先级）      → SP-20（§76.2 的登记面；
  本规程管 Emergency Change 自身的 Reconciliation）
Current 更新 / Closure 判定               → SP-19（Ch9；本规程只准备
  Ch9 输入，不提前把"已识别待校准"写成"已完成 Calibration"，§22）
普通高优先级需求 / 客户催促 / 老板要求    → 不构成 Emergency，走正常
  Change 链（SP-03 起）
```

---

# 2. 输入

```text
Incident 信号                       告警 / 用户报告 / 安全 Advisory /
                                    数据校验异常 / 依赖方通知（EA-15 面）
运行与暴露事实                       SP-15：Environment Current Runtime
                                    State、Rollout Slice 现状；SP-16：
                                    Flag / Kill switch 资产现状
Recovery 资产事实（适用）             SP-18：Anchor / 修复脚本 / 演练
                                    状态（压缩路径下"rollback path
                                    checked"的依据）
受影响面事实                         受损用户 / 数据 / 安全边界 / 合规
                                    面的即时可判事实（partial but
                                    sufficient for mitigation，§107）
现行 Change 上下文（适用）             相关 OPEN Change、最近 Release /
                                    Rollout 事实（Incident 归因输入）
```

入口再挑战义务（B1 系统性规则）：使 Gate 归零的归类——"这个不算 Emergency 直接走正常流程"、"先修了再说不用记录"、"内部事故不需要 Postmortem"、"反正已恢复可以关闭"——必须携带可解析理由；没有理由或理由不成立的，按本规程对应 Trigger 处置。

---

# 3. 输出

```text
Incident Record                    INC 编号 + 触发事实 + 时间线 +
                                   Severity / Priority 判定（P2 §21-22）
Emergency 判定 + Change 绑定        Emergency / 非 Emergency 判定依据；
                                   Emergency Change 用同一 Change
                                   Identity 开立（§7：Same Change Model）
Emergency Mitigation Objective     现在最先必须让什么危险停止（§9）
Emergency Compression Profile      七要素：normal obligation / current
                                   status / why compressed / temporary
                                   substitute / risk accepted by whom /
                                   must-do-after stabilization / owner
                                   （§11）
Emergency Action Trace + 最小
  不可消失事实                       §15 八问 + §13 九项——极端事故下
                                   先行动后补 Record 的 Operational Trace
Emergency Stabilization Fact       Mitigation Objective 经即时 Evidence
                                   达成的稳定事实（§16）——不含
                                   "已修复"语义
Emergency Deferred Obligation
  清单                              被压缩 / 延后且必须事后处置的义务
                                   逐项（§18）
Emergency Reconciliation 产物       §22 十项：实际修改重建 / Impact 补
  全 / Design 确认 / 验证补齐 /
  Runtime·Data 核查 / 临时面复查 /
  Exception 处置 / Postmortem 链接 /
  永久修复或 Successor / Ch9 输入
Postmortem / Follow-up              Action Item（Owner + Priority +
  可验证结束状态）+ 复发风险登记
  （P2 §24-26）；维护侧挂账移交 SP-20
```

本规程**不输出**：

```text
Recovery 手段执行                    → SP-18
Validation 判定                      → SP-17
执行控制（Authority Token）           → SP-15
永久修复实现 / 验证                  → SP-06 / SP-13
Calibration / Scoped Current Update /
  Closure                            → SP-19（Ch9）
维护期后续义务登记面                  → SP-20
```

---

# 4. 核心语义

**Emergency = 同一模型 + 压缩深度 + 强制对账（§7 [BASELINE]）**：Emergency Change 使用同一个 Engineering Change Identity、Change Record、Baseline、Authority、Evidence 与后续 Reconciliation 模型——压缩的是前置分析 / 设计 / 验证**深度**与**时点**，不是模型本身。可以裁剪 Design Depth / Review Depth / Pre-release Test / Approval；不可删除 Change Identity / Owner / Reason / Actual Modification / Verification / Deployment Record / Follow-up（P2 §19）。

**三类动作的边界（P2 §3）**：Incident Response 与 Operational Mitigation（用既有运行能力处置：重启、限流、切流、关 Flag——不改变软件，是 Operation）≠ Emergency Maintenance（修改 Maintained Software 的紧急受控修改，走本规程压缩 Change）≠ 正常 Maintenance。不改变软件的缓解动作留在运行域——其中重启 / 限流等不改变用户可见行为的按运行域既有规则执行并进 Action Trace，切流 / 关 Flag 等 materially 改变用户行为的仍是 Target-changing Action、走 SP-15 控制（Ch7 §87、§114，Flag 资产语义归 SP-16）；但**产生用户可见影响的每个 Material 动作都要进 Action Trace**；一旦决定改软件，立即进入压缩 Change Loop。

**Mitigation ≠ Root Cause Fix（§9-10）**：Mitigation Objective 回答"现在最先必须让什么危险停止"，不回答"永久方案长什么样"。因此 Service Restored ≠ Permanent Fix ≠ Verification Complete ≠ Change Completed（§10）——Stabilization Fact 只是"影响已控制到可接受临时状态"的 Engineering Progress Fact（§16），Change 仍 OPEN + ACTIVE / PAUSED（§17）。

**Compression Profile 区分 deferred 与 waived（§11-12、§19）**：没有 Profile，"Emergency"几周后就变成永久免责理由——团队只记得"当时很急"，不知道 Impact 哪部分没做、哪些 Test 没跑、哪个 Exception 仍有效。**Deferred = later，不是 no longer required**；真要 Waive 必须有明确 Authority / 理由 / 风险 / Scope / 必要时 Expiry（§19），不能只写 "because emergency"。

**最小不可消失事实与先行动后补记录（§13-15）**：即使极端事故，Change Identity / Owner / Trigger Reference / Affected Scope / Actual Modification / Action Authority / Immediate Validation / Recovery Direction / Deferred Obligation 原则上不能永久消失。用户正在持续受损而完整填写 Record 会直接延误安全 Mitigation 时，允许先执行最小安全动作——但保留同时发生的 Operational Trace（who / when / what target / what command-artifact-config / observed result / incident reference），可行后立即绑定稳定 Change Identity（§14）。**这不是允许无记录永久修改 Production。**

**Evidence Gap 不得改写成 PASS（§21）**：Emergency 可以改变何时完成验证、验证前允许什么受控动作、谁接受临时风险；不能改变真实 Evidence Result。没跑的 Security Regression 的正确表达是 NOT_READY / Evidence Gap / Deferred Obligation / Authorized Exception——不是 "PASS because emergency"。

**Reconciliation 与关闭屏障（§22-25）**：稳定后对实际修改、影响范围、Design / Authority 偏差、Required Verification、Runtime / Data State、Deferred Obligation、Temporary Mitigation 与 Current Baseline 补充核查并正式处置。**Reconciliation Barrier**：只要存在未明确处置的 Deferred Obligation / Temporary Mitigation / Evidence Gap / Unreconciled Modification / Current-Calibration Obligation，不得 CLOSED + COMPLETED（§24 [BASELINE]）。永久修复可留在同一 Change（同一清晰 Intent）或建 Successor（演化为新架构 / 新长期 Scope / 新 Owner / 独立 Delivery Boundary 时，§23）——Transfer 必须由 Successor 可追接受。正式 Calibration 与 Closure 归 Ch9 / SP-19。

**Follow-up 产生可执行动作（P2 §24-26）**：高价值 Action Item 有 Owner、Priority 与可验证结束状态——"以后注意 / 加强测试 / 加强监控"不是 Action。Postmortem 规模按影响裁剪（重大用户影响 / 数据安全事件 / 重复故障 / 意外故障模式才需要完整版，小型已知问题 Incident Note 即可）；**Blameless 不是无责任**——分析系统、流程、信息与条件怎样共同造成 Incident，同时保留 Action Owner / Priority / Due / 可验证结束状态的 Accountability。复发风险与重要学习不能消失。

---

# 5. Engineering Actions

## A1 — Incident 接收与 Emergency 判定

开立 Incident Record（INC + 触发事实 + 时间线），区分 **Severity**（后果多严重）与 **Priority**（多快处理——受 Customer Impact / Security / Workaround / Frequency / Cost of Delay 影响，高 Severity 不必然立即 Code Change，P2 §21）；Triage 至少看 User Impact / Data / Security / Blast Radius / Workaround / Recovery Cost 等（P2 §22）。Emergency 判定用 §8 标准成文；不成立的走正常 Change 链（SP-03 起），Incident 记录仍保留。

## A2 — Mitigation Objective 确立

明确"现在最先必须让什么危险停止"（stop duplicate charge / stop data loss / restore login / disable vulnerable endpoint，§9），并区分 Symptom / Immediate Cause / Contributing Factor / Latent Design Problem（P2 §23）——Mitigation 面向 Objective，不面向永久方案；根因分层留给 Reconciliation 与 Follow-up。

## A3 — Compression Profile 记录

按七要素逐项记录：哪些正常义务已满足、哪些被压缩、为什么、用了什么临时替代、风险被谁接受、稳定后必须补什么、Owner（§11）。"Emergency, skip tests"式记录违规——profile 的作用就是把 temporarily deferred 与 permanently waived 区分开（§12）。

## A4 — 稳定动作执行与路由

把 Mitigation 动作路由到正确的执行域：恢复类手段（Rollback / Rollforward / Disable Feature / Restore / Compensation / Traffic Shift）→ **SP-18**（JG-08）；不改变软件的运行域缓解按行为影响分流——重启 / 限流等不改变用户可见行为的按运行域既有规则执行、进 Action Trace（A5），切流 / 关 Flag 等 materially 改变用户行为的作为 Target-changing Action 走 SP-15 控制 + SP-16 资产语义（Ch7 §87、§114）；需要新软件内容的紧急修改 → 压缩 Change：实现 SP-06 / 验证 SP-13 的压缩时点 + 强制后补（Reconciliation 持有义务）。Hotfix 必须知道自己基于哪个 Release（Affected Release / Fix Source / Target Release / Forward-port or Backport / Compatibility，P2 §20）——不明确就 cherry-pick main 会制造新 Drift。Target-changing 动作仍受 SP-15 Authority Token 约束。

## A5 — Action Trace 与最小事实固化

每个 Material Emergency Action 可回答 §15 八问（谁 / 何时 / 哪个 Target / 什么动作 / 哪个 Artifact·Config·Command / 动作前观察 / 动作后观察 / 持久 Side Effect）；执行系统有不可变 Audit Log 的可引用不复制。极端事故下先行动后补 Record 的，Operational Trace 同步留存、事后立即绑定 Change Identity（§13-14）。

## A6 — Stabilization Fact 形成与状态语义

Mitigation Objective 经适用即时 Evidence 达成（duplicate stops / core flow works / error rate stable）→ 形成Emergency Stabilization Fact（§16）。如实表达状态：Stabilized ≠ Fixed（§17），Change 保持 OPEN + ACTIVE / PAUSED；Evidence Gap 表达为 NOT_READY / Deferred，不改写 PASS（§21）。恢复动作的验证事实由 SP-18 采集、SP-17 判定。

## A7 — Emergency Reconciliation

稳定后执行 §22 十项：重建实际修改、补全 Impact、确认 / 修订 Design、补齐 Required Verification、核查 Runtime / Data State、复查临时 Config·Flag、处置 Exception、链接 Postmortem、开立永久修复或 Successor、识别 Calibration / Current-Update 义务并**准备 Ch9 输入**（不提前写"已完成 Calibration"）。Reconciliation Barrier 检查（§24）+ Closure 前最低五问（§25）通过后移交 SP-19；Successor 路径（§23）：已完成什么 / 转移什么 / Successor 是谁 / 是否接受。

## A8 — Postmortem 与 Follow-up

按影响裁剪 Postmortem 规模（P2 §25）；Action Item 落成 Owner + Priority + 可验证结束状态（P2 §24）；Blameless 分析系统条件而非责备个人，同时保留 Accountability（P2 §26）；重复 Incident 的累计成本进入维护优先级信号（P2 §62，SP-20 域）；Follow-up 挂账移交 SP-20 维护周期；永久修复 Change 经 SP-03 开立。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Action Trace 采集 / Audit Log 引用 / 时间线维护 | Automation（EA-15） |
| Incident Record / Compression Profile / Deferred 清单维护 | Automation-assisted |
| Emergency 判定 / Severity·Priority | Engineering Decision |
| Mitigation Objective / Reconciliation / Successor 判定 | Engineering Decision |
| 稳定动作执行 | 归 SP-18（手段）/ SP-15（控制）|
| Validation 判定 | 归 SP-17 |
| Calibration / Closure | 归 SP-19 |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP21-01 Emergency 必须继续使用同一 Change Identity /
                     Baseline / Evidence / Authority 模型——不创建第二套
                     State Machine、不逃离工程流程（§7、P2 §19、§131）
[MUST][BASELINE]    G-SP21-02 Emergency 判定必须有 §8 标准依据（等待完整
                     流程会使真实损害显著持续或扩大）——"高优先级需求"、
                     "客户催"、"老板要求"不构成 Emergency（§8）
[MUST][BASELINE]    G-SP21-03 Emergency Compression 必须显式记录被压缩、
                     替代或延后的 Engineering Obligation（七要素 Profile，
                     §11-12、§131）
[MUST][BASELINE]    G-SP21-04 极端事故先行动后补 Record 时必须保留可重建
                     的 Operational Trace 并尽快绑定稳定 Change Identity
                     （§13-15、§131）——不允许无记录永久修改 Production
[MUST][BASELINE]    G-SP21-05 Emergency Stabilization ≠ Permanent Fix ≠
                     Verification Complete ≠ Change Closure（§10、§16-17）
[MUST][BASELINE]    G-SP21-06 Deferred Obligation 不得仅以 "Emergency" 为
                     理由永久 Waive——Waive 需明确 Authority / 理由 / 风险 /
                     Scope / 必要时 Expiry（§18-19、§131）；Temporary
                     Exception 必须有 Owner / Scope / Exit or Expiry /
                     Recheck（§20）
[MUST][BASELINE]    G-SP21-07 Emergency Evidence Gap 不得改写为 PASS——
                     正确表达是 NOT_READY / Evidence Gap / Deferred
                     Obligation / Authorized Exception（§21、§131）
[MUST][BASELINE]    G-SP21-08 Emergency 事后必须完成 Reconciliation 或把
                     剩余义务显式转给已接受 Successor；Reconciliation
                     Barrier 未满足不得 CLOSED + COMPLETED（§22-24、§131）
[MUST NOT][BASELINE] G-SP21-09 无依据的 gate-zeroing——"不算 Emergency 直接
                     修"、"先修了不用记录"、"内部事故不用复盘"、"已恢复
                     即可关闭"归类必须携带可解析理由，并可被 SP-05 / SP-13 /
                     组级审计再挑战（B1）
```

---

# 7. PASS Exit

```text
Incident / Emergency 义务完成（绑定 INC 与 Emergency Change）：
  Mitigation Objective 达成且 Stabilization Fact 成立即时 Evidence 在案
+ Compression Profile 与 Action Trace 完整（或已绑定稳定 Identity）
+ Reconciliation 完成：Deferred Obligation 逐项完成 / 转移（Successor
  已接受）/ 正式处置；Temporary Exception 已退出或移交治理
+ Follow-up Action Item 成文（Owner + Priority + 可验证结束状态），
  维护侧挂账移交 SP-20
+ Ch9 输入准备就绪 → 移交 SP-19（Calibration / Closure）
```

完成**不代表**：永久修复已交付（SP-03 / SP-06 / SP-13 正常链）/ Recovery 已执行（SP-18）/ Validation 已判定（SP-17）/ Change 已 Closure（SP-19）/ Follow-up Action 已全部完成（挂账追踪）。

---

# 8. Evidence

Evidence by Work：

```text
Incident Record（触发事实 + 时间线 + Severity / Priority）
Emergency 判定依据（§8 标准成文）
Emergency Compression Profile（七要素）
Emergency Action Trace（§15 八问 / Audit Log 引用）
Emergency Stabilization Fact（即时 Evidence）
Emergency Deferred Obligation 清单与逐项处置记录
Temporary Exception 登记与退出记录
Emergency Reconciliation 产物（含 Successor Transfer 与接受事实）
Postmortem / Incident Note + Action Item（Owner + Priority + 可验证
  结束状态）
```

只有 gate-zeroing 归类理由（不算 Emergency / 不用记录 / 不用复盘 / 已恢复即关）、Waive 决定（Authority + 理由 + 风险 + Scope）、Successor Transfer 决定必须显式成文；其余证据随工作自然产生。

---

# 9. Current Update Obligation

本规程**不写 Current**。Emergency 期间的 Runtime State 事实由 SP-15 执行期提交；Reconciliation 识别出的 Calibration / Current-Update Obligation 作为 **Ch9 输入**移交 SP-19（§22 明确：本章不得提前把"已识别待校准"写成"已完成 Calibration"）；Incident 学习引发的设计 / 结构修订归 SP-19 / SP-05。

---

# 10. FAIL / Return Path

```text
Mitigation 动作无法达成 Objective      → 换手段（SP-18 候选重选）/
                                         升级 Incident 等级与响应面
稳定后验证不通过                        → SP-17 路径 + 新 Recovery
                                         Attempt（SP-18）；Evidence Gap
                                         如实登记，不改写 PASS
Deferred Obligation 无人认领            → 升级项目 Owner；不得静默 Waive
永久修复演化为新架构 / 新长期 Scope     → Successor Change（§23），
                                         Transfer 须 Successor 可追接受
Incident 根因指向 Material 设计问题     → SP-05（经永久修复 Change）
根因指向维护期风险面（依赖 / EOL / 债务）→ SP-20（挂账与容量处置）
恢复物质基础缺失（Anchor 失效 / 无备份） → SP-18 Forward Fix 路径 +
                                         SP-20 Retention 改进登记
Reconciliation 发现实际修改与记录不符   → 重建事实优先（§22 reconstruct
                                         actual change），差异进入
                                         Evidence Gap 处置
```

---

# 11. Exception / Alternative Path

## 11.1 极端事故：先行动后补 Record

用户持续受损 / 服务持续不可用 / 数据持续损坏 / 安全暴露扩大，且完整填写 Record 会直接延误安全 Mitigation 时，允许先执行最小安全动作——Operational Trace 同步留存，事后立即绑定 Change Identity（§14）。边界不变：不允许无记录永久修改 Production。

## 11.2 Temporary Emergency Exception

临时引入的 auth bypass / disabled validation / manual operation / temporary flag / reduced redundancy 必须有 Owner / Scope / Risk / Expiry or Exit Condition / Recheck Trigger（§20）——否则临时措施无声变成永久架构。临时 Flag 的资产语义归 SP-16，退出治理在 Reconciliation 复查。

## 11.3 小型已知问题

不需要完整 Postmortem 的（无重大用户影响 / 非数据安全事件 / 首次且已理解），Incident Note + Root Cause + Fix / Follow-up 即可（P2 §25）——复发风险与重要学习不能消失；同类问题复发时升级为完整 Postmortem。

## 11.4 Successor 拆分

永久修复演化为新架构 / 新长期 Scope / 新 Owner / 独立 Delivery Boundary 时建 Successor Change（§23、§110）；原 Emergency Change 明确已完成 / 转移内容与 Successor 接受事实后，方可进入自身 Closure。

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05 / GI-06 / GI-13（Evidence Gap ≠ PASS 是 GI-06 直接应用；
  最小不可消失事实是 GI-05 真实状态义务的极端场景下限）

Part II:
Ch12 §3（Incident Response / Operational Mitigation / Emergency
  Maintenance 三类边界——本规程 Trigger A 的判定基础）、§18-26
  （Emergency Maintenance 非最终 Closure / 非逃离流程许可证 / Hotfix
  基线 / Severity vs Priority / Triage / Symptom-Fault-RootCause /
  Follow-up Action / Postmortem 裁剪 / Blameless）、§56-57（Workaround
  / Temporary Mitigation 的 Owner 与退出条件）、§62（Repeated Incident）

Part III:
Ch3 Runtime / Deployment 面：Mixed / Recovering State 真实表达（§42、
  §60-64）——事故中系统状态不被压扁；Recovery Runbook 不可用反例
  （§67：结构状态未分开表达所致）；Ch8 Current / Drift（§61：Current
  结构是事故后重建工程事实的锚点）

Part IV:
Ch8 §7-25——Emergency 核心语义（§7 定义、§8 判定、§9 Mitigation
  Objective、§10 ≠链、§11-12 Compression Profile、§13-15 最小事实与
  Trace、§16-17 Stabilization、§18-19 Deferred≠Waived、§20 Exception
  退出、§21 Evidence Gap、§22-25 Reconciliation 与 Barrier）；
  §105-110（WorkOrder：INC-77 + CHG-WO-E17 Emergency 实例）；
  §131-134（Minimum Requirements Emergency 条 + 推荐最小字段）；
  Ch9 接口（§25 Closure 前最低判断的下游）

Journey:
JG-08 处理线上 Incident / Emergency：SP-21 → SP-18 Recovery /
  Stabilization → SP-17 Validation → SP-19 Reconciliation / Current；
  永久修复 → SP-03 normal / successor Change
```

---

# 13. Executable Asset References

```text
EA-15 Observability          Incident 信号面（告警 / error rate /
                             critical flow）与 Stabilization 即时
                             Evidence 采集
EA-16 Recovery               Mitigation 手段的物质基础（rollback /
                             disable / repair 脚本——执行归 SP-18，
                             本规程消费其就绪事实）
```

工具适合：Incident Record / Timeline / Compression Profile / Deferred 清单维护、Action Trace 与 Audit Log 引用、告警信号采集。
工具不适合：Emergency 判定、Mitigation Objective 选择、Reconciliation / Successor 判定、Waive 决定、Postmortem 分析——"监控已恢复绿"不是 Stabilization 判定器，工具输出是 Signal 不是判定（GI-07）。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Incident 链 = 告警（EA-15）→ Incident Record（issue tracker）→
  Emergency Change（同一 Record 体系）；Action Trace = 部署平台
  Audit Log + GitOps commit 引用；Postmortem = 文档 + Action Item
  issue 化（Owner / Due / 可验证结束状态）

RP-B-CLI（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组6）:
  Emergency 影响 = 已分发副本（无法远程止血）——Mitigation 面收窄为
  停止分发 / 公告 + 快速 patch 版本；Kill switch 能力受限的形态在
  SP-16 已显式登记，此处按登记事实裁剪 Mitigation 手段

RP-C-SDK（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组6）:
  Consumer 侧 Incident = 兼容性断裂面——Mitigation = patch 版本 +
  迁移指引发布；已发布版本不可撤回，Reconciliation 的 Deferred 面
  含 Consumer 迁移进度跟踪
```

---

# 15. Example

**INC-77：WO-1.9.0 上线后的重复通知事故——Emergency 全生命周期。**（承接组5 SP-16 示例：reason 能力已渐进暴露中；P4 Ch8 §105-110 原生实例，本例展开为 SP-21 动作链。）

```text
A1 接收与判定：Production-US 告警——transfer action 触发 duplicate
   notification、用户影响持续（EA-15 信号）。开立 INC-77；判定：
   等待完整正常流程会使损害持续扩大 → Emergency 成立（§8 依据成文）；
   Emergency Change CHG-WO-E17 用同一 Change Identity 开立。
   Severity = 高（用户可见错误通知）；Priority = 立即（无 Workaround
   可用）——二者分开记录（P2 §21）
A2 Mitigation Objective：stop duplicate notification while keeping
   core transfer available——不回答永久方案，只回答"先让什么危险
   停止"（§9）
A3 Compression Profile：full root cause → deferred；full
   architecture review → deferred；full regression → deferred；
   immediate impact → partial but sufficient；rollback path →
   checked（SP-18 资产事实）；critical smoke → required now。
   Owner 记录 now / later 分界——不是 "Emergency, skip tests"（§107）
A4 执行路由：最快安全动作 = disable new notification path（不改软件
   的 Flag disable：资产 = SP-16 Kill switch 类资产，执行 =
   SP-15 Target-changing Action 控制 + SP-18 disable-feature 手段）；
   不在事故压力下重构 Notification Architecture
A5 Trace：disable 动作八问在案（谁执行 / 何时 / Production-US /
   flag flip / 动作前后 error rate 对比 / 无持久 Side Effect）；
   Audit Log 引用不复制（§15）
A6 Stabilization：duplicate stops + core transfer works + error
   rate stable → Emergency Stabilization Fact（§16）。状态如实：
   Stabilized ≠ Fixed——CHG-WO-E17 保持 OPEN + ACTIVE（§17）；
   未跑的 full regression = Deferred，不改写 PASS（§21）
A7 Reconciliation：稳定后十项——根因 = notification race（Symptom /
   Cause 分层，P2 §23）；Deferred 清单 = root cause / full impact /
   permanent design fix / regression verification / remove
   temporary flag / calibration（§109）；Barrier 检查通过前不得
   CLOSED + COMPLETED（§24）；永久修复若只是 same notification race
   fix → 留在 E17 走 SP-06 / SP-13 补齐；若演化为独立 Notification
   Service 重构 → 建 Successor CHG-WO-E18，Transfer 须 E18 可追接受
   （§110）；Ch9 输入（calibration / current-update 义务清单）准备
   就绪移交 SP-19
A8 Follow-up：Postmortem（重大用户影响 → 完整版，P2 §25）；Action
   Item = add notification idempotency guard，Owner = work-order-
   service，Done when = load test + production metric confirms
   duplicate rate = 0（P2 §24）——不是"加强监控"；重复通知的复发
   风险登记进入 SP-20 维护周期信号（P2 §62）；temporary flag 的移除
   与 SP-16 Cleanup Condition 衔接
```

---

# 16. 最终原则

> **Emergency 压缩的是时间，不是真相：模型一个不变、义务一个不少、对账一次不缺。恢复服务只是让危险停下来，找到根因才让教训值钱，而补完对账才让这次事故真正结束。最危险的事故不是损失最大的那次，是几个月后没人说得清当时到底改了什么、欠着什么、谁接受的——每一份"当时很急"，都要有一份后来补齐的账。**
