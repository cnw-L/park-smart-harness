# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-09 Dependency / Toolchain / Config Controlled Evolution

> 类型：Specialized Procedure  
> 状态：SEALED（2026-09-01：组4 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1712 处引用核验 PASS AFTER REPAIR（REPAIR-1 已修复）；证据见组4 审计报告与横向回归报告）  
> 单一职责：把一次触及 Dependency / Toolchain / Configuration 的变化，受控地完成专业演进——对依赖建立 Identity 与 Resolution 事实（为什么引入 / 哪个版本 / 谁拥有 / 传递依赖 / 风险），保证版本确定性与 Build Input 完整性，管理 Code / Config / Secret 三分与注入可追踪性，并把重要 Config Change 作为受控 Change 处理。  
> 同一个 Source Baseline 必须能确定实际使用的 Dependency Version，而不是每次 Build 随机解析；Config 自己同样属于受控工程事实；Secret 永远不是普通源码。  
> 结构化镜像：`第五篇-SP09-DependencyToolchainConfig-OperationContract.yaml`

---

# 1. Trigger

```text
A. Change 引入 / 升级 / 移除重要 Dependency，或改变 Dependency Resolution 机制
   （Lock / Manifest / Repository / Checksum）——JG-05 主线：SP-09 → SP-10
B. Toolchain / Build 工具 / Generator 变化（Compiler、Build Tool、Codegen 版本与
   来源，Ch11 §6、Ch9 §25）
C. Configuration / Secret 面变化：新增配置项、改变注入方式、Config 与 Artifact
   关系调整、重要 Config / Flag Change 本身（Ch9 §19-20、Ch11 §16-17/§42）
D. Dependency / Config 债务治理：过期依赖、永久 Pinned、无人拥有的依赖、
   隐藏在源码分支里的环境差异（Ch9 §19、§23）
```

红线：**Secret 不得作为普通源码处理**——不 Hard-code、不 Commit、不进通用 Artifact、不入日志与 Error（Ch9 §20、Ch11 §17）；意外进入 Version History 不是删文件了事，必须 Rotation 与安全处置（处置归 SP-10）。

不触发本规程的情形：

```text
Security Control 执行（漏洞响应、Supply Chain 安全策略、Secret Rotation 处置）
                                      → SP-10；
                                        Ch9 §24 分工：SP-09 管 Dependency /
                                        Toolchain 的 identity 与 resolution，
                                        SP-10 管 security control，互不覆盖
Config / 依赖项作为跨边界承诺的兼容演进   → SP-07（Config Schema / 暴露给外部的
                                        Dependency Surface 已成 Contract 时）
实现执行（代码改动）                    → SP-06
验证执行与 Candidate 结论               → SP-11 / SP-12 / SP-13
Release / 部署编排 / Target 验证         → SP-15 / SP-17（Config Change 的发布
                                        执行由其编排，本规程定义受控要素）
Environment Current Runtime State 事实   → SP-15（执行期提交）/ SP-17（Accepted
                                        Release Ledger 面）；项目级 Current →
                                        SP-19（本规程不更新 Current）
```

---

# 2. 输入

```text
Dependency / Toolchain / Config Impact  SP-04：触及哪些依赖 / 工具链 / 配置面
当前 Dependency 事实                    Manifest / Lock / Resolved Version /
                                        Base Image / Toolchain 版本（Ch11 §6）
当前 Config / Secret 面                 配置项清单、注入方式、Secret Reference /
                                        Required Secret Schema / Injection
                                        Mechanism（Ch11 §26、Ch1 §7.3）
Build Definition 现状                   版本化 Build 定义（Ch11 §5、§86.2）
Generated Code 关系（适用）              Source Artifact / Generator+Version /
                                        是否 Commit / 怎样 Regenerate（Ch9 §25）
```

入口再挑战义务（B1 系统性规则）：上游使 Gate 归零的归类——"dev-only dependency 所以无风险"、"toolchain 按风险不需要确定"、"Config 变化不是 Release"、Internal-only 归类——必须携带可解析理由；没有理由或理由不成立的，退回 SP-04 处置。

---

# 3. 输出

```text
Dependency Decision Record   重要 Dependency Change 五问：Why needed /
                             Which version / Who owns usage / What transitive
                             dependency / What security·maintenance risk
                             （Ch9 §21）+ 收益与长期维护成本评估（§23）
Resolution / Build Input     同一 Source Baseline 可确定的 Dependency Version
                             机制（Lock / Resolved Version / Manifest /
                             Repository / Checksum，Ch9 §22、Ch1 §7.2）；
                             Build Baseline 的 Dependency / Base Image /
                             Compiler·Toolchain 面（Ch11 §6、§86.2）
Toolchain / Generator 登记    Toolchain 版本（按风险）；Generated Code 的
                             Source Artifact / Generator+Version / Commit
                             策略 / Regenerate 方式（Ch9 §25）
Config / Secret 治理事实      Code / Config / Secret 三分落实（Ch9 §19）；
                             Config 作为受控工程事实（Ch11 §16）；Secret 的
                             Reference / Schema / Injection 可追踪（Ch11 §26）
Config Change Record         重要 Config / Flag Change 的 Identity·Revision /
                             Change Reason / Authorization / Verification /
                             Target State（Ch11 §42）
Dependency / Config Debt     过期依赖 / 永久 Pinned / 无人拥有依赖 / 隐藏环境
                             差异——Risk + Owner + Cleanup Condition
```

本规程**不输出**：

```text
漏洞处置 / 安全策略执行 / Secret Rotation  → SP-10
代码实现                                   → SP-06
验证结论                                   → SP-11 / SP-12 / SP-13
Release / Deployment 事实                  → SP-15 / SP-17
Current 任何更新                            → SP-19
```

---

# 4. 核心语义

**Dependency 是 Implementation 的一部分（Ch9 §21）**：第三方 Library / Package 不是"顺手 install 一下"——它进入 Build / Runtime / Security Surface / License / Compatibility / Upgrade Path。重要 Dependency Change 必须能回答五问：Why needed / Which version / Who owns usage / What transitive dependency / What security·maintenance risk。**不要为了一个小工具引入巨大 Dependency**（§23）：parse one date format 不该换来 large framework + hundreds of transitive packages——收益与长期维护成本一起算。

**版本确定性（Ch9 §22、Ch1 §7.2、Ch11 §6、§86.2）**：不同生态用 Lock File / Resolved Version / Manifest / Artifact Repository / Checksum，本规范不强制所有语言都有 Lock File，但要求**同一个 Source Baseline 能够确定实际使用的 Dependency Version，而不是每次 Build 随机解析到不同版本**；依赖结果具备足够确定性（不强制具体工具）。Dependency 必须成为 Build Input：Build Baseline 不能只有 Git Commit，还必须能确定 Dependency Manifest / Resolved·Locked Dependency / External Base Image / Compiler·Toolchain（按风险）。**[MUST][BASELINE] 正式 Build 必须能够确定 Build Definition / Dependency·Base Image / 影响输出的 Build Parameter，不能依赖不可追踪的本地状态**（§86.2）。

**Code / Configuration / Secret 三分（Ch9 §19、Ch1 §7.3）**：Code = 稳定业务逻辑；Configuration = 环境可以变化的参数；Secret = 不能作为普通源码公开存储的敏感凭据。**环境差异不能长期隐藏在无法治理的 Source Code 分支里**。项目必须让开发人员知道：什么是普通配置 / 什么属于 Secret / 本地怎样获得 / CI·Production 怎样注入（Ch1 §7.3）。

**Config 是受控工程事实（Ch11 §16、§42、§26）**：Environment-specific Configuration 必须和 Artifact 分开（Same Package + Environment-specific Configuration），但**不能为了"Artifact 不变"就把 Production Config 变成无人管理的手工输入**。重要 Config / Flag Change 本身可能是一种 Release——Binary 没变但 Runtime Behavior 已变化——需要 Identity·Revision / Change Reason / Authorization / Verification / Target State（§42）。Environment 应尽量可从受控信息重建：Secret Value 本身不一定进 Version Control，但 Secret Reference / Required Secret Schema / Injection Mechanism 应该可追踪（§26）。

**Secret 永远不是普通源码（Ch9 §20、Ch11 §17）**：Password / Private Key / API Token / Credential / Signing Secret 不 Hard-code / Commit / Print to Log / Return in Error；不作为 Build-time Constant 永久写进可广泛分发的通用 Artifact——用 Artifact + Secret Reference / Runtime Injection。意外进入 Version History 需要 Credential Rotation 和相应安全处理（处置归 SP-10）。

**Generated Code 必须知道 Source 在哪里（Ch9 §25）**：Source Artifact / Generator·Version / Generated Output / 是否 Commit / 怎样 Regenerate 必须明确；**Generated Output 必须可追到 Generator Input 和 Process**——不要出现 Generated File 被手改而下次生成全部覆盖无人知晓。

**与 SP-10 的分工（Ch9 §24）**：Third-party Component 必须进入 Security Thinking（SSDF：可信、可维护、已知风险）；但 Software Supply Chain / Security Control 执行归 SP-10，Dependency / Toolchain 的 identity 与 resolution 归本规程，**二者不得互相覆盖**。

---

# 5. Engineering Actions

## A1 — 确认入口与触及面

从 SP-04 移交出发，枚举本 Change 触及的面：Dependency（引入 / 升级 / 移除 / Resolution 机制）/ Toolchain（Compiler / Build Tool / Generator）/ Config·Secret（配置项 / 注入方式 / Config-Artifact 关系）。执行 B1 再挑战：上游的"dev-only 无风险 / toolchain 不需确定 / 不是 Release"归类没有理由的，退回 SP-04。

## A2 — Dependency 引入 / 升级 / 移除决策

重要 Dependency Change 登记五问（Ch9 §21）+ 收益与长期维护成本（§23：Security Surface / Upgrade Cost / Build Cost / Conflict）。评估 Third-party Component 的可信 / 可维护 / 已知风险面（§24）——发现需要安全处置（已知漏洞响应、供应链策略判定）的，移交 **SP-10**，本规程不代替执行；Identity 与 Resolution 事实仍由本规程维护。

## A3 — 版本确定性与 Build Input

确认 / 建立版本确定性机制（Ch9 §22、Ch1 §7.2：Lock / Resolved Version / Manifest / Repository / Checksum 按生态选择，目标是同一 Source Baseline 解析确定）。把 Dependency / Base Image / Compiler·Toolchain（按风险）纳入 Build Baseline（Ch11 §6）；正式 Build 满足 §86.2 [MUST][BASELINE]——Build Definition / Dependency·Base Image / 影响输出的 Build Parameter 可确定，不依赖不可追踪本地状态。"按风险不需要确定 toolchain"是 gate-zeroing 判断，携带理由（B1）。

## A4 — Toolchain / Generator 治理

登记 Toolchain 版本与升级路径（按风险，Ch11 §6）。Generated Code 明确五要素（Ch9 §25）：Source Artifact / Generator·Version / Generated Output / 是否 Commit（按 Build / Tooling 选择）/ 怎样 Regenerate；保证 Generated Output 可追到 Generator Input 和 Process；手改 Generated File 的行为被识别并纠正。

## A5 — Config / Secret 分离与注入治理

落实 Code / Config / Secret 三分（Ch9 §19）：源码中的环境分支 / 硬编码值识别并迁移到受控 Config。Config 自身作为受控工程事实管理（Ch11 §16：Config 定义可追踪，不是无人管理的手工输入）。Secret 面（Ch9 §20、Ch11 §17、§26）：不进源码 / Artifact / 日志 / Error；建立 Secret Reference / Required Secret Schema / Injection Mechanism 的可追踪性；让开发人员知道本地 / CI / Production 的获取与注入方式（Ch1 §7.3）。发现 Secret 已进入 Version History → 移交 SP-10 做 Rotation 与安全处置，本规程登记事实。

## A6 — Config Change 作为受控 Change

重要 Config / Flag Change 按 §42 建立：Identity·Revision / Change Reason / Authorization / Verification / Target State。"这个 Config 变化不算 Release"是 gate-zeroing 判断，携带理由（B1）；重要与否按 Runtime Behavior 影响判断（Binary 没变 ≠ 没变化）。发布编排移交 **SP-15 / SP-17**；本规程保证受控要素齐全。

## A7 — 兼容与跨边界判定

判定 Dependency / Config 变化是否触及跨边界承诺：Config Schema / 暴露给外部的 Dependency Surface 已成 Contract 的 → 兼容演进移交 **SP-07**（本规程提供事实输入）；纯内部 Dependency / Toolchain / Config 演进留在本规程。判定携带理由（B1）。

## A8 — Review / 验证移交与债务登记

Dependency / Toolchain / Config 变化的 Review 归 **SP-12**（Dependency Decision Record 作为 Review 材料）；行为验证归 **SP-11 / SP-13**（版本确定性可经可重现 Build 抽查验证，执行归 SP-14 Build / Provenance 面配合）。登记 Dependency / Config Debt：过期依赖 / 永久 Pinned / 无人拥有依赖 / 隐藏环境差异——Risk + Owner + Cleanup Condition，防永久化。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Lock / Manifest / Checksum 解析与记录 | Automation |
| 版本确定性核验（同一 Baseline 重复解析比对） | Guardrail |
| Dependency 五问决策 / 引入移除判断 | Engineering Decision |
| Config / Secret 三分归类、Release 判定 | Engineering Decision（归类携带理由） |
| Secret 扫描 / 注入引用完整性检查 | Guardrail |
| Review / 验证 / 发布执行 | 归 SP-12 / SP-11·13·14 / SP-15·17 |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP09-01 同一 Source Baseline 必须能确定实际使用的
                     Dependency Version——不得每次 Build 随机解析（Ch9 §22、
                     Ch1 §7.2、Ch11 §86.2）
[MUST][BASELINE]    G-SP09-02 正式 Build 必须能确定 Build Definition /
                     Dependency·Base Image / 影响输出的 Build Parameter，
                     不依赖不可追踪本地状态（Ch11 §86.2、§6）
[MUST][BASELINE]    G-SP09-03 Secret 不得 Hard-code / Commit / 打进通用
                     Artifact / 入日志与 Error（Ch9 §20、Ch11 §17）
[MUST][BASELINE]    G-SP09-04 环境差异不得隐藏在无法治理的源码分支；Config /
                     Secret Reference / Schema / Injection 可追踪（Ch9 §19、
                     Ch11 §16、§26、Ch1 §7.3）
[MUST][BASELINE]    G-SP09-05 重要 Config / Flag Change 必须作为受控 Change：
                     Identity·Revision / Reason / Authorization / Verification /
                     Target State（Ch11 §42）
[MUST][BASELINE]    G-SP09-06 重要 Dependency Change 必须有五问记录（Why /
                     Version / Owner / Transitive / Risk，Ch9 §21）
[MUST NOT][BASELINE] G-SP09-07 Generated Output 脱离 Source——必须可追到
                     Generator Input 和 Process（Ch9 §25）
[MUST NOT][BASELINE] G-SP09-08 与 SP-10 互相覆盖——安全处置（漏洞响应 /
                     Rotation / 供应链策略）不得在本规程内代替 SP-10 执行，
                     identity / resolution 也不得由 SP-10 代管（Ch9 §24）
[MUST NOT][BASELINE] G-SP09-09 无依据的 gate-zeroing——"dev-only 无风险"、
                     "toolchain 按风险不需确定"、"Config 变化不是 Release"
                     归类必须携带可解析理由，并可被 SP-05 / SP-13 / 组级审计
                     再挑战（B1）
```

---

# 7. PASS Exit

```text
Dependency / Toolchain / Config Evolution Plan 成立（绑定 Source Baseline）：
  每触及依赖有五问记录与版本确定性机制
+ Build Input 面完整（Dependency / Base Image / Toolchain 按风险）
+ Config / Secret 三分落实，注入可追踪
+ 适用时：Config Change 受控要素齐全、Generator 五要素明确、跨边界判定有理由
→ 移交 SP-06（实现）/ SP-10（安全处置时）/ SP-15（Config Release 编排时）
```

完成**不代表**：漏洞已处置 / 验证已通过 / Config Change 已发布 / Current 已更新。

---

# 8. Evidence

Evidence by Work：

```text
Dependency Decision Record（五问 + 成本评估）
Lock / Manifest / Resolved Version 事实（版本控制内）
Build Baseline 的 Dependency / Toolchain 面
Config 定义与 Secret Reference / Schema / Injection 登记
Config Change Record（§42 五要素）
Review Record（SP-12，Revision-bound）
```

只有 gate-zeroing 归类理由（dev-only / 按风险不确定 / 非 Release）、跨边界判定理由、SP-10 移交事实必须显式成文；其余证据随工作自然产生。

---

# 9. Current Update Obligation

本规程**不更新 Current**。Dependency Manifest / Lock / Config 定义 / Build Definition 是版本控制内的工程事实，随实现与交付链演进；Environment Current Runtime State 的事实更新归 SP-15（执行期提交）/ SP-17（Accepted Release Ledger 面）；项目级 Current 更新归 SP-19，任何 Current Baseline 的正式迁移显式走 **SP-19**。

---

# 10. FAIL / Return Path

```text
版本确定性无法建立（生态 / 机制限制） → 选定等价确定性机制或升级 Toolchain；
                                      不得以"生态如此"放弃（Ch1 §7.2 只要求
                                      结果确定，不限工具）
Dependency 风险不可接受              → 替代方案 / 自研小工具 / 移除；安全面
                                      争议移交 SP-10
触及跨边界承诺                       → 兼容演进移交 SP-07（携带事实输入）
Secret 已进入 Version History        → 移交 SP-10 Rotation 与安全处置；
                                      本规程登记事实，不删除历史掩盖
Material 设计问题                    → SP-05
Config Change 发布编排失败            → SP-15 / SP-17 路径
```

---

# 11. Exception / Alternative Path

## 11.1 无 Lock File 生态

Ch9 §22 不强制所有语言都有 Lock File；但必须用 Resolved Version 记录 / 受控 Artifact Repository / Checksum 等等价机制达到"同一 Source Baseline 解析确定"。所选机制与确定性证据登记（B1）。

## 11.2 低风险 Toolchain 不确定

Compiler / Toolchain 纳入 Build Baseline 是"按风险"（Ch11 §6）；低风险项目可以不固定 Toolchain 版本，但归类携带理由，且 Release Artifact 可追踪到 Source 的底线（Ch11 §86.1）不受影响。

## 11.3 一次性内部工具

一次性 / 内部 Tool 的 Dependency 治理可按风险从简（五问口头化），但 Secret 三分与版本确定性底线不豁免；"一次性 / 内部"归类携带理由（B1）。

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05

Part II:
Ch1 §7.2 Dependency Lock、§7.3 Configuration 和 Secret 要分开（可运行能力面）
Ch9 §19-25——本规程的 WHAT Authority
（§19 Code/Config/Secret 三分与本规程归口、§20 Secret 禁令、§21 五问、
 §22 版本确定性、§23 依赖成本、§24 SP-10 分工、§25 Generated Code）
Ch11 §5-6（Build Definition 版本化 / Dependency 作为 Build Input）、
§16-17（Config 与 Artifact 分离 / Secret 不进 Artifact）、
§26（Environment 可重建 / Secret Reference 可追踪）、
§42（Config Change 是 Release）、§86.1-86.2（Build Minimum [MUST][BASELINE]）

Part III:
Source / Build / Runtime Mapping（Ch5 Source·Build、Ch3 Runtime 面对应关系）

Part IV:
Ch3（Dependency / Config Impact 由 SP-04 产出，本规程深化）
Ch5（实现期 Dependency / Generated Code 落实）

Journey:
JG-05 新增或升级 Dependency / Toolchain / Config 主线（SP-09 → SP-10）
```

---

# 13. Executable Asset References

```text
EA-10 Build Definition         版本化 Build 定义、Dependency 作为 Build Input、
                               可重现 Build 基线
EA-13 Environment / Secret     env config / secret binding 的注入与访问
EA-03 Dev Environment          Toolchain 版本固定与 clean setup 验证
```

工具适合：Lock / Manifest 解析记录、版本确定性重复解析核验、Secret 扫描、注入引用完整性检查、可重现 Build 抽查。
工具不适合：Dependency 五问决策、引入 / 移除判断、Config Release 归类、跨边界判定。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Dependency 确定性 = uv / pip-tools lockfile；Build Input = lockfile + base
  image digest；Config = env vars + 版本化 config 定义；Secret = 平台注入
  （Reference 可追踪）；Config Release 走与 Binary 相同的受控链

RP-B-CLI（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组6）:
  Dependency 确定性 = lockfile / vendoring；Config = 用户配置文件（路径与
  Schema 版本化）；Secret = OS keychain / 外部注入引用；无服务端环境面

RP-C-SDK（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组6）:
  Dependency 最小化最强——SDK 的依赖进入 Consumer 的依赖树（§23 权重最高）；
  版本范围声明替代 Lock（Lock 不传递给 Consumer）；Toolchain / Generator
  版本固定（发布可重现性归发布方负责）
```

---

# 15. Example

**CHG-WO-142（工单转派能力升级）的依赖 / 配置面——reason 能力落地伴随的三个专业动作。**（承接 SP-07 / SP-08 示例：同一 Change 的 Contract 与数据面已定；本例覆盖依赖引入、Generator 治理与 Config Change。）

```text
A2 Dependency 引入：transfer reason 需要结构化校验 → 评估引入轻量校验库。
   五问记录：Why = 避免手写校验漂移；Which = v3.4.x（Resolved 固定）；
   Owner = work-order-service 团队；Transitive = 2 个（均纯函数库）；
   Risk = 维护活跃、无已知漏洞——安全面无处置需求，不触发 SP-10。
   否决另一候选框架（+180 transitive，§23）
A3 版本确定性：lockfile 更新随本 Change 提交；Build Baseline = git commit
   + lockfile + base image digest（Ch11 §6）
A4 Generator 治理：WorkOrderTransferred Event 的 AsyncAPI codegen 从
   generator v6.1 升 v6.3——登记 Generator 版本变化；Generated Client
   不 Commit（CI Regenerate），Source = event schema 文件（§25 五要素）
A6 Config Change：TRANSFER_NOTIFY_TIMEOUT 从 5s 调 10s（该 timeout 为
   Partner 通知通道参数，与 SP-07 示例中已提升的 "transfer 成功后 5s 内必有
   Event" 时序承诺无关）——Binary 不变但 Runtime Behavior 变化 → 按 §42 建立
   Config Change Record（Identity=cfg-wo-118 / Reason= Partner 网络抖动 /
   Authorization= Service Owner / Verification= 超时行为测试 / Target
   State=10s），发布编排移交 SP-15；Flag 暴露面的进一步生命周期治理 →
   SP-16（pending-definition〔历史标注：所指接口均已 SEALED 落地，见 第五篇-CurrentBaseline总索引 §2〕，组5；落地前由 SP-15 §11.3 Target-changing
   Action 过渡覆盖）
A7 跨边界判定：reason 结构化载荷的 category 允许值清单（Config Schema）被
   Partner 读取 → 已成跨边界承诺，其后续演进移交 SP-07（与本组 SP-08 / SP-10
   示例的 reason 载荷设定同一事实）；判定与理由成文（B1）
```

---

# 16. 最终原则

> **Dependency、Toolchain、Config 是软件沉默的地基：它们不出现在需求文档里，却决定同一份源码构建出什么、在哪台机器上能跑、秘密是否还是秘密。纪律只有三条——引入要回答为什么，版本要确定，秘密要分开。凡是"顺手装上"、"本机能跑"、"先写死在代码里"的地方，都是未来事故现在埋下的位置。**
