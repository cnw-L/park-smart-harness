# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-10 Security / Supply Chain Control

> 类型：Specialized Procedure  
> 状态：SEALED（2026-09-01：组4 Independent Concept Audit PASS AFTER REPAIR + 横向回归 1712 处引用核验 PASS AFTER REPAIR（REPAIR-1 已修复）；证据见组4 审计报告与横向回归报告）  
> 单一职责：把一次触及安全面的变化，受控地完成专业安全控制——安全要求早期识别，Enforcement Point 在可信边界真正生效，Third-party / Supply Chain 风险处置，Secret 安全处置，按风险分档的 Artifact Integrity / Provenance / SBOM 与 Release 权限控制，并组织 Security Evidence。  
> 安全不是上线前补一次扫描；UI Hide 与 Client Validation 不是 Enforcement；Dependency 的 identity 归 SP-09，安全处置归本规程，二者互不覆盖。  
> 结构化镜像：`第五篇-SP10-SecuritySupplyChainControl-OperationContract.yaml`

---

# 1. Trigger

```text
A. Change 触及安全面：Authentication / Authorization / Confidentiality /
   Integrity / Audit / Sensitive Data / Secret / Data Exposure / Retention /
   Compliance（P2 Ch4 §18）——SP-04 Impact 识别 Security Impact 后进入
   （JG-05 主线：SP-09 → SP-10）
B. Third-party Component 需要安全处置：可信 / 可维护 / 已知风险评估、
   漏洞响应、Supply Chain 策略判定（Ch9 §24）
C. Secret 安全事件：Secret 进入 Version History / 日志 / Artifact / Error，
   需要 Rotation 与安全处置（Ch9 §20）
D. Release / Artifact 供应链面：Integrity / Provenance / SBOM / Signing /
   Release Archive 要求建立或升级（Ch11 §49-51）；Deployment / Release
   权限与职责分离调整（Ch11 §56-57）
```

红线：**Security Requirement 必须在可信边界真正执行**（Ch9 §67.6 [MUST][BASELINE]）——不得仅依赖 UI Hide / Client Validation 保护服务端安全要求；Enforcement 必须在可信服务端或相应 Enforcement Point 生效（§40）。

不触发本规程的情形：

```text
Dependency / Toolchain 的 identity 与 resolution → SP-09（Ch9 §24 分工：
  本规程管 security control 执行，SP-09 管 identity / resolution，互不覆盖）
跨边界被依赖的 Authorization / Policy 语义演进   → SP-07（P2 Ch7 §16）
Data Meaning / Ownership / Write Authority       → SP-08（P2 Ch8 §46）；
  本规程承接其权限最小化与敏感数据控制的安全落地
实现执行（代码）                                  → SP-06
安全验证执行与 Candidate 结论                     → SP-11 / SP-12 / SP-13
  （本规程定义安全验证义务，不代替执行）
Build / Provenance 的构建期执行                   → SP-14
  （本规程按风险定义 Integrity / Provenance / SBOM 要求并消费其证据，
   不代替 SP-14 产生 Provenance）
Release / 部署编排 / Target 验证                  → SP-15 / SP-17
Emergency 压缩执行与事后对账                       → Ch8 + SP-21（pending-definition，组5）
Current 任何更新                                  → SP-19
```

---

# 2. 输入

```text
Security Impact 结论           SP-04：触及哪些安全面 / 信任边界 / 深度
安全要求事实                    Ch4 §18 十类 concern 中本 Change 适用项
                               （早于代码完成识别）
现有 Enforcement 面             可信服务端 / Enforcement Point 现状；
                               Input Validation 边界现状（Ch9 §40-41）
Third-party 事实                SP-09 移交的 Dependency Decision Record
                               （identity / resolution / transitive 事实）
供应链现状                      Artifact Integrity 机制 / Provenance / SBOM /
                               Signing / Release Archive 现状（Ch11 §49-51）
权限与职责现状                  Build / Promote / Deploy / Override Gate /
                               Rollback 权限面（Ch11 §56-57）
```

入口再挑战义务（B1 系统性规则）：上游使 Gate 归零的归类——"内部工具所以无安全要求"、"本 Change 不触及信任边界"、SBOM / Provenance "N-A"、"按风险不需要"——必须携带可解析理由；没有理由或理由不成立的，退回 SP-04 处置。

---

# 3. 输出

```text
Security Requirement Record   适用安全 concern 清单（§18）+ 每条的可验证表达；
                              Safety 领域判定（§25：触及人身风险系统 → 叠加
                              专门 Safety Standard，本规范不代替）
Enforcement Design            每条 Security Requirement 的 Enforcement Point
                              （可信边界，§40、§67.6）；Input Validation 边界与
                              规则归属（§41：不多层冲突规则）
Supply Chain Disposition      Third-party 处置：采用 / 替代 / 移除 / 缓解 +
                              漏洞响应记录；与 SP-09 移交事实互引（§24）
Secret Disposition Record     Rotation / 影响面 / 后续控制（Secret 事件时，§20）
Supply Chain Control Tier     按风险分档：Integrity（Checksum / Digest /
                              Repository Integrity 底线，§49）→ 更高要求加
                              Signing / Signed Provenance / Attestation /
                              SBOM / Release Archive（§50-51）
Release Authority Facts       Build / Promote / Deploy / Override Gate /
                              Rollback 权限定义（§56）；Release Authority 与
                              Exception Authority 可追踪（§57）
Security Evidence             上述记录 + 安全验证义务清单（移交 SP-11/12/13）
```

本规程**不输出**：

```text
Dependency identity / resolution 事实   → SP-09
代码实现                                → SP-06
验证结论（安全测试 PASS / Candidate）    → SP-11 / SP-12 / SP-13
Provenance / Attestation 构建产物        → SP-14
Release / Deployment 事实                → SP-15 / SP-17
Current 任何更新                          → SP-19
```

---

# 4. 核心语义

**安全要求必须早于代码完成被识别（Ch4 §18）**：Security / Privacy 不是上线前补一次扫描。Quality Requirement 阶段按风险识别十类 concern——Authentication / Authorization / Confidentiality / Integrity / Audit / Sensitive Data / Secret / Data Exposure / Retention / Compliance——它们随后影响 Architecture / Contract / Implementation / Security Verification / Operations。**Safety ≠ Security**（§25）：Security 防恶意访问与数据 / 系统破坏，Safety 防系统行为对人、财产、环境造成不可接受伤害；软件控制医疗 / 工业 / 车辆等人身风险系统时必须叠加专门 Safety Standard，本规范不代替领域标准。

**Enforcement 必须在可信边界生效（Ch9 §40、§67.6 [MUST][BASELINE]）**：Requirement / Contract 写"只有 TRANSFER_WORK_ORDER 权限可以执行"，不能只在 Frontend hide button 实现；真正 Security Boundary 必须在可信服务端或相应 Enforcement Point 生效。仅依赖 UI Hide / Client Validation 保护服务端 Security Requirement 是 [MUST NOT] 级违规。

**Input Validation 发生在正确边界（Ch9 §41）**：External Input 包括 HTTP / Message / File / CLI / Config / Database External Feed；按 Contract 验证 Type / Range / Format / Size / Allowed Value / Authorization Context；但不要在多个层各自定义互相冲突的业务规则。

**安全开发是 SDLC 的一部分（Ch9 §42、§24）**：NIST SP 800-218 SSDF v1.1 是当前 Final 基线——Secure Development Practice 集成到现有 SDLC，不是最后补一次；SSDF 覆盖 Third-party Component Risk 与 Vulnerability Response：引入的 Component 是否可信、可维护、存在已知风险，必须进入 Security Thinking。

**Supply Chain 控制按风险分档（Ch11 §11、§49-51）**：Provenance = 描述 Artifact 在哪里、何时、由什么 Build Process、使用什么 Input 产生的可验证 Metadata（SLSA v1.2：Subject + BuildDefinition + RunDetails + Builder + Build Metadata，含 Resolved Dependencies）。底线：**Artifact Integrity 必须可验证**（Checksum / Digest / Repository Integrity，确认 Build 后未被无声替换）；高安全 / 外部分发 / 监管软件进一步考虑 Artifact Signing / SBOM / Build Provenance / Release Archive / Integrity Verification（§50，具体格式由 Security / Supply Chain Policy 决定）。SBOM 适合 External Distribution / Security-sensitive / Regulated / Large Dependency Surface / Supplier·Acquirer Requirement，应尽量自动生成（§51）。普通小团队不需要一开始实施最高 SLSA Build Level（§11）。

**Release 权限与职责分离（Ch11 §56-57）**：自动化不意味着所有人都能随便 Deploy Production——Authentication / Authorization / Least Privilege / Audit；谁可以 Build / Promote / Deploy / Override Gate / Rollback 按风险明确。Separation of Duties 按风险使用：小团队一人 Build + Review + Deploy 仍然合理，不强制模拟 CAB；核心是 **Release Authority 和 Exception Authority 可追踪**。

**与 SP-09 / SP-14 的分工**：Dependency / Toolchain 的 identity 与 resolution 归 SP-09，安全处置归本规程（Ch9 §24，互不覆盖）；Provenance / Attestation 的构建期产生归 SP-14，本规程按风险定义要求并消费其证据。

---

# 5. Engineering Actions

## A1 — 确认入口与安全触及面

从 SP-04 移交出发，按 §18 十类 concern 枚举本 Change 触及的安全面，识别信任边界变化。执行 B1 再挑战：上游的"内部工具无安全要求 / 不触及信任边界 / N-A"归类没有理由的，退回 SP-04。

## A2 — 安全要求识别与可验证化

对每条适用 concern 形成可验证表达（Ch4 §18 示例形态："只有有权限管理员可以转派 / 转派行为需要 Audit / 普通用户不得读取内部操作原因"——可测试、可审查）。判定 Safety 领域（§25）：触及人身风险系统 → 显式登记并叠加专门 Safety Standard；普通业务系统判定"不适用"携带理由（B1）。识别必须在代码完成前完成；代码完成后才发现的新安全要求按新 Impact 处理。

## A3 — Enforcement Point 与 Validation 边界设计

每条 Security Requirement 指定 Enforcement Point（可信服务端或相应 Enforcement Point，§40、§67.6 [MUST][BASELINE]）；Frontend / Client 措施可以作为 UX，不作为 Enforcement。External Input 验证边界与规则归属明确（§41）：验证按 Contract 定义（Type / Range / Format / Size / Allowed Value / Authorization Context），规则单一归属，不多层冲突。设计移交 **SP-05**（Material 时），实现移交 **SP-06**。

## A4 — Third-party / Supply Chain 处置

承接 SP-09 移交的 Dependency 事实（或本规程直接识别），评估可信 / 可维护 / 已知风险（§24）：处置 = 采用 / 替代 / 移除 / 缓解，理由成文。发现已知漏洞 → 漏洞响应（影响面 / 修复版本 / 临时缓解 / 验证）——Emergency 级响应走 Ch8 + SP-21（pending-definition，组5）压缩路径，处置记录不豁免。

## A5 — Secret 安全处置

Secret 进入 Version History / 日志 / Artifact / Error 的处置（Ch9 §20）：不是删文件了事——Credential Rotation + 影响面评估 + 后续控制（扫描规则 / 注入改造）+ 记录。SP-09 登记事实，本规程执行处置。

## A6 — Supply Chain 控制分档

按风险定档（§49-51）：底线档 = Artifact Integrity 可验证（Checksum / Digest / Repository Integrity）；增强档（高安全 / 外部分发 / 监管 / 大依赖面 / 供需要求）= + Signing / Signed Provenance / Attestation / SBOM（自动生成）/ Release Archive。分档判定携带理由（B1）。Provenance / Attestation 的构建期产生移交 **SP-14**；本规程定义要求并消费证据。

## A7 — Release 权限与职责分离

定义 / 调整 Build / Promote / Deploy / Override Gate / Rollback 权限（§56：Authentication / Authorization / Least Privilege / Audit）；按风险决定是否 Separation of Duties（§57：不强制 CAB，但 Release Authority 与 Exception Authority 可追踪）。执行与记录归 **SP-15 / SP-17**，本规程定义权限面要求。

## A8 — 安全验证义务定义

为每条 Security Requirement / Enforcement / 处置定义验证义务（验证什么边界、什么证据），移交 **SP-11 / SP-12 / SP-13** 执行与绑定；本规程不代替验证执行，也不接受"扫描没报"替代 Requirement 级验证。

## A9 — Security Evidence 组织

汇总 Security Evidence：Security Requirement Record / Enforcement Design / Supply Chain Disposition / Secret Disposition / Control Tier 判定 / 权限事实——按 Change 绑定 Revision，供 SP-13 Evidence Binding 与后续审计消费。Evidence by Work：只要求分档判定理由、处置理由、Safety 判定、B1 归类显式成文。

## A10 — 移交边界汇总

- 安全设计 Material → **SP-05**；实现 → **SP-06**；
- 验证执行 → **SP-11 / SP-12 / SP-13**；
- Provenance 产生 → **SP-14**；Release 执行 → **SP-15 / SP-17**；
- Dependency 事实 ↔ **SP-09**（互不覆盖）；
- Emergency → **Ch8 + SP-21**（pending-definition，组5）；
- Current 更新 → **SP-19**。

---

# 6. Control Mode

| 动作 | 控制模式 |
|---|---|
| Secret 扫描 / Integrity 校验 / SBOM 生成 | Automation |
| Enforcement 存在性与位置核验 | Guardrail |
| 安全要求识别 / Enforcement 设计 / 处置决策 | Engineering Decision |
| Control Tier 分档 / SoD 判定 | Engineering Decision（理由成文） |
| 安全验证 / Provenance 产生 / Release 执行 | 归 SP-11·12·13 / SP-14 / SP-15·17 |

Hard Gate：

（标注约定：[BASELINE] 为规程级基线标注——依据为所引理论源条目或第五篇系统性规则（B1）；凡严于理论源标注面的，以本规程为准，差异在组基线索引登记。）

```text
[MUST][BASELINE]    G-SP10-01 Security Requirement 必须在可信边界真正执行——
                     不得仅依赖 UI Hide / Client Validation（Ch9 §67.6、§40）
[MUST][BASELINE]    G-SP10-02 安全质量要求必须早于代码完成被识别（Ch4 §18）
[MUST][BASELINE]    G-SP10-03 Artifact Integrity 必须可验证——Checksum /
                     Digest / Repository Integrity 至少其一（Ch11 §49）
[MUST][BASELINE]    G-SP10-04 Deployment / Release 权限受控——Authentication /
                     Authorization / Least Privilege / Audit；Build / Promote /
                     Deploy / Override Gate / Rollback 按风险明确（Ch11 §56）
[MUST][BASELINE]    G-SP10-05 Release Authority 和 Exception Authority 可追踪
                     （Ch11 §57）
[MUST][BASELINE]    G-SP10-06 External Input 在正确边界按 Contract 验证；
                     不得多层各自定义互相冲突的业务规则（Ch9 §41）
[MUST NOT][BASELINE] G-SP10-07 Secret 进入源码 / 日志 / Artifact / Error 后
                     仅删文件了事——必须 Rotation + 影响面 + 后续控制（Ch9 §20）
[MUST NOT][BASELINE] G-SP10-08 与 SP-09 互相覆盖——identity / resolution 不代管，
                     安全处置不推给 SP-09（Ch9 §24）
[MUST NOT][BASELINE] G-SP10-09 触及人身风险系统却不叠加专门 Safety Standard
                     （Ch4 §25）
[MUST NOT][BASELINE] G-SP10-10 无依据的 gate-zeroing——"内部工具无安全要求"、
                     "不触及信任边界"、SBOM / Provenance / SoD "N-A" 归类
                     必须携带可解析理由，并可被 SP-05 / SP-13 / 组级审计
                     再挑战（B1）
```

---

# 7. PASS Exit

```text
Security Control Plan 成立（绑定 Change Revision）：
  适用安全 concern 已识别且可验证（代码完成前）
+ 每条 Security Requirement 有可信边界 Enforcement Point
+ Supply Chain / Third-party / Secret 处置完成或有受控在途（Owner + 期限）
+ Control Tier 分档与权限面定义完成，理由成文
+ 安全验证义务已移交 SP-11 / SP-12 / SP-13
→ 移交 SP-05 / SP-06 / SP-14 / SP-15 各执行链
```

完成**不代表**：安全验证已通过 / 漏洞已修复上线 / Provenance 已产生 / Release 权限已生效。

---

# 8. Evidence

Evidence by Work：

```text
Security Requirement Record（concern + 可验证表达）
Enforcement Design（每条 Requirement 的 Enforcement Point）
Supply Chain Disposition / 漏洞响应记录
Secret Disposition Record（Rotation / 影响面 / 后续控制）
Control Tier 判定 + 权限面事实
安全验证义务清单（移交记录）
```

只有分档判定理由、处置理由、Safety 判定、B1 gate-zeroing 归类必须显式成文；其余证据随工作自然产生。

---

# 9. Current Update Obligation

本规程**不更新 Current**。安全控制定义与处置记录是 Change 绑定事实；Current Design / 权限面 / 供应链基线的正式迁移在实现 + 验证 + 交付完成后显式走 **SP-19**。

---

# 10. FAIL / Return Path

```text
安全要求在代码完成后才发现          → 按新 Impact 处理（SP-04），不得就地补
Enforcement 无法在可信边界生效       → 回 SP-05 重设计；不得以 Client 措施冒充
Third-party 风险不可接受且无替代      → 升级决策（Owner / Organization），
                                      不得默认接受
Emergency 漏洞响应                  → Ch8 + SP-21（pending-definition，组5）
                                      压缩路径；处置记录不豁免
验证义务无法定义证据                 → 回 A2 / A3 把要求可验证化，否则要求
                                      本身不成立（Ch4 §18 链路）
```

---

# 11. Exception / Alternative Path

## 11.1 小型内部工具

底线档从简：Integrity 底线（§49）与 Secret 禁令不豁免；Signing / SBOM / SoD 按 §50-51、§57 的适用条件可以不采用——"不适用"判定携带理由（B1），且 External Distribution / Regulated / 大依赖面任一条件成立即升级。

## 11.2 小团队职责合一

一个 Engineer Build + Review + Deploy 仍然合理（§57）；不强制模拟 CAB——但 Release Authority 与 Exception Authority 可追踪不豁免（G-SP10-05）。

## 11.3 Emergency 安全响应

严重漏洞 / 数据暴露可走压缩路径（Ch8 + SP-21，pending-definition，组5；落地前按 Ch8 正文执行）；安全分析、处置记录、事后对账不豁免。

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05

Part II:
Ch4 §18（Security / Privacy 十类 concern，早于代码完成识别）、
§25（Safety vs Security，领域标准叠加）
Ch9 §20（Secret 禁令与 Rotation）、§24（SSDF / Third-party / SP-09 分工）、
§40-41（Enforcement Point / Input Validation 边界）、§42（SSDF 集成 SDLC）、
§67.6（[MUST][BASELINE] 可信边界执行）
Ch11 §11（Provenance / SLSA v1.2）、§49（Integrity 底线）、§50（Secure
Release 五件）、§51（SBOM 适用）、§56（Deployment 权限）、§57（SoD /
Authority 可追踪）、§86.1-86.2（Build 可追踪 / 可确定 [MUST][BASELINE]）

Part III:
Source / Build / Runtime Mapping（Ch5 Source·Build、Ch3 Runtime 面对应关系：
Enforcement Point 在 Source / Runtime 的落点，Release 权限面在 Build /
Runtime 的映射）

Part IV:
Ch5（Enforcement 在实现期落地）
Ch6（安全验证义务进入 Candidate Evidence）
Ch7（Integrity / Provenance / 权限控制在 Release 期生效）
Ch8（Emergency 安全响应压缩路径）

Journey:
JG-05 新增或升级 Dependency / Toolchain / Config 主线（SP-09 → SP-10）
```

---

# 13. Executable Asset References

```text
EA-11 Provenance            SLSA / attestation 配置，subject ↔ artifact 验证
EA-13 Environment / Secret  Secret binding 与注入的安全面
EA-08 Verification Harness  安全验证（边界 / 权限 / 扫描）的确定性执行载体
```

工具适合：Secret 扫描、Integrity 校验、SBOM 自动生成、Attestation 验证、依赖漏洞匹配。
工具不适合：安全要求识别、Enforcement 设计、处置决策、Control Tier 分档、Safety 判定。

---

# 14. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Enforcement = 服务端依赖注入式权限检查（Enforcement Point 单一归属）
  Supply Chain = GitHub 生态：依赖漏洞匹配 / Secret 扫描 / Actions Attestation
  Release 权限 = 受保护环境 + required checks；小团队职责合一合法

RP-B-CLI（pending-definition，组6）:
  分发面 Integrity = Checksum + （外部分发时）Signing；SBOM 随发布自动生成
  Secret = OS keychain 引用；无服务端权限面（Deployment 权限裁剪，理由成文）

RP-C-SDK（pending-definition，组6）:
  外部分发默认增强档：Signing / SBOM / Provenance / Release Archive
  Consumer 不可控 → 供应链证据对外可验证；Safety 领域 SDK 叠加领域标准
```

---

# 15. Example

**CHG-WO-142（工单转派能力升级）的安全面——reason 能力上线前的安全控制闭环。**（承接 SP-07/08/09 示例；本例安全要求直接对应 P2 Ch4 §18 的转派示例。）

```text
A2 安全要求识别（代码完成前）：
   - 只有持 TRANSFER_WORK_ORDER 权限的角色可以转派（Authorization）
   - 转派行为必须产生 Audit 记录（Audit）
   - reason 的 note 内部批注部分普通用户与 Partner 不得读取（Data
     Exposure / Confidentiality；与本组 SP-08 / SP-09 示例的 reason 结构化
     载荷设定同一事实）
   - Safety 判定：工单系统无人身风险控制面 → 不适用，理由成文（B1）
A3 Enforcement 设计：TRANSFER_WORK_ORDER 检查在 work-order-service 服务端
   Enforcement Point 生效（不在 Admin App 隐藏按钮层，§67.6）；reason 的
   对外序列化在 API 边界过滤 note 的内部批注部分；输入验证按 Contract 在
   HTTP 边界执行（Type / Size / Allowed Value），规则单一归属
A4 Third-party 处置：SP-09 引入的校验库（v3.4.x）→ 可信 / 维护活跃 /
   漏洞库匹配无已知风险 → 处置 = 采用，理由成文；与 SP-09 记录互引
A6 控制分档：内部业务系统 + 无监管 → 底线档（Artifact Digest + 仓库
   Integrity，SP-14 已产 Provenance 事实，本规程消费）；分档理由成文
A7 权限面：Override Gate 权限仅限 Release Owner；Exception Authority 走
   既有登记路径（§57 可追踪）
A8 验证义务移交：权限拒绝用例 / audit 事件产生 / note 内部批注不出现在
   Partner 响应——移交 SP-11 / SP-13 执行绑定
```

---

# 16. 最终原则

> **安全不是一道上线前的扫描工序，而是一条贯穿要求、设计、实现、验证、交付的责任链：要求要早识别，Enforcement 要落在可信边界，依赖要可信，秘密要受控，制品要可验，权限要可追踪。凡是"前端隐藏了"、"扫描没报"、"删了就行"、"小工具不用管"的地方，都是安全责任被悄悄归零的地方——本规程的存在，就是让这些归零永远需要理由。**
