# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-14 Build / Artifact / Provenance Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-31：组3 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1050 处引用核验 PASS AFTER REPAIR（备注级）；证据见组3 审计报告与横向回归报告）  
> 单一职责：为 Candidate / Release 生产并担保**规范级构建产物身份**——固定 Build Baseline（Source + Dependency + Build Definition + Build Environment），执行可复现的 Canonical Build，建立 Digest 级 Artifact Identity，按 Supply-chain / Audit Risk 产出适当深度的 Provenance，执行 Same Artifact Promotion，并对 Release Formation 中的 Materialization Delta 作出显式评估与移交。  
> 边界：Feedback Build ≠ Candidate Build ≠ Release Build（Ch5 §70-71）；Artifact Identity 一经发布不得无痕改指（Ch7 §15）；Release Formation 不得重新 Build 一个"差不多的"产物冒充已验证（Ch7 §9）；Provenance 证明的是"Artifact ← Build Inputs / Builder"，不替代 Requirement / Performance / Migration / User 验证（Ch6 §109）。  
> 与 SP-13 / SP-15 的分工：SP-14 **生产** Artifact Identity 与 Provenance；SP-13 把产物**绑定**为 Candidate 成员并判定证据；SP-15 在 Release Formation 中**引用**身份并据 SP-14 的 Delta 评估决定是否需要回 SP-13 重评。  
> 结构化镜像：`第五篇-SP14-BuildArtifactProvenance-OperationContract.yaml`

---

# 1. Trigger

```text
A. Candidate 需要 Artifact 类成员——需要 Candidate-grade Build 与 Identity
B. Accepted Candidate 进入 Release Formation——需要确认引用的 Artifact Identity
   就是被验证的那个（Same Artifact Promotion）
C. Release Formation 涉及 Signing / Packaging / Distribution Wrapping /
   Platform-specific Materialization——需要评估 Materialization Delta
D. Build 失败或不可复现——需要分类、修复或处置
E. Supply-chain / Audit Risk 要求提升 Provenance 深度（签名 / SLSA / Attestation）
F. 纯 Source / Config / Docs 类 Change 无打包产物——按 §11.1 退化路径执行
   （Source 级锚定由本规程以退化形态承担；Candidate 成员绑定仍归 SP-13 A3）
```

红线：**"只是打包"不等于没有风险**（Ch7 §11）——产生新 executable / package identity 的物化必须显式评估并回 Ch6 判断 Evidence Applicability。

不触发本规程的情形：

```text
Local / Pre-submit 的 Feedback Build            → SP-11（Ch5 §68-70）
Candidate 成员绑定 / Evidence Applicability 判定 → SP-13（本规程提供身份与 Delta 事实）
Release Formation / Decision / Authorization    → SP-15
Deployment 执行                                  → SP-15
```

---

# 2. 输入

```text
Build 请求级别                 feedback / candidate / release——级别决定语义要求
Source Revision Set            可解析到 Revision 粒度（SP-06 / SP-13 移交）
Dependency Context             锁定文件 / 版本锚点（可事后重新解析当时真实内容）
Build Definition               Dockerfile / build config / package config 的明确
                               Revision（EA-10）
Build Environment              Builder 身份 / 镜像 / 工具链版本指纹
Risk / Policy                  Supply-chain / Audit Risk 等级，决定 Provenance 深度（Ch6 §108）
Accepted Candidate（Trigger B/C）含 Candidate Manifest 与被验证 Artifact Identity（SP-13）
```

入口再挑战义务（B1 系统性规则）：上游移交中"该 Feedback Artifact 已具备 Identity / 可追 Input / 稳定 Context"的声明（Ch5 §72）必须携带可解析依据；Build 级别声明（"这就是 candidate build"）必须能被 Build Baseline 记录支撑，否则退回来源规程。

---

# 3. 输出

```text
Build Baseline Record       Source Revision Set + Dependency Context + Build
                            Definition Revision + Build Environment 指纹
Canonical Build Result      Artifact 集 + Artifact Identity（Digest 级）+
                            Build 结果（含可复现性事实）
Provenance Record           按风险深度：普通 = CI Run ID / Source SHA / Artifact
                            Digest / Test Report / Reviewer Record（Ch6 §108）；
                            高风险 = Signed Artifact / SLSA Provenance /
                            Attestation / Trusted Producer / Immutable Evidence Store
Materialization Delta Record Release Formation 中身份是否变化、为何变化、
                            是否产生新 executable / package identity、
                            需要回 SP-13 重评的范围
Same Artifact Promotion Record Candidate → Release 引用的 Identity 链：
                            被晋升 Identity / 来源 Candidate Revision / 晋升目标
                            （staging / production / distribution channel）
```

**不输出**：

```text
Candidate 成员资格 / Acceptance        → SP-13（绑定与判定是 Ch6 的）
Evidence Applicability 结论            → SP-13（本规程只提供 Delta 事实）
Release Baseline / Release Decision    → SP-15
Verification 结论（Requirement / Performance / Migration / User）→ 各所属规程
                                    （Provenance 不替代这些验证，Ch6 §109）
任何 Current 更新                      → SP-19
```

---

# 4. 核心语义

**三级 Build 分离（Ch5 §68-71）**：Feedback Build 为快速反馈服务（可用临时环境、不保留 Artifact）；Candidate Build 必须产出具备明确 Identity、可追 Source / Build Inputs、足够稳定 Context 的 Artifact；Release Build 另需 Build Baseline / Artifact Identity / Provenance / Traceability（第二篇 Build / Release WHAT）。级别可以复用产物——Feedback Artifact 被 Ch6 显式选中即升级（Ch5 §72）——但**级别语义不可冒充**：拿 Feedback Build 的临时产物直接当 Release 产物是红线。

**Build Baseline（第二篇 Build WHAT + Ch5 §71）**：Source + Dependency + Build Definition → Build Result / Artifact。Candidate / Release 级 Build 必须把四个输入固定到可事后重新解析的粒度：Source Revision Set（multi-repo 绑定集合，不用单一 SHA 冒充，Ch5 §296 同旨）、Dependency 锁定、Build Definition Revision、Builder / 工具链指纹。可变别名不得充当输入身份（Ch6 §139 同旨适用于 Build Inputs）。

**Canonical Build 与可复现性（EA-10）**：同一 Build Baseline 应产生同一 Artifact Identity（reproducible），或差异可解释、可审计（如时间戳嵌入——差异点必须列举）。不可解释的不可复现 = Build 机制缺陷，按失败分类处置，不得通过"多跑几次碰到一致的"收敛。

**Artifact Identity（Ch7 §15）**：Digest 级不可歧义身份。一经发布（被 Candidate Manifest / Release Baseline 引用），不得无痕改指——今天 v1.9.0 指向 Artifact X、明天指向 Y 是禁止的；要改就新 Revision。

**Provenance 深度按风险（Ch6 §108-109）**：普通团队的 CI Run ID + Source SHA + Artifact Digest + Test Report + Reviewer Record 通常足够；高 Supply-chain / Audit Risk 用 Signed Artifact / SLSA Provenance / Attestation / Trusted Producer / Immutable Evidence Store 增强。**SLSA Build Provenance 只覆盖 Artifact ← Build Inputs / Builder**，不替代 Requirement Verification / Performance Test / Migration Reconciliation / User Validation（§109）。

**Same Artifact Promotion（Ch7 §9、§139 [SHOULD]）**：Release Formation 应优先引用 Ch6 已验证 Candidate 的实际 Artifact / Member Identity——可打包软件优先同一产物逐级晋升。禁止"Candidate X verified → Release 前重新 Build 一个差不多的 X2 → 直接说 X2 也 verified"。

**Release Materialization Delta `[BASELINE]`（Ch7 §10-11）**：Signing / Packaging / Distribution Wrapping / Platform-specific Materialization 导致的 Candidate / Artifact Identity 差异。物化**没有改变被验证软件内容身份** → 可继承 Candidate Evidence（记录判断依据）；**产生了新 executable / package identity** → 必须回 Ch6 判断 Evidence Applicability，必要时形成新 Candidate / 补 Verification。Delta 评估由本规程产出事实，Applicability 结论归 SP-13。

---

# 5. Engineering Actions

## A1 — 判定 Build 级别与用途

明确本次 Build 是 feedback / candidate / release 哪一级，级别决定下文要求集。级别声明写入 Build Record；上游声称"这个 Feedback Artifact 可直接进 Candidate / Release"的，核对其 Identity / Input 可追性 / Context 稳定性依据（Ch5 §72 三条件 + B1 再挑战），不满足则按 candidate / release 级重新 Build。

## A2 — 固定 Build Baseline

锁定四个输入：Source Revision Set、Dependency Context（lockfile / 版本锚）、Build Definition Revision、Build Environment 指纹。任何一项只能用可变别名解析的，Build 不得开始——先把它锚定到可事后重新解析的形式。

## A3 — 执行 Canonical Build

按 Build Definition 执行；记录 Build Run 身份（CI Run ID / Builder）。可复现性核验：同 Baseline 重跑应得同 Digest；差异必须可解释并列举差异点。Build 失败按 SP-11 九类分类路由（Source 问题回 SP-06 / Dependency 回 SP-09 域 / Toolchain·Infra 修机制 / External 隔离 / Unknown 保留），不盲目重跑收敛。

## A4 — 建立 Artifact Identity

为每个产物计算 Digest，形成 Artifact Identity 清单（multi-platform / multi-arch 逐平台列举，不用一个标签概括差异内容）。Identity 一经 SP-13 / SP-15 引用即冻结；内容变化必须产生新 Identity 并由引用方显式改绑。

## A5 — 产出 Provenance

按 Risk / Policy 定深度（**风险分档判定归 SP-10 A6**——SP-10 定义分档要求并消费证据，本规程按所定档执行产出；E-5 备注级修复，最终全篇横向回归登记）：普通级 = CI Run ID + Source SHA / Revision Set + Artifact Digest + Test Report + Reviewer Record（Ch6 §108）；高风险级追加签名 / SLSA Provenance / Attestation / Trusted Producer / Immutable Evidence Store。Provenance 记录明确标注其覆盖边界——**只证明 Artifact ← Build Inputs / Builder**，不得被引用为 Requirement / Performance / Migration / User 验证的替代（Ch6 §109）。

## A6 — 执行 Same Artifact Promotion

Candidate → Release 的每一步优先引用同一 Artifact Identity。Promotion 决策记录：被晋升的 Identity、来源 Candidate Revision、晋升目标（staging / production / distribution channel）。发现"重新 Build 一个差不多的"企图时拒绝并退回——要么引用已验证 Identity，要么把新产物作为新 Candidate 成员回 SP-13 验证。

## A7 — 评估 Release Materialization Delta

Release Formation 涉及 Signing / Packaging / Wrapping / Platform-specific Materialization 时，逐项回答：

```text
1. 被验证软件内容身份是否改变？（内容 Digest 对比）
2. 是否产生新 executable / package identity？（信封 / 签名 / 平台格式）
3. 若产生新身份：Delta 内容是什么、影响哪些 Evidence 的 Objective / Assumption？
```

内容身份未变（如纯签名信封）→ 记录"可继承"判断依据，移交 SP-15；产生新身份 → 形成 Materialization Delta Record，移交 SP-13 重评 Evidence Applicability（必要时新 Candidate / 补 Verification）。"只是打包"不是免检理由（Ch7 §11）。

## A8 — 移交构建事实

```text
→ SP-13   Artifact Identity + Build Baseline + Provenance（Candidate 成员绑定用）；
          Materialization Delta Record（重评用）
→ SP-15   Release Formation 可引用的 Identity 清单 + Promotion 记录 + Delta 处置状态
→ SP-11   Build 级 Feedback 需求（Build 自身失败的分类结果回本层闭环）
```

任何移交都不是 Candidate Accepted、不是 Evidence Applicability 结论、不是 Release Decision。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| A1 级别判定 | Guardrail（级别语义机械）+ B1 再挑战 |
| A2 固定 Build Baseline | Automation + Guardrail（别名红线机械） |
| A3 Canonical Build | Automation |
| A4 Artifact Identity | Automation（Digest 计算与登记） |
| A5 Provenance | Automation + Policy（深度由 Risk 定） |
| A6 Same Artifact Promotion | Guardrail + Engineering Decision |
| A7 Materialization Delta 评估 | Engineering Decision（工具可对比 Digest，结论留人） |
| A8 移交 | Automation + Guardrail |

Hard Gates：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST NOT][BASELINE] G-SP14-01 用 Feedback Build 产物冒充 Candidate / Release 级产物
                     （Ch5 §70-71/§277）
[MUST][BASELINE]    G-SP14-02 Candidate / Release 级 Build 必须固定 Build Baseline
                     四输入到可事后重新解析粒度；可变别名不得充当输入身份（Ch6 §139 同旨）
[MUST][BASELINE]    G-SP14-03 Artifact Identity 必须 Digest 级不可歧义；一经发布
                     不得无痕改指（Ch7 §15）
[MUST NOT][BASELINE] G-SP14-04 Release 前重新 Build"差不多的"产物并声称其已验证
                     （Ch7 §9）
[MUST][BASELINE]    G-SP14-05 Materialization 产生新 executable / package identity 时，
                     必须显式记录 Delta 并回 SP-13 重评 Evidence Applicability（Ch7 §11）
[MUST][BASELINE]    G-SP14-06 Provenance 深度必须匹配 Supply-chain / Audit Risk；
                     SLSA / Attestation 不得被引用为非 Build 类验证的替代（Ch6 §108-109）
[MUST NOT][BASELINE] G-SP14-07 通过反复重跑收敛不可解释的不可复现 Build——
                     不可复现即 Build 机制缺陷，先分类处置（Ch5 §278 同旨）
[MUST][BASELINE]    G-SP14-08 同级复用 / 晋升声明（"same artifact"）必须携带
                     Digest 对比依据，并可被 SP-13 / SP-15 入口再挑战（B1）
```

---

# 7. PASS Exit

```text
[ ] Build 级别声明与 Build Baseline 记录一致、四输入可重新解析
[ ] Canonical Build 成功；可复现性事实已记录（同 Digest 或差异点清单）
[ ] Artifact Identity 清单完整（逐平台）且未被无痕改指
[ ] Provenance 深度匹配 Risk，覆盖边界已标注
[ ] Same Artifact Promotion 链可追（Candidate Identity → Release 引用）
[ ] Materialization Delta（若有）已评估、已移交、SP-13 重评结论已回录
```

**完成不代表**：Candidate Accepted（SP-13）/ Evidence 适用于新身份（SP-13 结论）/ Release 成立或可交付（SP-15）/ 任何 Current 更新。

---

# 8. Evidence

Evidence by Work：Build 记录、Digest、CI Run、锁定文件的天然载体是 CI / 构建系统与 Artifact Registry（EA-10 / EA-11）。必须显式产生的：

```text
- Build Baseline Record（四输入锚点）
- 可复现性事实（同 Digest 证明或差异点清单）
- Promotion 记录（Identity 链）
- Materialization Delta Record 与"可继承"判断依据
- Provenance 覆盖边界声明
```

---

# 9. Current Update Obligation

```text
writesCurrent: false
```

Build / Artifact / Provenance 是事实生产，不更新任何 Current。Artifact 进入 Candidate、进入 Release、进入 Target 环境分别由 SP-13 / SP-15 / SP-17 决定；Current 提交统一走 SP-19。

---

# 10. FAIL / Return Path

```text
Build 失败            → SP-11 九类分类：Source → SP-06；Dependency → SP-09 域；
                        Toolchain / Infra → 修机制；External → 隔离；Unknown → 保留
不可复现且不可解释     → Build 机制缺陷，修 Build Definition / 工具链（EA-10 治理）
Materialization 产生新身份 → SP-13 重评；必要时新 Candidate Revision + 补 Verification
Promotion 链断裂（身份对不上）→ 停止 Release Formation，退回 SP-13 / 重新 Build
```

---

# 11. Exception / Alternative Path

## 11.1 无 Artifact 的 Change

纯 Source / Config / Docs 类 Change 无打包产物：Artifact Identity 退化为 Source Revision Set + Config Snapshot 绑定；本规程其余语义（Baseline 固定、Promotion 引用、Delta 评估）照常适用。

## 11.2 平台物化不可避免

Mobile / Firmware / 多平台分发必然产生 platform-specific 新身份（Ch7 §17/§88）：每个平台身份逐一登记 Delta 与重评结论，不允许用"同源"一句概括。

## 11.3 Emergency

Ch8 fast-path 可压缩 Provenance 深度到普通级下限，但 Build Baseline 固定、Identity 不冒充、Delta 评估不豁免；事后经 SP-21 / SP-19 对账补齐。

---

# 12. Theory Trace

```text
第一篇  GI-05 / GI-13
第二篇  Build WHAT（Source + Dependency + Build Definition → Result / Artifact）；
        Release WHAT 边界
第三篇  Source / Build / Artifact WHERE
第四篇  Ch5 §68-72（三级 Build 分离、Feedback Artifact 选中）、§277/§296/§304；
        Ch6 §13-15（Dynamic Config / Evidence Context / 无 Secret）、§108-109
        （Provenance 深度、SLSA 边界）、§139-140（两个 MUST-BASELINE）；
        Ch7 §8-17（Release Formation / Materialization Delta / Release Baseline /
        Identity / Coherence / Formation Scope）、§139（Same Artifact Promotion
        SHOULD）；Ch8（Emergency）
```

Theory Trace 只说明受哪些理论约束；本规程不复制理论正文，不成为第二份 Authority。

---

# 13. Executable Asset References

```text
EA-10 Build Definition    可复现构建的载体（Dockerfile / build config / package config）
EA-11 Provenance          SLSA / Attestation 配置；subject ↔ artifact verification
EA-07 Reusable CI         Build Run 身份与记录自动产生
EA-13 Environment / Secret Builder 环境指纹与签名密钥注入（Secret 不进 Manifest，Ch6 §15）
```

工具适合：固定 Baseline、执行 Build、计算 Digest、产生 Provenance、对比身份。工具不适合：Build 级别判定结论、Materialization Delta 的风险评估、Promotion 决策、"可继承"判断。

---

# 14. Reference Profile Bindings

```text
通用层        Operation Contract / Theory Trace / Evidence 语义 / Control 语义——全 Profile 共用
Delivery Shape  决定 Artifact 集构成与 Promotion 链形态（如 CLI 的多平台二进制 +
                校验和清单；SDK 的多语言包仓库分发——Ch7 §88 分发记录形态）
Risk Overlay    决定 Provenance 深度（Ch6 §108 两级）与可复现性严格度
```

具体 Profile 绑定在组6 RP 补齐时登记；本规程不预留学生位。

---

# 15. Example

**CHG-WO-142 / C2 构建与 Release 1.9.0 形成——接 SP-13 示例，引 SP-15 示例。**

A1-A3：C2 修复后需要 Candidate 级 Build。Build Baseline 固定：Source = 三仓 Revision Set（app@SHA / contract@SHA / migration@SHA）、Dependency = lockfile 锚点、Build Definition = Dockerfile@rev7、Builder = ci-runner image 指纹。Canonical Build 产出 `image sha256:9f2c…`；同 Baseline 重跑 Digest 一致，可复现事实记录。

A4-A5：Artifact Identity 登记（单平台单产物）。项目为普通 Supply-chain 风险：Provenance = CI Run ID + Revision Set + Digest + Test Report 引用，不强制 SLSA（Ch6 §109）。移交 SP-13 绑定进 C2 Manifest。

A6：C2 ACCEPT 后进入 Release Formation（WO-1.9.0，见 SP-15 示例）——直接引用 `sha256:9f2c…`，**不重新 Build**。Promotion 记录：C2 → release-1.9.0 candidate identity 链。

A7：发布前需要签名分发包。签名信封产生新 package identity（内容 Digest 不变）。Delta 评估：被验证内容身份未变 → 记录"可继承 Candidate Evidence"判断依据（信封不含可执行内容变化）；若某平台要求重打包为不同格式产生新可执行身份 → Delta Record 移交 SP-13，按 Candidate Delta ∩ Evidence Dependency Set 重评（本例结论：功能 / 合同证据适用，安装层 smoke 需补）。

红线对照：若有人提议"Release 前用最新依赖重新 Build 一版更稳"——拒绝：那是一个**新产物**，要么回 SP-13 作为新 Candidate 验证，要么放弃（Ch7 §9）。

---

# 16. 最终原则

> **构建规程的全部意义在于身份的真实性：被验证的、被发布的、被部署的必须是同一个可辨认的东西。Build Baseline 不定，身份就是空话；产物重建一次，验证就归零一次；签名打包不是免检通道，Provenance 也不是万能证明——它只回答"这东西由什么造成"，从不回答"这东西对不对"。Same Artifact 逐级晋升，Delta 如实评估，身份一经发布永不改指。**
