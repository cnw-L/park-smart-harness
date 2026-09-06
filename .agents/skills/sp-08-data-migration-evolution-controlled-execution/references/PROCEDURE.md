# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-08 Data / Migration Evolution & Controlled Execution

> 类型：Specialized Procedure  
> 状态：SEALED（2026-09-01：组4 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1712 处引用核验 PASS AFTER REPAIR（REPAIR-1 已修复）；证据见组4 审计报告与横向回归报告）  
> 单一职责：把一次触及持久数据的变化（Schema / Representation / Reference Data / Change-driven Transformation / Backfill / Production Data Fix），受控地完成专业演进与受控执行——建立数据语义与所有权事实，设计 Current → Target（必要时经 Transition）演进，管理 Migration / Backfill 的版本化与执行控制，定义兼容组合与 Recovery，并组织验证。  
> 代码可以重新部署，已经产生的数据不能简单重新生成；Migration Success（命令没报错）≠ Data Change 正确完成；Rollback ≠ Recovery。  
> 结构化镜像：`第五篇-SP08-DataMigrationEvolution-OperationContract.yaml`

---

# 1. Trigger

```text
A. Change 触及项目控制的持久 Data / Representation——SP-04 Impact 识别 Data /
   Migration Impact 后进入（JG-04 主线：SP-04 → SP-08 → SP-05（Material 时）→ SP-06）
B. Schema / Constraint / Index / Reference Data 需要新增、演进或收缩（§16-17、§41）
C. Change-driven Transformation / Backfill / Production Data Fix 需要受控执行
   （§17、§25-27、§42）
D. 数据侧兼容演进：Old / New Application 与 Schema 多版本并存、Dual Read / Write
   过渡、Retention / Archival / Deletion 变化（§28-31、§48）
```

红线：**高风险 Data Change 不得无 Recovery 设计而执行**（§65.5 [MUST][BASELINE]）——失败以后真正怎么恢复必须先有答案，而不是只问有没有 down.sql（§33）。

不触发本规程的情形：

```text
数据跨边界后 Consumer 可依赖什么（Data Exchange Contract 的演进）
                                      → SP-07（本规程只管数据自己的语义 / 结构 /
                                        Migration 可控，P2 Ch8 §68）
普通 Application Transaction Data      → 非 Migration 范畴（§17、§65.2）
实现执行（代码 / Artifact 同步）        → SP-06
验证执行与 Candidate 结论               → SP-11 / SP-12 / SP-13
Release 编排 / 部署 / Target 验证       → SP-15 / SP-17
  （Migration / Backfill 的执行控制本身是本规程的专业动作，与 SP-15 的 Release
    Path 编排配合，不由 SP-15 代为设计）
Dependency / Toolchain / Config 环境事实 → SP-09
Security Control 执行（权限最小化落地、敏感数据合规控制）
                                      → SP-10；
                                        Data Meaning / Ownership / Write Authority
                                        仍以本章 WHAT 与本规程为准（§46）
Current Data Baseline 的任何更新        → SP-19（§61）
Emergency Data Repair 的压缩执行与事后对账 → Ch8 + SP-21（pending-definition，组5）；
                                        专业动作与证据仍走本规程（§43）
```

---

# 2. 输入

```text
Data / Migration Impact 结论     SP-04：触及哪些持久数据 / Schema / Consumer /
                                 深度与不可逆性
Current Data Baseline            Current Data Model / Shape、Schema /
                                 Representation Version、Ownership / Authority、
                                 Constraint、Migration State、Supported Release
                                 Compatibility——带 Environment / Baseline Scope
                                 （§59-60）
数据语义与所有权事实              Meaning / Owner / Write Authority / Invariant /
                                 Authoritative Source / Derived 关系（§4-8）
Migration 资产现状               Applied Migration State（各环境：ID / Applied
                                 Time / Result / Schema State，§18-19）
Existing Data 事实（适用）         数据量 / 分布 / 非法值 / 历史语义（§25、§35、§65.3）
发布路径事实                     Rolling / 多版本并存 / Maintenance Window /
                                 Zero-downtime 要求来源（§28、§55-56）
```

入口再挑战义务（B1 系统性规则）：上游使 Gate 归零的归类——SP-04 的"Data 无影响"判断、"additive 所以零风险"假设、"低风险纯 DDL"归类、N-A 组合声明——必须携带可解析理由；没有理由或理由不成立的，退回 SP-04 处置。Additive ≠ 零风险（§22：新 Index 可能长时间 Lock、新 Column Default 可能触发大规模 Rewrite、新业务默认可能改变语义）。

---

# 3. 输出

```text
Data Evolution Record        每触及数据面：Meaning / Owner / Write Authority /
                             Invariant / Authoritative Source / Derived 定位 /
                             Null·Default 语义 / Identifier 稳定性 /
                             Time·Unit·Encoding（§8、§12-15）
Schema Evolution Design      Current / Target /（必要时）Transition Schema 区分
                             （§20）；Additive / Destructive 显式识别（§22-23）
Migration / Backfill Plan    版本化 Migration Artifact（Identity / Dependency /
                             顺序，§16-18）；Backfill 决策（允许为空 / 推导 /
                             默认值 / 人工修复 / 无法恢复清单，§25）；
                             大型 Backfill 的 Batch / Rate / Pause-Resume /
                             Observability 设计（§27、§53-54）
Compatibility Plan           真实 Release Path 的版本组合定义（§28、§65.4）；
                             与 Application Release 的解耦编排（§55）
过渡机制设计（适用时）        EMC 阶段计划 / Dual Read·Write 的 Owner / Exit
                             Condition / Verification / Cleanup + 冲突
                             Source of Truth（§29-31）
Recovery Design              Forward Fix / Restore / Compensation / Repair /
                             Disable Feature / Replay Event 之一或组合（§33）；
                             长迁移的 Restart / Recovery 机制（§34）
Verification Plan            Precondition / Postcondition / 独立验证手段
                             （§35-37）；高风险用 Production-like Data（§52）
Migration Evidence           Artifact / ID / Review / Execution Result /
                             Environment / Start·End / Validation / Backfill
                             Result / Error·Retry / Recovery Record（§62）
```

本规程**不输出**：

```text
Data Exchange Contract 的 Consumer 承诺演进  → SP-07
代码实现 / 业务逻辑                          → SP-06
验证结论（Test PASS / Candidate 结论）        → SP-11 / SP-12 / SP-13
Release / Deployment 事实                    → SP-15 / SP-17
Current Data Baseline 更新                    → SP-19（§61：Target 不提前覆盖 Current）
持续 Data Quality 治理制度                    → 运行期治理（本规程只管本 Change 的
                                              可验证 Data Quality Requirement，§40）
```

---

# 4. 核心语义

**Data ≠ Data Model ≠ Schema ≠ Database（§2）**：Data 首先是业务或系统事实；Schema 是某种持久化实现形式，不是完整 Data Contract，但它是重要的 Executable Constraint（§9）——能稳定放进 Schema / Constraint 的不变量应考虑自动保护，但 Constraint 要保护真实 Invariant，不为"数据库更严格"制造错误限制（§11）。**代码可以重新部署，已经产生的数据不能简单重新生成**（§1）——这是数据变化五重风险（业务语义 / 兼容 / Migration / 运行 / 不可逆）的根源。

**Data Ownership 与 Authoritative Source（§4-7）**：核心业务 Data 必须有明确 Owner（谁定义 Meaning / Write Rule / Invariant / 谁批准破坏性语义 Change）；Data Owner ≠ Database Administrator（§5）。针对每个明确 Business Fact，必须知道哪个系统是 Authoritative Source；Derived Data（Cache / Index / Read Model / Projection）不能默认一定可以完整重建——必须明确 Source / Lineage / Refresh / Consistency Expectation / Retention Assumption / Recovery / Rebuild Method（§7）。Direct Database Read 也形成 Contract（§45）：Schema Change 必须知道谁在读。

**Data Meaning 必须比 Column Name 更稳定（§8、§12-15）**：重要数据明确 Meaning / Allowed Value / Unit / Timezone / Null Meaning / Default Meaning / Lifecycle / Ownership。Null 的 unknown / not applicable / not collected / not migrated / not yet calculated 是完全不同的语义（§12）；Default Change 是 Semantic Change，必须进 Impact（§13）；Identifier 一旦被外部依赖就形成 Contract（§14）。

**Schema 必须版本化（§16-19）**：项目控制的持久 Data / Representation Change 必须建立 Migration 或等价 Versioned Change Mechanism（[MUST][BASELINE] §65.2）；Schemaless ≠ Evolution-less。Migration = Known Preconditions + Migration Artifact → Reproducible Target State 的可版本化、可追踪 Change Artifact（§17），不强制幂等 / 线性序号，但 **Migration Identity、Dependency、Applied History 可确定**（§18），Applied Migration State 按环境可查询（§19）。

**Current / Target / Transition 三分离（§20、§59-61 [BASELINE]）**：Transition Schema 是迁移期间兼容旧新 Application 的临时结构；Migration 完成前 Target 不得冒充 Current；Current Data Baseline 是数据工程事实的 Baseline Metadata / Design State（不是业务行数据的静态 Snapshot），必须带 Environment / Baseline Scope（§60）。

**Additive ≠ 零风险，Destructive 必须显式识别（§22-24）**：DROP / RENAME / Narrow Type / Change Meaning / Re-use Identifier / Delete Historical Data / Tighten Constraint 必须问：旧 Application 还需要吗？旧 Data 还存在吗？Consumer 是否读取？Rollback 怎么办？Rename 在版本并存时通常走 Expand → Migrate → Contract，但单一 Consumer + 可协调原子 + 风险可接受时直接 Rename 也可能是正确方案——按真实 Compatibility Requirement 决定，不机械禁止（§24）。

**Backfill 与 Schema Migration 分开思考（§25-27）**：新 Schema ≠ 旧 Data 自动正确；复杂 Change 区分 Schema Migration / Data Backfill / Application Switch / Cleanup，而不是一个巨大 Transaction 一次做完；数据量大时 **Migration 本身就是 Production Workload**。

**Rollback ≠ Recovery（§32-34）**：不能把"所有 Migration 都必须有 Down Script"当通用安全规则——数据可能已经删除 / 合并 / 向外发送副作用 / 写入旧版本无法理解的值。Recovery 手段 = Forward Fix / Restore Backup / Compensation / Data Repair / Disable Feature / Replay Event。长时间或可中断 Migration 按风险设计 Idempotency / Checkpoint / Batch Progress / Resume / Safe Retry / Partial State Detection（§34）。

**Dual Read / Write 是可选过渡机制，不是默认方案（§29-31）**：它可能显著放大一致性问题；采用前必须能回答四问（两个写入是否原子？一个失败怎么办？怎样发现分叉？谁是 Authoritative Source？），并必须有 Owner / Exit Condition / Verification / Cleanup——不要让"双写三个月"变成"双写三年"。

**Migration Success ≠ Data Change 正确完成（§35-37、§52）**：高风险 Migration 执行前检查 Precondition（不满足优先阻止，而不是继续赌）；执行后证明 Postcondition；重要 / 转换型 / 高风险 Change 不以 exit code = 0 为唯一完成证据（§65.6 [MUST][BASELINE]），独立检查 Row Count / Null Count / Constraint / Checksum / Aggregate / Sample / Business Invariant / Old·New Comparison；高风险尽量在脱敏 Production-like Data 上验证 Scale / Lock / Duration。**Backup ≠ Recovery**（§49）：Backup exists + Restore process exists + Restore has been verified + Recovered data can be validated，缺一不可。

---

# 5. Engineering Actions

## A1 — 确认入口与数据触及面

从 SP-04 移交出发，定位本 Change 在数据链路中的位置（§3：Requirement → Data Meaning → Impact → Design → Schema / Migration Design → App Compatibility → Migration / Backfill → Verification → Release → Current Data Baseline）。枚举触及的持久数据面：Schema / Constraint / Index / Reference Data / Transformation / Backfill / Production Data Fix（§17、§41-42）。执行 B1 再挑战：上游的"无 Data 影响 / additive 零风险 / 低风险纯 DDL"归类没有理由的，退回 SP-04。

## A2 — 建立数据语义与所有权事实

对每触及数据面明确（§65.1 [MUST][BASELINE]）：Meaning / Owner / Write Authority / Invariant；Authoritative Source 与 Derived 定位（§6-7）；Null / Default 语义（§12-13）；Identifier 稳定性（§14：是否全局唯一 / 可重用 / 暴露外部 / 可迁移）；Time / Unit / Encoding（§15）。发现语义缺失或 Owner 不清的，先补齐再设计演进——不得在语义空白上设计 Migration。

## A3 — 定义 Current / Target / Transition

从带 Scope 的 Current Data Baseline 出发（§59-60），定义 Target Schema；存在非原子兼容需求时定义 Transition Schema（§20——迁移期兼容旧新 Application 的数据结构；变更过渡的方案编排 Transition 设计归 SP-05，见 A10，两者不同层）。显式识别 Additive / Destructive（§22-23）；Destructive 逐项回答旧 Application / 旧 Data / Consumer / Rollback / Backup 五问。识别 Direct Reader / Shared Database 风险（§44-45）。

## A4 — 设计 Migration / Backfill

建立版本化 Migration Artifact：Identity / Dependency / 顺序明确（§16-18 [MUST][BASELINE] §65.2）；外部 SaaS / 第三方控制的 Schema 至少版本化 External Contract / Expected Schema / Compatibility Assumption / Integration Change（§65.2）。Backfill 决策显式成文（§25、§65.3 [MUST][BASELINE]：旧数据允许为空？能否推导？需要默认值？必须人工修复？哪些无法恢复？）。大型 Backfill 按 Production Workload 设计：Batch / Rate Limit / Pause·Resume / Checkpoint / Observability（§27、§53-54）。理解目标 Database 的真实运行行为（Lock Level / Transactional DDL / Online Index——§50-51，不把某一种 Database 的行为当通用规律）。高风险变化按风险定义 Precondition（§35）。

## A5 — 定义兼容组合与 Release 耦合

非原子发布必须定义真实 Release Path 需要支持的组合（§28、§65.4 [MUST][BASELINE]）：Old App + New Schema / New App + Old or Transition Schema / Rollback App + New Data——不是所有组合都必须支持，但真实发布路径会出现的组合必须提前定义并验证；N-A 组合携带理由（B1）。与 Application Release 解耦到合理程度（§55：高风险不一 Deployment 同时 DROP + Deploy + Backfill；简单 Change 不强拆）。Zero-downtime 要求必须来自 Availability / Business Requirement，不是默认硬指标（§56）。禁止先改 Production 再补代码，禁止代码依赖尚未执行的新 Schema（§21）。

## A6 — 设计过渡机制（适用时）

EMC 三阶段（§29）或 Dual Read / Dual Write / Fallback Read / Shadow Write（§30-31）按真实方案选择——不是所有 Data Change 的默认模板。Dual Write 必须回答四问并登记 Owner / Exit Condition / Verification / Cleanup + 冲突 Source of Truth；EMC 的 Contract 阶段长期不完成会让系统更糟（§29），过渡机制一律携带退出条件。

## A7 — 设计 Recovery 与验证

Recovery Design（§65.5 [MUST][BASELINE] 高风险必有）：从 §33 手段中选定，并设计失败检测方式；长迁移设计 Restart / Recovery（§34）。Verification Plan：Postcondition（§36）+ 按风险的独立验证（§37：Validation Query / Script / Check 可重复执行；低风险纯 DDL 可以 Applied State + Integration Test 为足，归类携带理由——B1）；高风险用脱敏 Production-like Data 验证（§52）；适用时确认 Backup / Restore Readiness（§35、§49）。验证执行移交 SP-11 / SP-13，本规程定义"要证明什么"。

## A8 — 受控执行 Migration / Backfill

执行控制链：Precondition 检查（不满足优先阻止，§35）→ 受控执行（版本化 Artifact，不经无记录手工修改，§65.2）→ 运行 Observability（§53：Started / Progress / Rate / Error / Remaining / Lag / Resource / Paused / Completed）→ 需要时 Stop / Resume 且 Stop 后 Data State 仍合法（§54）→ Postcondition 证明（§36）→ 独立验证（§37）→ Migration Evidence 落盘（§62）。执行环境 / 时机与 SP-15 的 Release Path 编排对齐；本规程对"Migration 是否被正确执行与验证"负专业责任。

## A9 — Owner / Review 组织

明确 Data Change Owner 四方协调（§57：Data Meaning Owner / Application Owner / Migration Executor·Operator / Reviewer；小团队可兼任，高风险增 DBA·Platform / Security / Operations）。Review 按风险检查 §58 十五项（Meaning / Ownership / Current·Target·Transition / Schema Change / Existing Data / Compatibility / Backfill / Constraint / Migration Runtime / Failure / Recovery / Verification / Application Release Order / Consumer / Security·Privacy），Checklist 按 §66 适用性勾选，N-A 项携带理由（B1）。Review 执行归 SP-12。

## A10 — 移交边界与登记

- 数据设计 Material 到设计层 → 演进与兼容结论移交 **SP-05**（Transition 设计归 SP-05，本规程的 Migration / Backfill / Recovery 计划作为其输入）；
- 代码与 Migration Artifact 实现 → **SP-06**；
- 验证执行与 Candidate 结论 → **SP-11 / SP-12 / SP-13**；
- Release 编排与 Target 验证 → **SP-15 / SP-17**（Migration 执行窗口由其编排，执行控制归本规程）；
- Production Data Fix 走 §42 受控链（Incident / Defect → Fix Design → Scoped Fix Artifact → Review → 必要的 Backup / Verification → Execute → Evidence），Fix Artifact 是 Change Artifact，不是临时 SQL；
- Emergency Data Repair → **Ch8 + SP-21**（pending-definition，组5）压缩与事后对账，本规程的专业动作与真实数据状态 / 恢复证据不豁免（§43）；
- 过渡机制 / 双写 / 临时兼容结构携带 Exit Condition 登记，防永久化（§30、§29）。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Migration Artifact 版本化 / Applied State 记录 | Automation |
| Precondition / Postcondition 机械核验 | Guardrail |
| Additive / Destructive 识别、兼容组合定义、Recovery 设计 | Engineering Decision |
| Backfill 决策（允许为空 / 推导 / 修复） | Engineering Decision |
| Migration / Backfill 执行 | Automation + Guardrail（Precondition 阻止 / Observability / Stop-Resume） |
| Dual Write 采用与否、Exit Condition 判定 | Engineering Decision + Guardrail（四问 + 退出条件机械核验） |
| Review / 验证 / Release 编排执行 | 归 SP-12 / SP-11·13 / SP-15·17 |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP08-01 核心业务 Data 的 Meaning / Owner / Write Authority /
                     Invariant 必须明确，不得语义空白上设计演进（§65.1）
[MUST][BASELINE]    G-SP08-02 项目控制的 Schema / Out-of-band Data Change 必须经
                     Migration 或等价 Versioned / Auditable 机制管理，不得依赖
                     无记录 Production 手工修改；外部控制的至少版本化 External
                     Contract / Expected Schema / Compatibility Assumption /
                     Integration Change（§65.2）
[MUST][BASELINE]    G-SP08-03 Data Change 必须考虑 Existing Data——Backfill /
                     Null / Default / Historical Meaning 按适用性检查（§65.3）
[MUST][BASELINE]    G-SP08-04 非原子发布必须定义真实 Release Path 需要支持的
                     Old·New App × Schema 组合并验证；N-A 组合携带理由
                     （§65.4、§28）
[MUST][BASELINE]    G-SP08-05 高风险 Data Change 必须有 Recovery Design——
                     Forward Fix / Restore / Repair / Compensation 之一或组合；
                     不要求所有 Migration 都有简单 Down Migration（§65.5、§32-33）
[MUST][BASELINE]    G-SP08-06 Migration 必须有 Verification——exit code = 0 不得
                     作为高风险 Data Change 唯一完成证据（§65.6、§36-37）
[MUST NOT][BASELINE] G-SP08-07 Target / Proposed 提前覆盖 Current Data Baseline；
                     Migration 完成前 Target 不得冒充 Current（§61、§20，GI-05）
[MUST NOT][BASELINE] G-SP08-08 Dual Write 无 Owner / Exit Condition / Verification /
                     Cleanup，或无冲突 Source of Truth 定义（§30-31）
[MUST NOT][BASELINE] G-SP08-09 先改 Production 再补代码，或代码依赖尚未执行的
                     新 Schema（§21）
[MUST NOT][BASELINE] G-SP08-10 无依据的 gate-zeroing——"additive 零风险"假设、
                     "低风险纯 DDL"归类、N-A 组合、"Backup 存在即 Recovery 可行"
                     声明必须携带可解析理由，并可被 SP-05 / SP-13 / 组级审计
                     再挑战（B1、§22、§49）
```

---

# 7. PASS Exit

```text
设计分支（移交实现前）：
  Data Evolution & Execution Plan 成立（绑定 Current Data Baseline + Scope）：
    语义与所有权事实明确
  + Current / Target /（Transition）区分
  + 版本化 Migration / Backfill 计划 + 兼容组合定义
  + Recovery Design + Verification Plan
  → 移交 SP-05（Material 时）/ SP-06

执行分支（Migration / Backfill / Fix 执行后）：
  Precondition 通过 → 受控执行（Observability 全程）
  → Postcondition 证明 + 独立验证结论（移交 SP-11 / SP-13）
  → Migration Evidence 完整（§62）
  → 移交 SP-15 / SP-17 交付链
```

完成**不代表**：验证已通过 / Release 已完成 / Current Data Baseline 已更新 / Derived Data 已重建完成。

---

# 8. Evidence

Evidence by Work：

```text
Data Evolution Record（语义 / 所有权 / 判定依据）
版本化 Migration Artifact + Applied State 记录
Backfill 决策记录
Compatibility 组合与验证状态
Recovery Design + （适用时）Restore 验证事实
Migration Evidence（§62 十项）
Review Record（SP-12，Revision-bound）
```

只有 Backfill 决策、N-A 组合理由、低风险归类理由、Destructive 五问回答、Dual Write 四问与退出条件、Emergency 修复记录必须显式成文；其余证据随工作自然产生。

---

# 9. Current Update Obligation

本规程**不更新 Current**。Current Data Baseline 描述当前数据工程事实且必须带 Environment / Baseline Scope（§59-60）；Target Data Design 在 Migration 完成前不得提前覆盖 Current（§61）——故障处理人员依据 Current 判断真实 Database。Applied Migration State（§19）与 Migration Evidence（§62）是执行事实记录，不是 Current 改写；Current Data Baseline 的迁移在 Release / Baseline Transition 完成后显式走 **SP-19**。

---

# 10. FAIL / Return Path

```text
Precondition 不满足                → 阻止执行，回 A4 修复前置或调整方案；
                                     不得继续赌（§35）
Postcondition / 独立验证失败        → 按 Recovery Design 处置（§33），
                                     不得带着未解释的不一致进入交付
语义 / Owner 空白                  → 回 A2 补齐，不得语义空白上推进
兼容组合不可支持（Rollback / 旧 App）→ 回 A5 重定组合或调整 Release 编排（§28、§55）
Material 设计问题                  → SP-05
Dual Write 分叉且无冲突 SoT         → 停止双写推进，回 A6 补定义（§31）
Emergency Data Repair              → Ch8 + SP-21（pending-definition，组5）压缩路径；
                                     §43 记录链与本规程证据不豁免
```

---

# 11. Exception / Alternative Path

## 11.1 小型兼容 Schema Change

§64.1 轻量形态（新增 nullable internal field / 数据量小 / 单一 Application 使用）：Migration + Integration Test + Deployment Order Check 即可；"小型 / 兼容 / 单一使用"三个前提携带理由（B1）。

## 11.2 单一 Consumer 可原子协调

单一 Consumer + 可安排 Maintenance Window + 能原子协调 Application 与 Schema + 风险可接受时，直接 Rename / 一步变更可以是更简单的正确方案（§24）——按真实 Compatibility Requirement 决定，不机械套用 EMC。

## 11.3 Emergency Data Repair

严重事故可走 Fast Path（§43）：Emergency Approval → Minimal Safe Fix → Verify → Record → Post-facto Review → Change Record / Evidence 补齐 → 必要时更新 Migration / Baseline。压缩执行与事后对账归 Ch8 + SP-21（pending-definition，组5；落地前按 Ch8 正文执行）；Fast Path 不能无痕。

## 11.4 低风险纯 DDL 的验证裁剪

低风险纯 DDL 可以 Migration Tool 的 Applied State + Integration Test 为足够验证（§37），不为形式制造大量 Validation Script；"低风险纯 DDL"归类携带理由（B1），且不得用于数据转换型 / 破坏性 Change。

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05

Part II:
Ch8 数据要求 全章——本规程的 WHAT Authority
（§2 概念分层、§4-8 语义与所有权、§9-15 Constraint 与语义细节、
 §16-19 版本化与 Applied State、§20-24 Current/Target/Transition 与
 变更类型、§25-31 Backfill 与过渡机制、§32-37 Rollback/Recovery 与验证、
 §41-43 Reference Data / Production Fix / Emergency、§44-56 共享与运行风险、
 §57-58 Owner 与 Review、§59-62 Current Data Baseline 与 Evidence、
 §64 三类场景、§65 Minimum Requirements、§66 Checklist）
Ch7 §13（数据跨边界后的 Contract 面前置，归 SP-07）
注：Ch8 §43 / §68 正文中引用的第五篇编号为旧 lineage（SP-22 Emergency、
SP-23 / SP-24、SP-25~27 Calibration）；按 SP-22 封顶口径：SP-22→SP-21
（组5 pending）、SP-25~27→SP-19；SP-23 / SP-24 在封顶体系中无定义来源，
不预留、不引用（总索引 §1 编号权威）。

Part III:
Data / Shared Infrastructure / Runtime Mapping（Ch6 Data·Infra·Runtime 面）

Part IV:
Ch3（Data / Migration Impact 由 SP-04 产出，本规程深化）
Ch4（Transition 设计承接——Migration / Backfill / Recovery 计划作为 SP-05 输入）
Ch5（Migration Artifact 实现与同步）
Ch7（Migration 执行窗口纳入 Release 编排，SP-15 / SP-17）
Ch8（Emergency Data Repair 压缩路径）

Journey:
JG-04 Data / Migration Journey
```

---

# 13. Executable Asset References

```text
EA-09 Migration / Contract Template   Migration / Backfill 骨架、Precondition /
                                      Postcondition / compatibility 验证模板
EA-08 Verification Harness            Validation Query / 独立验证的确定性执行载体
EA-17 Current Navigation              Current Data Baseline / Applied Migration
                                      State 可发现性
```

工具适合：Applied State 记录、Precondition / Postcondition 机械核验、Validation Query 执行、Observability 采集、Migration 编排执行。
工具不适合：Backfill 决策、兼容组合定义、Recovery 设计、Destructive 五问判定、Dual Write 采用决策。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Migration 载体 = Alembic（版本化 + Applied State）；Backfill = 受控 Batch Job
  Current Data Baseline = data authority 文档 + alembic head + backfill 状态记录
  高风险验证 = 脱敏 Production-like 副本；Observability = Job 进度 + 数据库指标

RP-B-CLI（pending-definition，组6）:
  持久数据面 = 本地状态文件 / 嵌入式 DB（如 SQLite）；Schema 版本化随包发布
  兼容组合 = 新版 CLI + 旧本地状态（升级路径）；Rollback 兼容按安装形态裁剪

RP-C-SDK（pending-definition，组6）:
  通常无自有持久数据权威；携带本地存储 / 缓存 Schema 时：版本化 + 升级路径
  + 旧版本可读性定义；Consumer 不可控 → 存储格式演进按最保守判定
```

---

# 15. Example

**CHG-WO-142（工单转派能力升级）的数据演进——C9 契约束背后的 V203 Migration。**（承接 SP-07 示例：transfer API 增加 reason 的兼容演进判定完成后，数据侧的专业动作；同一 Change 的 Candidate / 交付 / Closure 见组3 各规程示例。本示例对应 P2 Ch8 §64.2 的"WorkOrder 增加 Transfer Reason"标准业务 Data Change。）

```text
A1 触及面：work_order 表新增 transfer_reason（Schema Change）——定位 §64.2
   标准业务 Data Change
A2 语义事实：reason = 结构化载荷 {category：取自 Config 驱动的允许值清单
   （SP-09 A7 移交的 Config Schema 事实）；note：自由文本，其中 internal 部分
   不出边界（SP-10 A3 序列化过滤）}，以序列化形态承载于 transfer_reason 列
   （空 = 旧数据无记录要求 / 新数据可选，Null 语义显式登记 §12）；
   Owner = WorkOrder Module；Write Authority = 仅 work-order-service；
   Authoritative Source = PostgreSQL 主库；Search Index 中的 reason 副本 =
   Derived（可重建，Refresh = Event 驱动）
A3 Current/Target：Current = 无 reason 列；Target = 含 nullable reason 列；
   无并存改名需求 → 无需 Transition Schema；Additive 判定成立但按 §22 检查
   运行风险（无 Default 触发 Rewrite；新 Index 本 Change 不涉及）
A4 Migration 设计：V203 = ADD COLUMN transfer_reason TEXT NULL（版本化，
   Identity / Dependency 明确）；列级 Backfill 决策 = transfer_reason 历史行
   允许为空，不推导、不设默认值、不人工修复——决策与理由成文（§25、§65.3），
   范围仅限该列；Search Index 历史行回填是独立工作面：S5 reindex Backfill 按
   Production Workload 设计（§27、§53-54）——Batch / Rate Limit / Pause·Resume
   （SP-15 示例 Recovery R1 的 "backfill pause" 对象即此）/ Checkpoint / 对账
   （完成后供 SP-17 示例 "migration reconciliation complete" 消费）；
   Precondition：Expected Current Version = V202、目标库 PostgreSQL 版本
   Lock 行为确认（§50）
A5 兼容组合：Old App + New Schema（旧版不写不读 reason 列 → 支持，验证状态 =
   待执行——执行移交 SP-11 / SP-13）；
   New App + Old Schema 不出现（部署顺序：Migration 先于 App 部署 → N/A，
   理由 = Release Path 编排保证，B1）；Rollback App + New Schema = 同
   Old App 组合 → 支持
A7 Recovery 与验证：低风险 Additive → Recovery = Restore 就绪确认 +
   Forward Fix 预案；Verification = Postcondition（Schema = expected）+
   Integration Test（reason 写入 / 读取 / 空值语义）→ 移交 SP-11 / SP-13
A8 执行：Precondition 通过 → V203 执行（秒级，Observability 记录）→
   S5 reindex Backfill 受控执行（Batch / Pause·Resume / 对账，§53-54）→
   Postcondition 证明 → Migration Evidence 落盘（§62）
   ——与 SP-07 的判定闭环：API 层 reason optional 兼容（SP-07 A3）与
   数据层 nullable 演进（本规程）共同支撑"业务终态 reason required 不在
   本 Change 无声推进"
```

---

# 16. 最终原则

> **代码可以替换，数据必须演进。真正安全的数据变化，不是一次没报错的 SQL，而是让新旧软件、历史数据、Schema、验证和恢复在整个 Change 生命周期中保持一致：语义有 Owner，演进有版本，存量有决策，失败有 Recovery，执行有证据，Current 有真相。不要把数据库当成软件工程流程之外的黑盒，也不要把 Migration 当成一次 SQL 执行。**
