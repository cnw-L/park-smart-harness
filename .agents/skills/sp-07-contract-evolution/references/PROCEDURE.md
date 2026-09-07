# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-07 Contract Evolution Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-09-01：组4 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1712 处引用核验 PASS AFTER REPAIR（REPAIR-1 已修复）；证据见组4 审计报告与横向回归报告）  
> 单一职责：把一次触及跨边界 Contract 的变化，受控地完成专业演进动作——建立 Contract 现状事实（Current Baseline / Stability / Lifecycle / Consumer 图景），按四视角判定 Compatibility 与 Breaking Change，选择演进策略（兼容演进 / Parallel Change / 新 Major），并组织 Deprecation / Removal 治理。  
> Contract ≠ Interface ≠ Schema；结构兼容 ≠ Contract 兼容；Version 是工具而不是兼容策略本身。  
> 结构化镜像：`第五篇-SP07-ContractEvolution-OperationContract.yaml`

---

# 1. Trigger

```text
A. Change 触及一个或多个跨边界 Contract——SP-04 Impact 识别 Contract Impact 后进入
   （JG-03 主线：SP-04 → SP-07 → SP-05（Material 时）→ SP-06）
B. 需要新增 / 演进 / 废弃 Contract——含 Config、Authorization / Policy 语义
   已形成跨边界承诺的情形（P2 Ch7 §14-16）
C. 发现 De-facto Dependency / 隐式 Contract 需要治理——正式提升为 Contract /
   提供迁移窗口 / 明确停止支持（§37）
D. Deprecated Contract 的 Removal Condition 到期评估（§55、§73.5）
```

红线：**Stable Contract 不得无声 Breaking**（§73.2 [MUST][BASELINE]）——Breaking Change 必须显式识别、Impact、策略、验证、受控 Release，不得作为普通 Internal Refactor 直接发布。

不触发本规程的情形：

```text
纯内部实现重构（不触及任何跨边界承诺）        → SP-06
Data Schema Ownership / Migration / Backfill → SP-08
  （本规程只管数据跨边界后 Consumer 可依赖什么，§13）
Dependency / Toolchain / Config 作为构建与环境事实 → SP-09
  （Config 作为跨边界承诺的兼容演进仍归本规程）
Security Enforcement 执行                    → SP-10
  （跨边界被依赖的 Authorization / Policy 语义演进归本规程，§16）
Contract Test / 验证执行与结论                → SP-11 / SP-12 / SP-13
Release / Delivery / Target 验证             → SP-15 / SP-17
Current Contract 的任何更新                   → SP-19（§68）
```

---

# 2. 输入

```text
Contract Impact 结论            SP-04：触及哪些 Contract / 边界类型 / 深度
Current Contract Baseline       当前有效承诺 + Artifact 引用（§67-69）
Stability / Lifecycle 现状       Stability Level × Lifecycle Status（§28-31）
Consumer 图景                   Consumer Type / Known Critical Consumer /
                                External·Internal / Upgrade Control（§19、§43-44）
触及 Contract 的类型             §8 六类：Module / HTTP·RPC / Event·Message /
                                Data Exchange / Configuration / Authorization·Policy
De-facto Dependency 线索（适用）  §37：已长期被依赖但未正式承诺的行为
```

入口再挑战义务（B1 系统性规则）：上游使 Gate 归零的归类——SP-04 的"Contract 无影响"判断、Internal-only 归类、N-A 声明——必须携带可解析理由；没有理由或理由不成立的，退回 SP-04 处置，不得带着未挑战的缺口进入演进设计。

---

# 3. 输出

```text
Contract Evolution Record     每个触及 Contract：Identity / 类型 / Stability ×
                              Lifecycle / Compatibility 判定 + 依据 / 演进策略 /
                              验证策略 / Owner（绑定 Current Baseline Revision）
Compatibility Matrix          必须支持的版本组合及其验证状态（适用时，§74）；
                              N/A 组合显式标注且与 Deployment / Rollback 策略一致
Parallel Change 阶段计划       Expand / Migrate / Contract 阶段定义 + 每兼容层的
                              Cleanup Condition + Owner（适用时，§48-51）
Deprecation Record            Deprecated What / Replacement / Reason / Migration
                              Guide / Consumer·Usage / Deprecation Start /
                              Removal Condition·Policy / Owner（适用时，§53）
Contract Debt 登记             兼容层 / 双栈 / 临时 Adapter 的 Risk + Owner +
                              Cleanup Condition（适用时，§78）
```

本规程**不输出**：

```text
Implementation Output / 代码实现               → SP-06
验证结论（Contract Test PASS / Candidate 结论） → SP-11 / SP-12 / SP-13
Release / Delivery 事实                        → SP-15 / SP-17
Current Contract 更新                           → SP-19（§68：Proposed 不提前覆盖 Current）
Data Migration / Backfill 执行                  → SP-08
```

---

# 4. 核心语义

**Contract 是 Consumer 可依赖的完整承诺（§2、§3.3）**：不只是 Interface / Schema，还包括 Meaning / Precondition / Postcondition / Failure Semantics / Default Behavior / Ordering / Delivery / Idempotency / Authorization / Compatibility / Stability / Deprecation Policy。**结构兼容不等于 Contract 兼容**——一个字段没变也可能 Semantic Breaking（§4：404→200+null），一个字段新增也不一定天然兼容（§5：新增 required field / response enum value）。

**隐式 Contract 与 De-facto Dependency（§1、§37）**：代码碰巧的行为被长期依赖即形成隐式 Contract。Breaking 判断的四个关键词是 Existing / Supported / Reasonable Consumer / Declared Contract——未文档行为不自动获得永久兼容权，但已被大量 Consumer 长期依赖时不得在 Impact 中假装不存在；处置三选一：正式提升为 Contract / 提供迁移窗口 / 明确停止支持。

**Stability × Lifecycle 两轴分离（§28-31）**：Stability Level = Experimental / Preview（可选）/ Stable（[BASELINE]），回答"可以期待多强的兼容承诺"；Lifecycle Status = Active / Deprecated / Retired，回答"当前存续状态"。Stable + Deprecated 并存合法。治理强度与 Consumer Independence 匹配（§7）：Provider 越无法控制 Consumer 升级，兼容义务越强。

**Compatibility 四视角（§32-36）**：Source / Wire / Semantic / Operational——不是互斥分类；Operational Compatibility（Timeout / Rate Limit / Resource / Ordering / Delivery / Retry / Availability Window / Deployment Compatibility）是 [BASELINE] 工程扩展。Semantic 往往比 Schema 更难（§35）。

**Breaking 判定的经典清单（§38-42）**：删除 Operation / 删除 Field / Rename（= Remove + Add，§39）/ Required Input 新增（§40）/ Field Type Change / 缩窄允许值 / 改变默认行为（§42：Optional Field ≠ Semantic Compatible）/ 改变 Error · Permission · Event 语义 / 取消原有 Side Effect / 改变关键 Ordering · Delivery Guarantee。Enum 变化分 Input / Output 思考（§41）。

**Version 是工具，不是兼容策略本身（§45-47）**：优先级 = Backward-compatible Evolution → Parallel Change / Migration → 必要时 New Major / New Contract。SemVer 适合 Library / Package / SDK 等明确版本化 Public API Artifact（§46），不机械要求所有 Endpoint / Event / Config 使用 MAJOR.MINOR.PATCH。**Version 字符串不得掩盖 Semantic Breaking**（§47）——兼容性最终看 Consumer Experience。

**Parallel Change（§48-52）**：把 Backward-incompatible 变化拆成 Expand → Migrate → Contract 三阶段；适用于一切 Provider / Consumer 不能原子升级的场景（不只 HTTP API：Event Schema / Config / Module Public Capability）。最大风险是 Expand 和 Migrate 做完、Contract 阶段永远不执行——**每个兼容层必须有 Cleanup Condition + Owner**（§51）。

**Deprecation（§53-56）**：先宣布退出，再真正删除；不是 TODO 注释（§54）；Removal Condition 比"随便定日期"重要（§55——内部 Contract 可以是"所有 Known Consumer 已迁移"，外部可能需要 Minimum Notice Period / Usage Threshold / Support Policy）；Stability Level 影响 Deprecation 承诺（§56）。

**Artifact 与验证（§57-66）**：必须存在权威、可发现的 Current Contract Source（§57）；机器可读 Artifact（OpenAPI / AsyncAPI / Proto / JSON Schema / Config Schema）非常有价值但不能替代 Semantic Documentation 与 Behavior Verification（§58-62）。Contract Test 验证"被显式编码出来的边界期望"，不是完整证明（§63）；Consumer-driven Contract 适合多独立 Consumer + Provider 频繁演进 + E2E 昂贵的场景，不是所有内部调用都要上（§64）。**验证不能只验证 Schema，也不能只依赖 Contract Test**（§65：Shape / Semantic Rule / Error / Default / Compatibility / Authorization / Ordering·Delivery / Idempotency）。机器 Diff 是重要 Signal，不是最终 Breaking Change 判定器（§66）。

**Current Contract Baseline（§67-69）**：必须描述当前有效承诺，不得把 Current v1 / Future v2 / Deprecated v0 混在无版本语义的描述里；**Proposed Contract 在新 Contract 成为有效软件状态前不得提前覆盖 Current**（§68）；多版本并存时 Supported Contract 各版本的 Stability / Lifecycle 与 Consumer Migration 状态要更清楚（§69）。

---

# 5. Engineering Actions

## A1 — 确认入口与 Contract 触及面

从 SP-04 移交出发，枚举本 Change 触及的全部跨边界 Contract（§6 的边界清单：跨 Module / Service / Team / Deployment / Release / 外部 Consumer / 持久化·消息边界 / 配置·权限公共承诺），按 §8 六类归类，按 §7 确定治理强度（Consumer Independence 越强越严格）。执行 B1 再挑战：上游的"无 Contract 影响"归类没有理由的，退回 SP-04。

## A2 — 建立 Contract 现状事实

对每个触及 Contract：解析 Current Contract Baseline（§67-69：当前有效承诺 + Artifact 引用 + 多版本并存状态）、Stability Level × Lifecycle Status（§28）、Provider / Consumer（§19）。建立 Consumer 图景（§43-44）：谁在用 / 哪些版本 / 是否外部 / 能否强制升级 / 是否存在长期离线 Client / 是否有持久化旧 Message。**Consumer 越不可见，Provider 越应该保守。**排查 De-facto Dependency（§37）：发现未文档但已被长期依赖的行为，显式登记并按三选一处置。

## A3 — Contract Diff 与 Compatibility 判定

产生 Before / After 对照（§66：OpenAPI Diff / Proto Compatibility Checker / Schema Registry Compatibility / Git Diff / Manual Semantic Review）。机器 Diff 覆盖结构变化；人工 Review / Behavior Test / Consumer Test 补 Semantic / Operational 变化——**机器 Diff 是 Signal，不是判定器**。按四视角逐一检查（§32-36），对照 §38-42 清单判定 Breaking 与否。判定结论携带理由（B1）：判定"兼容"必须说明四视角各自依据；判定"Breaking"必须说明触及哪个承诺面。该判定可被 SP-05 / SP-13 / 组级审计再挑战。

## A4 — 选择演进策略

按优先级（§45）：能 Backward-compatible 演进就不上新版本；不行则 Parallel Change / Migration；再不行才 New Major / New Contract。**非原子升级必须先定义必须支持的版本组合**（§73.4 [MUST][BASELINE]）：Old Consumer + New Provider 永远要查；New Consumer + Old Provider 只在 Rolling / Independent Deployment 需要时；Rollback 组合（§75）；Stored Old Message / Data（§76——删除 / 复用字段前检查 retained event / dead-letter / audit log / archived file / old row）。用 Compatibility Matrix 表达组合及其验证状态（§74）；标记 N/A 的组合必须真实可靠、与 Deployment / Rollback Strategy 一致——这个 N/A 是 gate-zeroing 判断，按 B1 携带理由。

## A5 — Parallel Change 阶段控制（适用时）

定义 Expand / Migrate / Contract 三阶段（§48-52）：Expand = 新旧同时工作；Migrate = Consumer 逐步迁移（周期取决于 Consumer Independence，外部最长）；Contract = 旧 Consumer 迁移完成 + 兼容窗口结束 + Removal Condition 满足后才删除旧能力。**每个兼容层登记 Cleanup Condition + Owner**（§51）；Migrate 阶段状态（谁已迁 / 谁未迁）如实维护，防止永久双栈。

## A6 — Deprecation / Removal 治理（适用时）

Deprecated Contract 登记八项（§53）：Deprecated What / Replacement / Reason / Migration Guide / Consumer·Usage / Deprecation Start / Removal Condition·Policy / Owner。Removal Condition 按内外部区别定义（§55）；Stability Level 影响承诺强度（§56）。只打标签没有迁移对象 / 迁移状态 / 退出条件的，不是 Deprecation，是注释（§54）。

## A7 — Contract Artifact 与验证策略

确认权威、可发现的 Current Contract Source（§57）；多 Consumer / 长期维护的 HTTP API 优先机器可读 Artifact（§58-59），Event 用 AsyncAPI / Schema + Event Semantics（§60），Proto 演进遵守其纪律（§61：不复用 tag / 保留已删 tag / 不随意改类型 / 不加 required / 不随意改默认语义）。制定验证策略（§65 八项按适用性）：Shape / Semantic Rule / Error / Default / Compatibility / Authorization / Ordering·Delivery / Idempotency。Contract Test / CDC 按适用条件引入（§63-64）；验证执行移交 SP-11 / SP-12 / SP-13，本规程只定义"要验证什么承诺面"。

## A8 — Review 组织与 Owner 确认

确认 Contract Owner（§70：Provider Owner 管 Meaning / Compatibility Policy / Change Review / Deprecation / Migration Support / Current Artifact；Consumer Owner 管正确使用 / 迁移 / 不依赖 Undocumented Detail；外部 Consumer 无法指定 Owner 时用 Documentation / Support / Usage Telemetry / Communication 管理）。Review 覆盖风险边界（§71 按类型），Checklist 按适用性勾选（§72，N-A 项携带理由——B1）。Review 执行归 SP-12。

## A9 — 移交与下游边界

- Contract 变化 Material 到设计层 → 演进策略与 Compatibility 结论移交 **SP-05** 作 Design Decision（Transition 三分离语义归 SP-05，本规程的 Parallel Change 阶段计划作为其输入）；
- 实现执行（含 Contract Artifact 同步硬规则）→ **SP-06**；
- 验证执行与 Candidate 结论 → **SP-11 / SP-12 / SP-13**；
- 交付与 Target 验证 → **SP-15 / SP-17**；
- Emergency Breaking Change（§77：Critical Security Vulnerability / Regulatory / Data Exposure / Severe Production Risk）→ 压缩执行与事后对账归 **Ch8 + SP-21**（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5），但 §77 八项最低记录（Reason / Risk / Affected Consumer / Emergency Decision / Communication / Mitigation / Verification / Follow-up Migration）与本规程的兼容分析**不豁免**。

## A10 — Contract Debt 与 Health 登记

兼容层 / 永久双版本 / Deprecated 永不删 / Consumer 直读 Provider DB / 重复 Event / 临时 Adapter / Compatibility Flag——逐项登记 Risk + Owner + Cleanup Condition（§78）。长期项目可观察 Health Signal（§79：Deprecated Contract Count / Consumer Migration Age / Breaking Change Incident / Contract Test Failure / Unknown Consumer / Direct Cross-boundary DB Access / Compatibility Layer Age），不强制 KPI 化。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Contract Diff 生成 / 机器兼容检查 | Automation |
| 四视角 Compatibility / Breaking 判定 | Engineering Decision（机器 Signal 只作输入） |
| 演进策略选择 / Matrix 组合定义 | Engineering Decision |
| Expand / Migrate / Contract 阶段推进判定 | Engineering Decision + Guardrail（Removal Condition 机械核验） |
| Deprecation 字段完整性 / 兼容层 Cleanup 登记 | Guardrail |
| Review / 验证 / 交付执行 | 归 SP-12 / SP-11·13 / SP-15·17 |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP07-01 Stable Contract 不得无声 Breaking——显式识别 → Impact
                     → Migration / Version / Deprecation 策略 → Verification →
                     受控 Release（§73.2）
[MUST][BASELINE]    G-SP07-02 非原子升级必须先明确必须支持的版本组合并验证；
                     N/A 组合必须真实可靠且与 Rollback 策略一致（§73.4、§74-76）
[MUST][BASELINE]    G-SP07-03 Deprecated Contract 必须有 Replacement / Migration /
                     Owner / Removal Condition，不得只打标签（§73.5、§54）
[MUST][BASELINE]    G-SP07-04 跨稳定边界（Consumer 可独立变化）必须有明确
                     Contract：Capability / Input·Output·Message / Meaning /
                     Failure / Compatibility Expectation / Owner（§73.1）
[MUST NOT][BASELINE] G-SP07-05 把机器 Diff / Schema 兼容当最终 Breaking 判定器——
                     Semantic / Operational 视角必须检查（§65-66、§35-36）
[MUST NOT][BASELINE] G-SP07-06 在完全不知道 Consumer 的情况下盲改关键 Contract
                     （§43-44）
[MUST NOT][BASELINE] G-SP07-07 建立无 Cleanup Condition / 无 Owner 的兼容层
                     （§51、§78）
[MUST NOT][BASELINE] G-SP07-08 Proposed Contract 提前覆盖 Current Contract；
                     Current 更新一律走 SP-19（§68，GI-05）
[MUST NOT][BASELINE] G-SP07-09 用 Version 字符串不变声称"无 Breaking Change"——
                     兼容性看 Consumer Experience（§47）
[MUST NOT][BASELINE] G-SP07-10 无依据的 gate-zeroing——"兼容"判定、N-A 组合、
                     De-facto 降级、Internal-only 归类必须携带可解析理由，
                     并可被 SP-05 / SP-13 / 组级审计再挑战（B1、§74）
```

---

# 7. PASS Exit

```text
Contract Evolution Plan 成立（绑定 Contract Identity + Current Baseline Revision）：
  每个触及 Contract 有四视角 Compatibility 判定与依据
+ 演进策略明确（兼容演进 / Parallel Change 阶段计划 / New Major）
+ 验证策略覆盖适用承诺面（§65）
+ 适用时：Matrix 组合与验证状态、Deprecation Record、兼容层 Cleanup 义务
→ 移交 SP-05（Material 时）/ SP-06
```

完成**不代表**：验证已通过 / Contract 已发布 / Consumer 已迁移完成 / Current Contract 已更新。

---

# 8. Evidence

Evidence by Work：

```text
Contract Evolution Record（判定 + 策略 + 依据）
Contract Diff（机器 + 人工语义对照）
Compatibility Matrix（适用时）
Deprecation Record / Removal 评估（适用时）
Review Record（SP-12，Revision-bound）
```

只有 Breaking 判定理由、N-A 组合理由、De-facto 处置决策、Emergency 八项记录必须显式成文；其余证据随工作自然产生。

---

# 9. Current Update Obligation

本规程**不更新 Current**。Current Contract 必须描述当前有效承诺（§67）；Proposed Contract 在成为有效软件状态前不得提前覆盖（§68）——Current Contract 的迁移在新 Contract 经 Implementation + Verification + Release / Baseline Transition 完成后，显式走 **SP-19**。多版本并存期间，Supported Contract 的 Stability / Lifecycle 与 Consumer Migration 状态如实维护（§69），这是 Baseline 事实维护，不是 Current 改写。

---

# 10. FAIL / Return Path

```text
Consumer 图景不可知且变化关键       → 先补 Consumer 信息（§43-44 轻量手段），
                                      否则只能选保守策略；禁止盲改（G-SP07-06）
验证策略覆盖不足                   → 回 A7 补承诺面
Material 设计问题（Transition / 目标变化）→ SP-05
De-facto Dependency 争议           → 三选一显式决策（§37），不得搁置
Rollback / Stored Message 组合不可支持 → 回 A4 重定组合或调整 Release 策略（§75-76）
Emergency Breaking                 → Ch8 + SP-21（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5）压缩路径；
                                     §77 八项记录与本规程兼容分析不豁免
```

---

# 11. Exception / Alternative Path

## 11.1 同 Team、同 Repo、可原子升级

§80.1 轻量形态：Public Interface + Semantic Rule + Module Test 即可；Breaking Change 仍需 Impact，但可不要求长期 Version（§80.1）；Deprecation 承诺按 §56（Stability Level 影响 Deprecation 承诺）与实际 Consumer 显式判断。前提"可原子升级"必须真实（同 Repo 同 Release），否则按 §80.2/§80.3 加强。

## 11.2 Experimental / Preview Contract

可明确不保证长期兼容（§29、§56），但最低四项不可省：Not Stable 标注 / Consumer Scope / Change Expectation / Owner。Experimental 不等于可以没有 Documentation。

## 11.3 Emergency Breaking Change

§77 四类情形可压缩 Deprecation Window；八项最低记录不豁免；压缩执行与事后工程对账归 Ch8 + SP-21（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5；落地前按 Ch8 正文执行），Compatibility 与 Consumer 影响分析仍走本规程。

## 11.4 一次性内部系统

可协调原子升级（§48），不强制 Parallel Change；"一次性 / 可协调"的判断携带理由（B1）。

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05

Part II:
Ch7 Contract 要求 全章——本规程的 WHAT Authority
（§28-31 Stability×Lifecycle、§32-42 Compatibility 与 Breaking、
 §43-47 Consumer 与 Version、§48-56 Parallel Change 与 Deprecation、
 §57-66 Artifact 与验证、§67-69 Current Baseline、§70-72 Owner 与 Review、
 §73 Minimum Requirements、§74-77 Matrix / Rollback / Stored / Emergency、
 §78-79 Debt 与 Health、§80 三类裁剪）
Ch6 模块要求（Module Public Capability 前置）
注：Ch7 §77 / §86 正文中引用的第五篇编号为旧 lineage（SP-22 Emergency、
SP-25~27 Calibration）；按 SP-22 封顶口径映射为 SP-21（组5 pending）与 SP-19。

Part III:
Contract / Consumer / Mapping（Ch7 Cross-dimension Mapping 的 Contract 关系面）

Part IV:
Ch3（Contract Impact 由 SP-04 产出，本规程深化）
Ch4（Transition 设计承接——Parallel Change 阶段计划作为 SP-05 输入）
Ch5（Contract Artifact 同步硬规则在 SP-06 A5）
Ch8（Emergency Breaking 压缩路径）

Journey:
JG-03 修改公共 API / Event / Contract 主线
```

---

# 13. Executable Asset References

```text
EA-09 Migration / Contract Template   兼容演进骨架与 compatibility / smoke 验证
EA-08 Verification Harness            Contract Test / 兼容矩阵的确定性执行载体
EA-17 Current Navigation              Current Contract / Consumer Registry 可发现性
```

工具适合：机器 Diff、Schema 兼容检查、Matrix 存在性核验、Deprecation 字段完整性检查。
工具不适合：Semantic / Operational Compatibility 判定、演进策略选择、De-facto 处置决策。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  HTTP Contract Artifact = OpenAPI（CI diff check）；Internal Event = Schema + 语义文档
  Consumer 图景 = Service Dependency Map + Repository Search；Module Test + 可选 CDC

RP-B-CLI（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组6）:
  Contract 面 = 命令 / 参数 / 输出格式（含 JSON 输出稳定性）；SemVer 于包版本
  Consumer = 下游脚本 / CI 集成；无长期在线 Consumer，Rollback 兼容按安装形态裁剪

RP-C-SDK（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组6）:
  Contract 面 = Public API Surface；严格 SemVer；兼容窗口最强
  Deprecation 先行于 Removal（至少一个 Minor 标记）；Consumer 不可控 → 最保守判定
```

---

# 15. Example

**CHG-WO-142（工单转派能力升级）的 Contract 演进——本组示例链的前段：C9 契约束怎样从 v1 演进出 reason 能力。**（本示例对应 P2 Ch7 §81-84 的 WorkOrder Transfer API / Event 例子；同一 Change 的 Candidate / 交付 / Closure 见组3 各规程示例。）

```text
A1 触及面：POST /v1/work-orders/{id}:transfer（HTTP Contract，Stable/Active，
   外部 Partner 是 Known Critical Consumer）+ WorkOrderTransferred Event
   （Event Contract）→ 治理强度按 §80.2/§80.3 之间处理
A2 现状事实：Current = transfer v1（input: targetUserId；failures: 403/404/409；
   幂等 by idempotency key）；Consumer 图景 = Web / Admin App / Partner（外部，
   不能强制升级）；排查发现 Admin App 长期依赖"transfer 成功后 5s 内必有
   WorkOrderTransferred"这一未文档时序 → De-facto Dependency 登记，
   决策：正式提升为 Event Contract 的 Timing 语义（§37 三选一）
A3 Diff 与判定：需求 = transfer 增加 reason。直接 required = 经典 Breaking
   （§40）→ 判定：required 方案 Breaking；改为 optional + 默认行为不变 =
   Source/Wire/Semantic/Operational 四视角均兼容（§32-36），理由记录。
   Event 新增 reason 字段：按 §84 检查旧 Consumer 忽略未知字段 /
   Schema Registry Policy / Deserializer strict / 不改变原 Event Meaning →
   判定兼容，理由记录
A4 策略：Backward-compatible 演进（reason optional）足以承载近期需求；
   业务终态"所有新 Transfer 必须有 reason"登记为未来 New Major / staged
   enforcement 事项，不在本 Change 无声推进（§83）。版本组合：
   Old Consumer + New Provider 必须工作（Matrix 唯一组合，验证状态 =
   待执行——执行移交 SP-11 / SP-13）；
   New Consumer + Old Provider 不存在独立部署 → N/A，理由 = 部署顺序保证
A5 本 Change 无需 Parallel Change 三阶段；若未来推进 reason required，
   走 Expand（已就位）→ Migrate（Partner 迁移）→ Contract（Removal
   Condition = 所有 Known Consumer 已迁移 + 通知窗口）
A7 验证策略：Shape（schema test）+ Default（reason 缺省行为不变）+
   Error（403/404/409 语义不变）+ Idempotency（同 key 不产生第二次
   transfer）+ Event Meaning / Ordering 不变 → 移交 SP-11 / SP-13 执行
```

---

# 16. 最终原则

> **Contract 演进的全部纪律，是让"承诺"这个词保持含金量：Provider 可以自由改变内部实现，但 Consumer 被允许依赖的东西——语义、默认、失败、顺序、幂等——要么不变，要么被显式识别为 Breaking 并给出迁移与退出路径。Version 号是工具，Diff 是 Signal，Schema 是片段；真正的判定永远站在 Consumer 一侧。最危险的从来不是 Contract 会变，而是变了没有人识别、没有人迁移、没有人删除。**
