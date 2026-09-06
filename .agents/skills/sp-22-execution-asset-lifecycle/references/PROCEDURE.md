# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-22 Execution Asset Lifecycle

> 类型：Specialized Procedure  
> 状态：SEALED（2026-09-01：组6 Independent Concept Audit PASS AFTER REPAIR（P1×4 已修复并复验 4/4 PASS）+ 横向回归 PASS AFTER REPAIR（R×3 已修复并复验、N×5 已修复）；证据见组6 审计报告与横向回归报告）  
> 单一职责：把 Guide / Template / Workflow / Script / Reference Profile / Operation Contract Schema 这类**执行资产**自身的治理组织成与软件同构的受控生命周期——为每个资产登记七要素身份（Owner / Version / Compatibility / Tests / Consumers / Deprecation / Replacement-Migration），把资产修改作为正常 Engineering Change 走同一 Change Loop，判定资产版本的兼容性与 Consumer 影响，维护 Guide Current Surface（哪些资产版本有效 / 哪些已 superseded / Mirror 是否同步），处置 Guide Drift，并用 Golden Path Regression 证明资产真实可用。核心事实为 Current Asset Version。  
> Execution Asset 的修改本身是 Engineering Change——"只是改个模板 / 脚本 / 文档"不构成绕过 Change Loop 的理由；无七要素登记的资产不得被 Consumer 引用；Publication Mirror 与 Research Evidence 都不因"存在"而自动取得规范地位。  
> 结构化镜像：`第五篇-SP22-ExecutionAssetLifecycle-OperationContract.yaml`

---

# 1. Trigger

```text
A. 新资产创建：项目 / 组织首次产出可复用执行资产——Template Repo、
   Reusable Workflow、Guide 文档、Reference Profile、Operation Contract
   Schema、脚本集——需要登记与发布
B. 资产修改请求：使用中发现缺陷（模板生成即坏、workflow 步骤失效）、
   依赖 / 平台漂移（GitHub Actions runner 变化、工具版本 EOL）、
   规范演化（下游 SP 修订导致资产过时）、反馈环证据（真实使用暴露的
   断裂点）
C. 资产版本发布与 Consumer 迁移：新版本产生，需要兼容性判定与面向
   consuming projects 的受控 rollout（含 breaking 变更的迁移计划）
D. 资产退出 / Supersession / Guide Drift 处置：资产被替代、下线、
   或发现同一 Concern 出现冲突的非 owner 表面
   ——任一 JG 的资产反馈均可触发（全链通用，非单一 Journey 专属）
```

红线：**资产的修改是 Engineering Change**（GI-03）——不存在"文档 / 模板 / 脚本可以随手改"的第二条路径；**资产无七要素登记不得被引用**；**Guide Current Surface 必须可回答 P1 §10.2 五问**——"哪个版本有效"回答不了时，Consumer 已经在追随漂移。

不触发本规程的情形：

```text
资产修改的 Change 开立与基线绑定          → SP-03（资产 Change 与软件
                                           Change 同一开立面）
资产兼容性的四视角判定框架                → SP-07（资产对 Consumer 是
                                           Contract，兼容语义复用，不重定义）
资产内容的具体实现                        → SP-06
资产的本地 / 候选验证框架                 → SP-11 / SP-13
资产 Change 的交付与 rollout 执行控制     → SP-15
Deprecation / EOL / Retirement 三分离的
  定义域                                  → SP-20（资产退出同构复用其语义，
                                           本规程登记资产侧事实）
资产紧急修复的压缩执行与事后对账          → SP-21（同一压缩模型）
Consumer 项目自身的项目级 Current 更新    → SP-19（各项目自己的 Closure 面）
被治理资产所描述的软件语义本身            → 各篇 designated semantic owner
                                           （本规程管资产，不管资产承载的
                                           专业语义，GI-11）
```

---

# 2. 输入

```text
资产触发事实                         反馈环证据（使用断裂点、缺陷报告、
                                    依赖 Advisory）、平台 / 工具漂移信号、
                                    规范演化输入（SP 修订引发的过时面）
资产现状                             Asset Registry：现存资产清单、版本、
                                    七要素状态、Deprecation 状态
Consumer 影响面事实                  哪些项目引用哪个版本（workflow asset
                                    version pin、template instantiation、
                                    profile 引用）——影响事实，非判定
资产接口事实                         资产对 Consumer 暴露的接口面：check 名、
                                    命令、目录约定、schema 字段、生成物
                                    结构（兼容判定的对象）
验证基础事实                         Golden Path / sample repo / regression
                                    matrix 现状（EA-19 面）
```

入口再挑战义务（B1 系统性规则）：上游使 Gate 归零的归类——"只是文档不用走 Change"、"内部模板没人用不用验证"、"脚本改一下不影响别人"、"audit 报告写了就当规范了"——必须携带可解析理由；没有理由或理由不成立的，按本规程对应 Trigger 处置。

---

# 3. 输出

```text
Asset Registry 条目（新增 / 更新）    七要素：Owner / Version /
                                   Compatibility / Tests / Consumers /
                                   Deprecation / Replacement-Migration
Asset Change                        经 SP-03 开立的正常 Engineering
                                   Change（携带资产触发事实与影响面）
资产兼容性判定 + Consumer 迁移计划   兼容 / Breaking 判定（复用 SP-07
                                   四视角语义）；Breaking 时逐 Consumer
                                   的迁移路径与时限
资产版本发布与 rollout 记录          渐进发布（opt-in → 渐进 → 默认）、
                                   可回退策略、版本 pin 事实（禁无策略
                                   @main）
Guide Current Surface 更新          有效版本 / superseded 版本 /
                                   Mirror 同步状态 / registry 核验时间
                                   （P1 §10.2 五问的答案）
Guide Drift 登记与修复记录          非 owner 表面冲突的登记 → 修复 →
                                   跨篇回归（GI-12）
Golden Path Regression 证据         资产在 sample / matrix 上真实可用：
                                   能找到、能执行、Gate 真拦截（§G）
资产反馈 backlog                    真实使用证据转化成的资产改进项
```

本规程**不输出**：

```text
Change 开立 / Starting Baseline      → SP-03
兼容性判定框架本身                   → SP-07
资产实现修改                         → SP-06
本地 / 候选验证判定                  → SP-11 / SP-13
rollout 执行控制（Authority / Slice）→ SP-15
Deprecation / EOL / Retirement 定义 → SP-20
Emergency 压缩语义                   → SP-21
Consumer 项目级 Current              → SP-19
资产承载的专业语义修订               → 各篇 designated owner
```

---

# 4. 核心语义

**Execution Asset 与软件同构（GI-03 + 总地图 §D）**：Template、Workflow、Guide、Profile、Schema 都是会被许多项目消费、会演化、会损坏、会过时的工程制品。它们不因为"是文档 / 是配置"就获得更宽松的治理——每个资产必须七要素可解析：**Owner / Version / Compatibility / Tests / Consumers / Deprecation / Replacement-Migration**。"everyone copies 一份自己改" 是资产的死亡：没有 Consumer 事实就没有兼容性可言，资产漂移成 N 份无主副本。

**资产修改走同一 Change Loop**：资产 Change 与软件 Change 用同一 Identity / Baseline / Authority / Evidence 模型（Ch1 总则）。可以裁剪的是各 SP 的适用深度（B1 理由成文），不可删除的是 Identity / Owner / 验证 / 记录。规范自身的修订（本指南各篇）同样如此——第五篇各 SP 的修订是 Change，SEALED 状态翻转是显式的版本事件，不是无声编辑。

**资产对 Consumer 是 Contract（复用 SP-07 语义）**：workflow 的 check 名、模板的目录约定、schema 的字段、命令的输出格式都是 Consumer 依赖的接口面。资产版本升级必须作四视角兼容判定；Breaking 资产变更 = Contract Breaking Change——需要迁移计划、过渡期与逐 Consumer 处置，而不是"push 了新版本，用的自己适配"。`@main` 无版本引用一个被所有项目消费的资产，等于把全组织的 CI 押在一个无人承诺的移动目标上。

**Guide Current Surface ≠ Project Engineering Current（P1 §4.5）**：哪些规范源 / 索引 / 资产版本当前有效，是与任何具体项目的工程 Current 完全不同的治理面。它必须能回答（P1 §10.2）：当前哪些 normative source 有效、哪些 index 有效、哪些已 superseded、publication mirror 是否与 current 同步、source registry 最近何时核验。**Publication Mirror 不得反向创造或覆盖 Normative Current Source**（GI-13）——合并版、门户、搜索视图只是镜像；**Research / Audit Evidence 是 point-in-time 证据**（GI-14）——研究报告不因"更新 / 更详细"自动成为规范正文。

**Guide Drift 必须登记并修复（GI-12）**：同一 Concern + Scope 出现冲突的非 owner 表面（旧索引与新索引并存、摘要与正文相抵、"更靠后的文件"被当作权威），不得静默并存——登记 Guide Drift → 修复 non-owner 面 → 跨篇回归。不存在按篇号 / 时间 / "更具体"自动决定谁覆盖谁。

**Golden Path Regression 证明资产真实可用（总地图 §G）**：资产的"可用"不是作者声称，而是可证明：developer can find it / execute it、Current 与 Authority 输入可发现、必需输出产生、Evidence 被捕获、Hard Gate 真拦截、人工决策不被静默自动化、资产有版本、有回归测试。模板要 generate+build 通过，workflow 要在 sample repo 上真实运行，schema 要被真实 contract 校验——通过标准是工程结果，不是"看起来对"。

**反馈环闭合（总地图 §J）**：真实执行产生的 Evidence / Engineering Facts 是资产改进的第一输入——Golden Path 在哪断、哪个 Gate 拦错了人、哪个模板生成即坏，都应回到资产 backlog。规范 / 资产与真实工程之间没有反馈环，规范就会 Drift 成纸面正确。

---

# 5. Engineering Actions

## A1 — 资产身份确认与 Registry 登记

确认触发面对应的资产与版本：新资产进入 Asset Registry（七要素逐项登记）；既有资产核对登记是否漂移（无 Owner / 无 Version / Consumers 未知——按资产债务处置）。无七要素登记的资产不得被 Consumer 引用；"内部资产不用登记"是 gate-zeroing 判断，携带理由（B1）。

## A2 — 资产修改作为正常 Change 开立

把修改请求转成 Asset Change（SP-03）：携带触发事实、影响面（哪些 Consumer / 哪个版本）、修改意图。资产 Change 的 Scope 显式包含资产本身与受影响 Consumer 的迁移义务。B1 再挑战："只是文档"不成立——文档是资产，资产是 Change。

## A3 — 兼容性判定与 Consumer 影响

对资产接口面（check 名 / 命令 / 目录 / schema 字段 / 生成物结构）作四视角兼容判定（复用 SP-07 语义，不重定义）：兼容则允许原地升级路径；Breaking 则产出逐 Consumer 迁移计划（路径 / 时限 / 支持期）。Consumer 影响事实来自 Registry 的 Consumers 项——没有 Consumer 事实的兼容判定是空转。

## A4 — 资产版本发布与受控 rollout

资产新版本发布渐进推进（opt-in → 渐进 → 默认新 Consumer → 存量迁移），每步可回退；rollout 执行控制归 SP-15。版本引用必须 pin 到可承诺的版本（`@v3` / digest），**禁无策略 `@main`**。Breaking 资产变更的过渡期：旧版本保持可用至迁移完成（Deprecation 语义复用 SP-20），有期限、有 Owner。

## A5 — Golden Path Regression 验证

按资产类型组织回归验证：Template → generate + build；Reusable Workflow → sample repo 真实运行；Contract Schema → 真实 contract 校验 + shape conformance（CLI / SDK / Service 形态至少覆盖目标面）；Guide 资产 → 导航可解析（链接活、Current 可发现）。通过标准是总地图 §G 十问，不是作者自评。验证框架复用 SP-11 / SP-13，本规程持有资产特定的回归清单。

## A6 — Guide Current Surface 维护

每次资产版本事件后更新 Guide Current Surface：有效版本、superseded 版本（含 supersession 事实——Successor 是谁、旧版本何时停止）、Mirror 同步状态、registry 核验时间。五问可回答是硬条件；回答不了时先修导航再谈新版本。

## A7 — Guide Drift 处置

发现同一 Concern 的冲突非 owner 表面（旧索引、过时摘要、并存副本）→ 登记 Guide Drift → 修复 non-owner 面（指向 designated owner，不折中、不并存）→ 跨篇回归确认无第二语义。supersession 遵循 Ch8 §58：不是"Cancelled + 一个备注链接"——必须撤销旧表面的 Authority，Successor 明确可追。

## A8 — 资产反馈环维护

把真实使用证据（Golden Path 断裂点、Gate 误拦、模板缺陷、规范过时面）收进资产反馈 backlog，按维护优先级排期（信号进入 SP-20 域的挂账面）；高价值反馈转 A2 开立 Asset Change。反馈环的 Evidence 引用真实工作事实（GI-06），不是"大家觉得"。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Asset Registry 维护 / 版本事件记录 | Automation |
| Guide Current Surface 状态呈现 | Automation |
| Golden Path Regression 执行 | Automation + Guardrail |
| 兼容性判定 / Breaking 判定 | Engineering Decision |
| rollout 策略 / 迁移时限 | Engineering Decision |
| Guide Drift 处置 / supersession 决定 | Engineering Decision（GI-12 流程） |
| rollout 执行控制 | 归 SP-15 |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP22-01 Execution Asset 的任何修改必须作为受控
                     Engineering Change 走 Change Loop——不存在"只是
                     文档 / 模板 / 脚本"的第二条路径（GI-03、Ch1）
[MUST][BASELINE]    G-SP22-02 每个被引用的 Execution Asset 必须七要素
                     可解析：Owner / Version / Compatibility / Tests /
                     Consumers / Deprecation / Replacement-Migration
                     （总地图 §D）——无登记不得被 Consumer 引用
[MUST][BASELINE]    G-SP22-03 资产版本升级必须作兼容性判定与 Consumer
                     影响处置（接口面四视角，复用 SP-07 语义）——
                     Breaking 资产变更必须有逐 Consumer 迁移计划
[MUST][BASELINE]    G-SP22-04 资产引用必须 pin 到可承诺版本，rollout
                     渐进可回退——被多项目消费的资产禁无策略 @main
                     引用
[MUST][BASELINE]    G-SP22-05 Guide Current Surface 必须回答 P1 §10.2
                     五问（有效源 / 有效索引 / superseded / Mirror
                     同步 / registry 核验时间）
[MUST][BASELINE]    G-SP22-06 Publication Mirror 不得成为第二套规范源
                     （GI-13）；Research / Audit Evidence 不因存在或
                     更新自动取得规范地位（GI-14）——只有显式纳入
                     Current Baseline 的规则获得规范地位
[MUST][BASELINE]    G-SP22-07 Guide Drift 必须登记、修复并回归，不得
                     静默并存冲突语义；supersession 必须撤销旧表面
                     Authority 且 Successor 明确（GI-12、Ch8 §58）
[MUST][BASELINE]    G-SP22-08 资产"可用"必须由 Golden Path Regression
                     证明（§G 十问）——模板 generate+build、workflow
                     sample repo 真跑、schema 真实 contract 校验，
                     不是作者自评
[MUST NOT][BASELINE] G-SP22-09 无依据的 gate-zeroing——"只是文档"、
                     "内部资产没人用"、"脚本改一下没事"、"报告写了
                     就是规范"归类必须携带可解析理由，并可被 SP-05 /
                     SP-13 / 组级审计再挑战（B1）
```

---

# 7. PASS Exit

```text
Execution Asset 义务完成（绑定 Asset Change）：
  资产七要素登记齐全且与真实状态一致
+ Asset Change 走完适用 SP 链（开立 SP-03 → 实现 / 验证适用 SPs →
  交付 SP-15）
+ 兼容性判定与 Consumer 影响处置成文（Breaking 时含逐 Consumer 迁移
  计划与时限）
+ Golden Path Regression 证据在案（§G 十问对应的实际验证）
+ Guide Current Surface 已更新（含 supersession 事实）
→ 资产反馈 backlog 更新；Consumer 项目迁移义务移交各项目正常链
```

完成**不代表**：所有 Consumer 已迁移到新版本 / 资产退出生命周期已完成（Deprecation 过渡期语义归 SP-20）/ Consumer 项目的 Current 已更新（各项目 SP-19）/ 资产承载的专业语义已修订（归各篇 designated owner）。

---

# 8. Evidence

Evidence by Work：

```text
Asset Registry 条目（七要素 + 版本事件）
Asset Change 记录（触发事实 + 影响面 + 修改内容）
兼容性判定与 Consumer 迁移计划
资产版本发布与 rollout 记录（版本 pin 事实）
Guide Current Surface 状态（含 registry 核验时间）
Guide Drift 登记与修复记录
Golden Path Regression 运行证据
```

只有 gate-zeroing 归类理由（只是文档 / 内部资产 / 脚本没事）、Breaking 判定理由、supersession 决定、迁移时限决定必须显式成文；其余证据随工作自然产生。

---

# 9. Current Update Obligation

本规程**不写 Project Engineering Current**。Asset Registry 与 Guide Current Surface 是独立于任何项目工程 Current 的治理面（P1 §4.5：Guide Current Surface ≠ Project Engineering Current），由本规程直接维护；资产变更引发的 consuming projects 项目级 Current 变化归各项目自己的 SP-19；规范正文（各篇）的修订走各篇 designated owner 的修订 Change。

---

# 10. FAIL / Return Path

```text
资产修改被判定 Material 设计问题         → SP-05（资产架构 / 接口重设计）
兼容性判定为 Breaking 且无迁移可行路径   → 重开版本策略（新 Major /
                                        过渡双轨）；必要时 SP-07 迁移
                                        语义咨询
Golden Path Regression 失败             → 修复资产（回 SP-06）——
                                        不得带伤发布"下版再修"
Consumer 迁移超期 / 无人认领             → 资产债务登记（挂 SP-20
                                        维护优先级面）；旧版本支持期
                                        不得无声续期
资产触发源于下游 SP 修订过时             → 规范演化输入 → 对应 SP 的
                                        修订 Change（本规程不修专业语义）
Guide Drift 修复牵涉跨篇语义             → GI-12 流程（concern + scope
                                        解析 owner → 修复 → 跨篇回归），
                                        不得篇内私了
资产紧急修复（模板坏在生产路径上）       → SP-21 同一压缩模型 +
                                        强制事后对账；本规程不发明
                                        旁路
```

---

# 11. Exception / Alternative Path

## 11.1 单 Consumer 资产

只有唯一 Consumer 的资产（团队自用脚本 / 单项目模板）可裁剪 rollout 深度（无渐进阶段、无正式迁移计划），但七要素登记、Change 开立、验证义务不裁剪——裁剪的是发布面，不是治理面（GI-09）。归类携带理由（B1）。

## 11.2 资产 Supersession 过渡期

被替代资产的旧版本在过渡期与 Successor 并存是合法的：并存必须有期限、有迁移路径、旧版本 Deprecation 状态显式；过渡期内新 Consumer 一律走新版本。旧表面的 Authority 在 supersession 决定生效时撤销（Ch8 §58），不是"留着当备份"。

## 11.3 Schema 冻结形态

Operation Contract Schema（EA-18）这类被全部契约投影依赖的资产可采用冻结策略：冻结期内字段只增不改（向前兼容承诺），Breaking 变更须开新 apiVersion 并为旧版本保持发布。冻结决定本身是 Asset Change，登记于 Registry。

## 11.4 组织级资产与小团队形态

无独立 platform 工程团队的小团队：资产 Registry 可以就是仓库里的一个受控清单文件 + CODEOWNERS；Golden Path 可以是 CI 里的一个 sample job。载体可裁剪，七要素、Change 模型、验证义务不可裁剪（P2 Ch1 §4.3 最低工程要求同理）。

---

# 12. Theory Trace

```text
Part I:
GI-03（任何 Engineering Change 必须受控——资产不例外）、GI-06、
  GI-11（资产承载的专业语义归 designated owner）、GI-12（Guide Drift
  登记修复）、GI-13（Publication Mirror 非规范源）、GI-14（Research
  Evidence 是 point-in-time）、GI-17（Applicability 不静默丢弃）；
  §4.5 Guide Current Surface、§10.1 Asset Classes、§10.2 五问

Part II:
Ch1 §2 / §4.3（工程基础与最低工程要求——资产是项目工程能力的一部分）、
  §16.3（长期 Drift 防护）；Ch12（Maintenance——资产同为维护对象，
  优先级与挂账语义）

Part III:
Ch5 Source / Build Structure（资产在源码中版本化、可构建、可追踪）、
  Ch8 Current Structure / Drift（资产有效版本的 Current 语义与
  Drift 防护）

Part IV:
Ch1（Change Execution 总则——asset changes 走同一 Change Loop）、
  Ch2（Establishment / Baseline Binding）、Ch8 §58（Superseded
  不是备注链接——资产 supersession 语义）、Ch9（Closure / Current）

Journey:
全链通用（任一 JG 的资产反馈触发；J 最终主模型的 Guide / Asset
  Feedback Loop 收口点）
```

---

# 13. Executable Asset References

```text
EA-18 Profile Manifest          资产身份 / profile 元数据与 conformance
EA-19 Golden Path Regression    资产回归验证（generate → deploy 链）
EA-01 Execution Navigation      资产可发现面（链接可解析）
EA-17 Current Navigation        资产有效版本的权威解析面
```

工具适合：Asset Registry 维护、版本事件记录、Golden Path CI job、supersession 状态呈现、Guide Current Surface 面板。
工具不适合：兼容性 / Breaking 判定、supersession 决定、Drift 修复裁决——工具显示"最新版本"不是"当前有效版本"的判定器（GI-07）。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  组织级资产形态 = org/engineering 仓库的 reusable workflow + template；
  版本引用 pin @v3 / immutable SHA（禁 @main）；Golden Path = sample
  repo CI matrix；Asset Registry = 仓库受控清单 + CODEOWNERS；
  合并阅读视图（完整版）为 Publication Mirror，不作为修改入口

RP-B-CLI（已随组6 落定：
  第五篇-ReferenceProfile-CLI-PythonTyper-GitHub.md）:
  资产面 = template repo / 发布通道 / 安装脚本；无服务端 rollout——
  版本发布即分发，"渐进"由通道与 cohort 承载（同 SP-16 Version
  Exposure 语义）；已分发副本不可撤回，Breaking 迁移义务更重

RP-C-SDK（已随组6 落定：
  第五篇-ReferenceProfile-SDK-PythonLibrary-GitHub.md）:
  资产面 = 库模板 / 发布流程 / consumer 迁移指南；已发布版本不可
  撤回；资产 Consumer = 下游开发者，迁移跟踪以 Adoption 观察承载
```

---

# 15. Example

**org/engineering 的 `python-ci` reusable workflow v3 → v4 升级——Execution Asset 全生命周期。**（承接组1 RP-ONLINE-API-PY-GH §12 的版本 pin 事实与 CHG-WO-142 项目链：work-order-service 以 `org/engineering/.github/workflows/python-ci.yml@v3` 消费该资产。）

```text
A1 身份确认：Registry 现状——python-ci@v3，Owner = platform 团队，
   Consumers = 12 个仓库（含 work-order-service），Tests = sample
   repo matrix，Deprecation = 未定。触发事实：sample job 在新版
   runner 上警告 + 规范要求 migration smoke 步骤（假设的 SP-08
   修订带来的语义演化输入——Trigger B 规范演化面的示例设定，
   非现行 SP-08 内容）——资产过时面成立
A2 Change 开立：AST-CHG-014（Asset Change，SP-03）——Scope =
   python-ci 资产本身 + 12 Consumer 的迁移义务。B1 再挑战
   "只是改 workflow"：不成立——12 个仓库的 CI 依赖此资产接口
A3 兼容判定：接口面 = check 名 `verify`（不变）、新增 migration
   smoke 步骤（可选开启）。四视角判定：对现有 Consumer 兼容
   （新步骤 opt-in）；对开启 migration smoke 的 Consumer 行为
   变化——判定为"兼容 + 可选增强"，非 Breaking；若未来改
   check 名 = Breaking，须逐 Consumer 迁移
A4 发布与 rollout：v4 发布，v3 进入 Deprecation（期限 6 个月，
   复用 SP-20 语义）；rollout = workflow_dispatch opt-in →
   渐进迁移 → 新仓库默认 v4；执行控制归 SP-15；v3 在过渡期
   保持可用且不再接收修复
A5 Golden Path：sample repo matrix 上 v4 真实运行（generate →
   verify → migration smoke → build）；§G 十问核对——
   developer 能找到（EA-01）、check 名稳定、Gate 真拦截
   （故意失败分支被 block）
A6 Guide Current Surface：Registry 更新——python-ci 当前有效
   = v4；v3 = superseded（Successor = v4，停止时间 6 个月后）；
   组织门户资产页同步（Mirror 同步状态核对）；registry 核验
   时间登记
A7 Drift 处置：迁移期发现两个仓库私改 fork 的 python-ci-old
   副本仍在跑——登记 Guide Drift（同一 Concern 非 owner 表面），
   修复 = 指回 org 资产 + 私有步骤走参数化提案；不折中并存
A8 反馈环：迁移期 evidence——3 个仓库迁移卡在 self-hosted
   runner 差异 → 进资产 backlog，排期 v4.1（参数化 runner
   支持）；Golden Path 断裂点（sample 未覆盖 self-hosted）
   补进 matrix
```

---

# 16. 最终原则

> **规范约束软件，也要约束写规范的自己：模板、工作流、指南、Schema 都是资产——有 Owner、有版本、有 Consumer、有退出条件，才配被别人依赖。对资产的每一次"随手一改"，都是同时修改所有下游项目的执行环境；而无登记、无验证、无反馈环的资产，不是效率工具，是全组织共享的定时漂移。规范自己 Drift 了，它治理出来的一切都会跟着漂。**
