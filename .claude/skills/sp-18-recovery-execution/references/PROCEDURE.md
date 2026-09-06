# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-18 Recovery Execution

> 类型：Specialized Procedure  
> 状态：SEALED（2026-09-01：组5 Independent Concept Audit PASS AFTER REPAIR（P1×2 已修复）+ 横向回归全量引用核验 PASS；证据见组5 审计报告与横向回归报告）  
> 单一职责：把一次需要恢复的交付 / 运行失败，受控地执行到明确、安全、可验证的目标状态——基于 SP-15 提供的 Trigger / Decision 输入 / Anchor 核验作出 Recovery Decision，选择并执行恢复手段（Rollback / Rollforward / Disable Feature / Restore Data / Compensation / Traffic Shift / Failover / Pause），开立 Recovery Attempt 执行记录，维护修复脚本与恢复演练资产，并把 Recovery Validation 判定移交 SP-17。本规程落地后正式承接此前由 SP-15 代行的 Recovery 执行记录义务（Ch7 §89-102）。  
> Recovery ≠ Rollback；Recovery Command SUCCESS ≠ Recovery Complete；Recovery Anchor 必须在依赖它之前真实存在；失败 Attempt / Partial State / Recovery 都是历史工程事实，不得删除。  
> 结构化镜像：`第五篇-SP18-RecoveryExecution-OperationContract.yaml`

---

# 1. Trigger

```text
A. 交付循环内恢复：SP-15 判定 Proceed = STOP / Target Validation FAIL /
   Transition Invariant 破 / Canary 坏 / 数据不符 → Recovery 评估移交
   （JG-06 发布失败 → SP-18；JG-07 异常）
B. Incident 恢复 / 稳定：SP-21 需要 Recovery / Stabilization 动作
   （JG-08：SP-21 → SP-18 → SP-17 → SP-19）
C. Recovery 资产治理：修复脚本维护、恢复演练 / Recovery Smoke（EA-16）、
   高风险 Release 前 Recovery 执行面就绪（Ch11 §61）
D. Recovery 后 Forward Fix 路由：恢复本身需要新软件内容的
   （Ch7 §97）
```

红线：**Recovery 不得默认等于 Binary Rollback**（§90）；**依赖某 Recovery Anchor 前必须核验其真实存在**（§94 [BASELINE]）——事故发生才发现旧 Artifact 已删 / Schema 不兼容 / 没有备份是违规，不是意外。

不触发本规程的情形：

```text
Recovery 触发识别 / Decision 输入组织 / Anchor 真实性核验 /
Recovery Attempt 事实框架开立 / 执行控制（Authority Token） → SP-15
（本规程在其控制框架内执行；A12 提供 Trigger / Decision / Anchor）
Recovery Validation 判定语义 / 恢复后 Accepted Current Release → SP-17
Migration·Backfill 自身的暂停·恢复·对账设计（如 S5 reindex 的
Batch / Pause·Resume / Checkpoint / 对账）          → SP-08（本规程的
   backfill pause 只是消费其设计）
Emergency 压缩路径语义（Compression Profile / 事后对账）→ SP-21 / Ch8
Candidate 缺陷的修复实现                            → SP-06 / SP-13
Backup 策略与四要素设计                             → SP-08 数据域
   （Backup ≠ Recovery，本规程只消费已存在的恢复物质基础）
Feature disable 的资产与意图                        → SP-16（执行仍走
   本规程 + SP-15 控制框架）
Environment Current Runtime State 事实提交          → SP-15（执行期）；
   项目级 Current → SP-19（本规程不更新 Current）
```

---

# 2. 输入

```text
Recovery 移交包（SP-15 A12）         Trigger + 当前 Actual State +
                                    Failure / Unknown Evidence + Ch4
                                    Recovery Direction + Data / Contract
                                    Compatibility 核验结果 + Recovery
                                    Anchor 真实性核验结果（§91-94）
Recovery 资产现状                   修复脚本清单与版本（rollback /
                                    forward / repair，EA-16）、最近演练
                                    证据、Backup / Recovery Inventory
                                    （第三篇 Ch6 §83）
Migration / Backfill 状态（适用）      SP-08：Migration 阶段、可暂停点、
                                    对账 watermark（backfill pause 的对象）
暴露资产事实（适用）                 SP-16：Flag State / Kill switch 触发
                                    条件（disable feature 手段的物质基础）
Incident 上下文（适用）              SP-21：Mitigation Objective /
                                    Stabilization Fact（Trigger B 路径）
```

入口再挑战义务（B1 系统性规则）：使 Gate 归零的归类——"有 down.sql 所以能恢复"、"备份存在 = 可恢复"、"内部工具不需要恢复路径"、"低风险直接重试"——必须携带可解析理由；没有理由或理由不成立的，退回 SP-15 / SP-04 处置。

---

# 3. 输出

```text
Recovery Decision                  路径选择（Pause / Rollback / Rollforward /
                                   Restore / Compensate / Shift Traffic /
                                   Failover 或组合）+ 决策依据成文（§92、§96）
Recovery Attempt 执行记录          §98 九字段的执行侧补全（Attempt ID /
                                   Trigger / Starting State / Strategy /
                                   Anchor / Actions / Evidence / Final
                                   Observed State / Validation）——本规程
                                   正式承接执行记录义务（此前 SP-15 代行）
恢复执行事实                        所选手段的执行结果 + Authority Token
                                   确认事实（经 SP-15 控制框架）
Recovery Validation 事实集          old artifact truly running / data
                                   readable / critical flow restored /
                                   migration·traffic safe（§99-100）→
                                   移交 SP-17 判定
Forward Fix 路由决定                新软件内容回正常链（SP-06 → SP-13）
                                   或 Ch8 压缩路径 + 强制后补（§97）
Recovery 资产事实                   修复脚本版本、演练记录、执行面就绪
                                   结论（EA-16 证据面）
```

本规程**不输出**：

```text
触发识别 / Decision 输入 / Anchor 核验  → SP-15
Recovery Validation 判定结论            → SP-17
恢复后 Accepted Current Release 更新    → SP-17
Emergency 语义与事后对账                → SP-21 / Ch8
Candidate 修复实现                      → SP-06 / SP-13
Current 任何更新                        → SP-15（Runtime State）/ SP-19（项目级）
```

---

# 4. 核心语义

**Recovery ≠ Rollback（§89-90）**：Recovery 是"恢复到一个明确、安全、可验证的目标状态而执行的一组受控动作"；Rollback Artifact 只是八类候选手段之一——Forward Fix / Disable Feature / Restore Data / Compensation / Traffic Shift / Failover / Pause 同为候选（§90）。选择由 Change 类型与当前 Actual State 决定（P2 Ch11 §58、Ch7 §96）：有时 rollback 更安全，有时 rollforward fix 更安全，**不做全局固定选择**。

**Recovery Decision 基于事实（§92 [BASELINE]）**：基于当前 Target Actual State、Failure / Unknown Evidence、Ch4 Recovery Direction、Data / Contract Compatibility 与可用 Safe State 作出工程 Decision。**Binary Rollback 前必须回答三问**（P2 §59、Ch7 §95）：Old Binary 能读 New Data 吗？Old Consumer 能用 New Contract 吗？Migration 允许 Rollback 吗？——Artifact rollback ≠ System rollback。v1.9 已写入新值而 v1.8 不认识时，Binary Rollback 会失败。

**Anchor 真实存在 + 用旧不用新（§93-94、P2 §60）**：Recovery Anchor 是准备恢复到 / 继续向前到达 / 用来判断安全性的已知 Release / Artifact / Data State / Traffic State / Checkpoint / Stable Behavior Reference。事故时通常应**使用已经保存和验证过的旧 Artifact**，而不是 checkout 旧 commit 重新 resolve dependency 重新 Build 指望它和当年一样——Release Archive 与 Artifact Retention 的价值就在这里。

**恢复动作是 Target-changing Action（§114-115）**：delayed rollback、automated recovery、traffic revert、feature disable 同受 Target Change Authority Token 约束——旧 Intent 的异步恢复动作不得覆盖被新 Intent 接管的 Target。执行控制框架归 SP-15；本规程在框架内执行，不发明绕过通道。

**Command SUCCESS ≠ Complete（§99-100）**：`kubectl rollout undo` 成功只表示控制面操作完成；必须确认 old artifact truly running / data readable / critical flow restored / migration·traffic safe。Recovery Validation 的判定语义归 SP-17（§100 [BASELINE] 定义在彼处消费）；本规程负责采集验证事实。

**失败是历史（§102、P2 §62）**：失败 Attempt、Partial State、Recovery 都是历史工程事实，不得为了 Release 页面整洁删除；Release Failure 必须留下 Evidence（Release ID / Target / Attempt / Failure Point / Artifact / Migration State / Recovery Action / Final State），进入 Incident、Release Record 与 Engineering Health。

---

# 5. Engineering Actions

## A1 — 入口与决策输入核验

接收 SP-15 移交包（Trigger / Actual State / Evidence / Recovery Direction / Compatibility 核验 / Anchor 核验）。输入不齐全（如 Anchor 未核验、Compatibility 未检查）的，退回 SP-15 补齐——**不得在输入缺失状态下凭直觉开始恢复动作**。Incident 路径（Trigger B）同样先固化等价输入。

## A2 — Recovery Decision

在候选手段（§90 八类）中按 §92 事实作出路径选择并成文决策依据；与 Migration / Exposure 事实交叉核验：需要 backfill pause 的确认 SP-08 设计的暂停点存在；需要 disable feature 的确认 SP-16 Flag / Kill switch 资产与触发条件。Anchor 失效（旧 Artifact 已删 / Schema 不兼容）时不得宣称 rollback 可行——转入 Forward Fix 路径（A7）并按风险升级 Incident（SP-21）。

## A3 — Anchor 绑定与旧 Artifact 使用

把决策绑定到具体 Anchor（§93：previous accepted release / verified old artifact digest / database restore point / last reconciled migration watermark / stable traffic pool）。回滚类恢复使用 Release Archive 中已验证的旧 Artifact，不重新 Build"旧版本"（P2 §60）。

## A4 — 执行（Target-changing Action 框架内）

按所选手段执行：每次恢复动作前经 SP-15 确认 Authority Token 未被 supersede（§114-115）；非幂等动作在 Outcome Unknown 时先 Reconcile 实际结果再继续（Ch7 §42-44 部署规则同源）。执行中的 Runtime State 事实由 SP-15 执行期提交；本规程不直接写 Current。

## A5 — Recovery Attempt 执行记录

在 SP-15 开立的 §98 事实框架上补全执行侧：Actions / Evidence / Final Observed State（Validation 字段的事实由 A6 供 SP-17 填判定）。本条即此前"SP-15 代行执行记录"义务的正式承接点。

## A6 — Recovery Validation 事实采集与移交

采集 §99-100 验证事实：实际运行的 Artifact、数据可读性、关键业务流恢复、Migration / Traffic 安全；整理成 Recovery Validation 事实集移交 **SP-17** 判定（判定语义 = §100 [BASELINE]，恢复后 Accepted Current Release 归 SP-17 / §101）。验证不通过的，开立新 Recovery Attempt 或升级 Incident（SP-21），**不得把未验证状态报告为已恢复**（GI-06）。

## A7 — Forward Fix 路由

恢复需要 new source / new artifact / new contract 的，原则上回 **SP-06（实现）→ SP-13（Candidate / Verification）** 再 Delivery；Emergency 场景走 **SP-21 / Ch8 压缩路径 + 强制后补对账 / Verification**（§97）。Candidate 缺陷被 Target 有效证明的（Ch7 §105），随移交包回 SP-13 处置 C2 类重评。

## A8 — Recovery 资产与演练

维护修复脚本资产（rollback / forward / repair script，EA-16）的版本化与可用性；高风险 Release 前完成 Recovery 路径演练 / Recovery Smoke（EA-16 evidence face），支撑 SP-15 入口条件（§32 Recovery Direction）与授权 Basis（"previous safe artifact retained"）的物质面；Backup / Recovery Inventory 作为可查证据面（第三篇 Ch6 §83）。P2 §61 五问（什么情况停止 / 什么情况 Rollback / 什么情况只能 Forward Fix / Data 怎样恢复 / 谁做决定）的答案可执行性由本规程保证。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| 修复脚本执行 / 流量切换 / Artifact 回滚 | Automation（受 SP-15 Authority 控制） |
| Anchor 存在性机械核验 / 状态采集 | Guardrail / Automation |
| Recovery Decision（路径选择） | Engineering Decision |
| Forward Fix 路由判定 | Engineering Decision |
| 触发识别 / Attempt 框架开立 / Authority 控制 | 归 SP-15 |
| Recovery Validation 判定 | 归 SP-17 |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP18-01 Recovery 不得默认等于 Rollback——手段选择必须
                     基于 Actual State / Failure Evidence / Compatibility /
                     Anchor，八类候选按事实选择（§90-92、§96；P2 Ch11 §58）
[MUST][BASELINE]    G-SP18-02 依赖某 Recovery Anchor 前必须核验其真实存在
                     （§94）；回滚类恢复使用已保存验证的旧 Artifact，
                     不得事故时重新 Build 旧版本（P2 Ch11 §60）
[MUST][BASELINE]    G-SP18-03 Binary Rollback 前必须完成 Data / Contract
                     Compatibility 三问核验（Old Binary 读 New Data /
                     Old Consumer 用 New Contract / Migration 允许）
                     （§95、P2 Ch11 §59）
[MUST][BASELINE]    G-SP18-04 Recovery Command SUCCESS ≠ Recovery Complete——
                     控制面成功后必须确认实际状态再移交判定（§99）
[MUST][BASELINE]    G-SP18-05 Recovery Attempt 九字段记录齐全；失败 Attempt /
                     Partial State / Recovery 历史不得删除（§98、§102、
                     P2 Ch11 §62）
[MUST][BASELINE]    G-SP18-06 恢复动作（含 delayed rollback / automated
                     recovery / traffic revert / feature disable）执行前确认
                     Authority Token 未被 supersede——不绕过 SP-15 控制框架
                     （§114-115）
[MUST][BASELINE]    G-SP18-07 Forward Fix 产生新软件内容必须回正常链
                     （SP-06 → SP-13）或走 Ch8 压缩路径 + 强制后补对账，
                     不得就地裸改（§97）
[MUST][BASELINE]    G-SP18-08 高风险 Release 的 Recovery 执行面（Anchor /
                     脚本 / 演练过的路径）必须在 Release 前就绪（Ch11 §61、
                     EA-16）——"理论上可以 rollback"不算就绪（§94）
[MUST NOT][BASELINE] G-SP18-09 无依据的 gate-zeroing——"有 down.sql 所以能
                     恢复"、"备份存在 = 可恢复"、"内部工具无需恢复路径"、
                     "低风险直接重试"归类必须携带可解析理由，并可被
                     SP-05 / SP-13 / 组级审计再挑战（B1）
```

---

# 7. PASS Exit

```text
Recovery 完成（绑定 Recovery Attempt）：
  所选手段执行完毕且 Authority Token 确认事实在案
+ Recovery Attempt 九字段记录齐全（含 Final Observed State）
+ Recovery Validation 事实集移交 SP-17 并获判定
+ 适用时：Forward Fix 路由决定成文、恢复后 Current 事实经 SP-15 / SP-17
  提交
→ 移交 SP-17（判定）/ SP-21（Incident 对账，适用时）/ SP-13（Candidate
  重评，适用时）
```

完成**不代表**：Target 重新交付（回 SP-15 新 Attempt）/ Change 关闭（SP-19）/ Incident 关闭（SP-21）/ 根因已修复（Forward Fix 正常链）。

---

# 8. Evidence

Evidence by Work：

```text
Recovery Decision 记录（路径 + 依据 + 交叉核验）
Recovery Attempt 记录（§98 九字段）
Anchor 核验与旧 Artifact 使用事实（digest 比对）
Authority Token 确认事实（每次恢复动作）
Recovery Validation 事实集（移交 SP-17 的输入）
修复脚本版本与演练记录（EA-16）
失败历史（Attempt / Partial State / Recovery——保留不删）
```

只有 gate-zeroing 归类理由（down.sql / 备份存在 / 内部工具 / 直接重试）、Forward Fix 路由理由、Anchor 失效后的升级决定必须显式成文；其余证据随工作自然产生。

---

# 9. Current Update Obligation

本规程**不更新 Current**。恢复动作造成的 Environment Current Runtime State 变化由 **SP-15** 在执行期提交（Authority 背书下随真实恢复事实更新，Mixed / Recovering State 如实记录）；恢复后 Accepted Current Release 归 **SP-17**（§101）；项目级 Current（含 Recovery 引发的设计 / 结构修订）归 **SP-19**。

---

# 10. FAIL / Return Path

```text
决策输入不齐（Anchor 未核验 / Compatibility 未查） → 退回 SP-15 补齐
Recovery Validation 不通过             → 新 Recovery Attempt 或升级
                                         Incident（SP-21）；不得报告已恢复
Anchor 失效且无替代                     → Forward Fix 路由（A7）+
                                         Incident 升级评估
恢复动作 Outcome Unknown                → 先 Reconcile 实际结果（SP-15
                                         §部署规则同源），不盲目重试
旧恢复动作被新 Intent supersede         → 按 Ch7 §116 Outdated Attempt
                                         中止，不自 cover（SP-15 控制）
Candidate 缺陷                         → SP-13 重评 / SP-06 修复
Migration·Backfill 面恢复设计缺口       → SP-08
Material 设计问题（恢复路径本身不成立） → SP-05
```

---

# 11. Exception / Alternative Path

## 11.1 Outcome Unknown 的恢复动作

恢复动作部分失败 / 结果未知时，先 Reconcile 实际 Target State（Ch7 §42-44 同源规则），再决定继续、重试还是换手段；非幂等动作（数据写入类）不盲目 Retry。

## 11.2 无可用 Anchor

旧 Artifact 已删 / Schema 不兼容 / 无备份时，rollback 不可行是**事实**不是失败态度：转入 Forward Fix（A7），按影响升级 Incident（SP-21）；该状况本身进入 Engineering Health 与 Release Archive 保留策略改进（SP-09 域的 Retention 事实）。

## 11.3 数据破坏性变更已发生

Migration 已产生破坏性变更的，走 Restore Data / Compensation 路径；Backup 四要素（P2 Ch8 §49，SP-08 域）缺一的，不得宣称可恢复——如实登记 Evidence Gap，移交 SP-17 按 NOT_READY 语义处置。

## 11.4 Emergency 压缩执行

事故中 Recovery 与 Emergency Change 边界：稳定系统的恢复动作走本规程；需要新软件内容的 Emergency 修复走 SP-21 / Ch8 压缩路径（压缩的是义务时点不是义务本身），恢复动作本身仍受 Authority Token 约束。

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05 / GI-06（Command SUCCESS ≠ Complete 是 GI-06 直接应用）

Part II:
Ch11 §58-62——Rollback 非唯一答案 / Binary Rollback 兼容三问 /
  不重新 Build 旧版本 / Recovery Plan Release 前知道 / Release Failure
  Evidence（本规程的执行侧 WHAT）

Part III:
Ch3 Runtime / Deployment 面：Mixed / Recovering State 真实表达（§42、
  §60-64）、Runtime-Relevant Change 含 Release / Recovery、Recovery
  Runbook 不可用反例（结构状态未分开表达所致）
Ch6 Data / Shared Infrastructure WHERE 面：Operational Owner 承担备份
  与故障恢复、Backup / Recovery Inventory 证据面（§83）、Drift 反例
  （Backup / Restore 目标错误）；Recovery / Restore 的 WHAT 边界归
  第二篇 + 第四篇 + SP-08（本章 §职责声明）

Part IV:
Ch7 §89-102——Recovery 核心语义，本规程的执行权威（§89 定义、§90 八类
  手段、§91 Trigger、§92 Decision、§93-94 Anchor、§95 兼容性、§96 选择、
  §97 Forward Fix、§98 Attempt、§99-101 Command≠Complete·Validation·
  恢复后 Accepted、§102 历史保留）；§42-44（Outcome Unknown / Reconcile）；
  §114-116（Authority Token 约束恢复动作 / Outdated Attempt）；§122-132
  （WorkOrder：Canary FAIL → Recovery R1 实例）；§139（Recovery 相关
  MUST 条）

Journey:
JG-06 发布失败 → SP-18；JG-07 异常 → SP-18；JG-08 Incident：
SP-21 → SP-18 Recovery / Stabilization → SP-17 → SP-19
```

---

# 13. Executable Asset References

```text
EA-16 Recovery                rollback / forward / repair script 的版本化
                             资产；Recovery rehearsal / smoke 证据面
EA-15 Observability           Recovery Validation 事实采集（artifact
                             distribution / critical flow / data signal）
```

工具适合：脚本执行、Anchor digest 比对、状态采集、Attempt 记录维护、演练编排。
工具不适合：Recovery Decision（路径选择）、Anchor 真实性判断结论、Validation 判定（SP-17）、"看起来没事"式的完成判断——工具输出是 Signal 不是判定器（GI-07）。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Rollback = 按已验证 image digest 重新部署 + 流量回 stable pool；
  Restore = 数据库 PITR / snapshot；repair script 入库版本化；
  演练 = Staging 环境 Recovery Smoke（EA-16）

RP-B-CLI（pending-definition，组6）:
  无服务端 Rollback——Recovery = 重新分发旧版本 / Withdrawal Record；
  本地数据迁移回滚受限，修复优先；恢复脚本随 Distribution 版本化

RP-C-SDK（pending-definition，组6）:
  Consumer 侧无法强制回滚——Recovery = 发布 patch 版本 + 兼容指引 /
  迁移说明；Yanking / Withdrawal 是分发面动作（SP-15 §11），
  恢复语义 = 引导 Consumer 到安全版本
```

---

# 15. Example

**CHG-WO-142（工单转派能力升级）的恢复面——Canary FAIL 后的 Recovery R1 执行。**（承接组3 SP-15 示例 A11-A12 与 SP-17 示例：WO-1.9.0 在 Production-US 以 canary S1 = 5% 流量部署，new version transfer error material、old version 正常 → Proceed = STOP，Delivery Finding = Candidate Defect Discovered in Target。本例覆盖 SP-18 的执行侧。）

```text
A1 入口：接收 SP-15 移交包——Trigger = Canary bad（§91）；Actual State =
   mixed 1.8/1.9（S1 5% 新流量）；Compatibility 核验 = v1.8 仍能读取
   expanded schema / data（V203 为 backward compatible expand，SP-08
   设计事实）；Anchor 核验 = verified v1.8 artifact digest 在
   Release Archive 中可用（授权 Basis "previous safe artifact retained"
   的同一事实）
A2 Decision：路径 = traffic revert + artifact rollback（组合手段），
   依据 = schema expand 本身 backward compatible → 不需要 destructive
   rollback（§129-130）；决策成文
A3 Anchor 绑定：verified v1.8 digest（不重新 Build——P2 §60）；
   migration expand 保留、backfill pause 的对象 = S5 reindex backfill
   （SP-08 §53-54 设计的 Batch / Pause·Resume / Checkpoint 机制，
   组4 基线索引登记的同一事实）
A4 执行：traffic → stable pool、artifact → v1.8、migration expand
   保留、backfill pause——每次动作前经 SP-15 确认 Authority Token
   （§114：traffic revert 类动作同受约束）
A5 Attempt 记录：R1 九字段补全（Trigger / Starting State = mixed /
   Strategy = revert+rollback / Anchor = v1.8 digest / Actions /
   Evidence / Final Observed State）——SP-15 代行记录义务至此正式
   移交本规程
A6 Validation 事实：100% v1.8 serving、critical transfer flow
   healthy、new bad path inactive、data consistent → 移交 SP-17：
   Recovery Validation PASS、Accepted Current Release 保持 1.8
   （Target Scope = Production-US，§131）；Environment Current
   Runtime State = recovered v1.8 + expanded schema（SP-15 执行期提交）
A7 Forward Fix 路由：FAIL 根因 = Candidate logic defect → C2
   disposition 重评，修复走 SP-06 → C3 → SP-13 重验 → 新 Release /
   Attempt（§132）——不就地裸改
A8 演练事实：R1 路径在 Release WO-1.9.0 前已于 Staging 演练
   （EA-16 rehearsal/smoke）；repair script（流量回切脚本）版本化
   入库，Release Archive 保留 v1.8 digest（SP-14 / SP-09 域事实）
```

---

# 16. 最终原则

> **Rollback 只是把旧二进制放回去，Recovery 是让系统重新安全——数据还要读得通、旧 Consumer 还要接得住、关键流程还要走得完、迁移还要停得稳。真正的恢复能力在事故之前就已决定：Anchor 留没留、脚本练没练、兼容三问答没答。命令返回成功只是恢复的开始，验证通过才是恢复的结束；而失败的历史从来不是页面的污点，是系统下次活下来的依据。**
