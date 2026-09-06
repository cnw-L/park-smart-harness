# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-01 Current / Authority Navigation Procedure

> 类型：Specialized Procedure  
> 状态：SEALED（2026-08-30：组2 Independent Concept Audit PASS AFTER REPAIR + 横向回归 20/20 VERIFIED；证据见《第五篇-第二组-SP0103040506-IndependentConceptAudit报告》《第五篇-第二组-SP0103040506-横向回归报告》）  
> 单一职责：从任意工程任务出发，解析出**诚实、分 Scope、Authority 可解析**的 Current Context。  
> 不是 Current 的生产者，也不是 Acceptance / Approval 的决策者；它是几乎所有 Journey 与其它 Procedure 的第一步。  
> 结构化镜像：`第五篇-SP01-CurrentAuthorityNavigation-OperationContract.yaml`

---

# 1. Trigger

调用 SP-01：

```text
A. 进入一个已有项目，需要知道"当前真实是什么"（JG-00）
B. 建立 Engineering Change 之前，需要 Starting Baseline 的真实来源（SP-03 前置）
C. Impact / Design / Implementation 之前，需要确认判断基于哪一版 Current
D. Incident / Emergency 中，需要快速定位受影响的 Current 与 Authority
E. 发现 Declared 与 Observed 可能不一致，需要核实 Current 真相
F. Authority / Owner 不清楚，需要解析"这件事谁说了算"
G. Review / Verification / Release 前，需要确认所依据的 Current Reference
```

SP-01 可以被任何 Journey、任何 Procedure、任何人机执行者调用。

---

# 2. 输入

至少：

```text
Engineering Scope          我在哪个项目 / 系统 / 组件范围内工作
Task Intent                我准备做什么（决定需要哪些 Concern 的 Current）
Navigation Entry           Authoritative Navigation Surface 的位置
```

可选：

```text
Known Concern List         已知会触及的 Requirement / Contract / Data 等
Target Environment Scope   Development / Production / Supported Release
Time Constraint            Emergency 时允许最小化深度（见 §11 Exception）
```

---

# 3. 输出

核心输出：

```text
Current Context
=
  Scoped Current Reference Set     每个适用 Concern 的 Current Reference + Revision + Scope
+ Authority Map                    每个 Concern + Scope 的 designated Authority / Owner
+ Evidence Pointers                支撑各 Current 的 Observed Evidence 位置
+ Truth Status                     每项：fact / Unknown-Gap / absent / Target
+ Structure Health Findings        导航中发现的 Drift / Dangling / Conflict（若有）
+ Resolved-At                      解析时间与来源 Revision
```

SP-01 **不输出**：

```text
Acceptance / Approval 决定
Current 的创建或修改
Target / Design 结论
Change 的建立
Readiness PASS
```

> SP-01 是**读取与解析**，不是**写入与批准**。

---

# 4. 核心语义：Current 是 Scoped 的

[MUST][BASELINE] Current Context 必须按 Concern / Baseline Kind + Scope + Authority 分别解析（GI-04）。

禁止：

```text
project.current_version = 1.4.2
→ 冒充 Requirement / Design / Contract / Data / Release / Runtime
   所有 Scope 已经同时一致
```

一个合法的 Current Context 示例：

```text
Requirement Current      req-baseline R12      (product scope)
Design Current           design-baseline D7    (search module)
Source Current           git sha a1b2c3        (main branch)
Contract Current         openapi v2.3 baseline (public API)
Data Current             schema migration M041 (production DB)
Release Current          1.4.2                 (production)
Runtime Current          deployment rev 88     (production)
```

这些 Reference 允许处于**不同 Revision**，只要各自 Scope 明确。

---

# 5. 核心语义：五种状态不得合并

[MUST NOT][BASELINE] 导航时必须区分（GI-05）：

```text
Accepted / Declared Current    被治理接受为有效的声明
Target / Intent                已批准但未实现的未来状态
Observed / Actual Evidence     实际观察到的事实证据
Runtime Actual State           运行时真实状态（适用时）
Tool Snapshot                  工具扫描的某时刻快照
```

典型冲突：

```text
Registry declares:  runtime:A uses artifact:X
Production shows:   runtime:A uses artifact:Y
```

处理规则：

```text
不得静默选择一边
→ 记录 Structure Health Finding
→ 标注该 Current 为 health-affected
→ 后续使用此 Current 的 Change 必须知道这一点
```

Accepted Current 在被 Calibration 之前**仍然存在**——它不是假的，但它已经带病。

---

# 6. 核心语义：Authority 分散在专项事实源

[MUST][BASELINE] Authority Map 必须解析到各 Concern 的 designated source（GI-11）：

```text
Requirement Authority  → Current Requirement Baseline / Product Authority
Architecture Authority → Current Architecture / Design Authority
Module Authority       → Current Module Definition
Source Authority       → Git / Source Revision
Contract Authority     → Contract Baseline
Data Authority         → Current Data Baseline / Data Owner
Runtime Authority      → Runtime / Deployment Definition + Environment State
Release Authority      → Release / Candidate Record
```

禁止：

```text
Navigation Surface / Portal / Catalog / Scanner
→ 仅因"能找到所有信息"就取得 Ultimate Authority（GI-07）
```

导航面负责 link / index / resolve / summarize；专项事实源负责语义。

---

# 7. Engineering Actions

## A1 — 确定 Scope 与 Concern List

从 Task Intent 推出本次需要哪些 Concern 的 Current：

```text
改 API        → Contract + Consumer + Module + Source
改数据库      → Data + Migration + Runtime + Module
线上 Incident → Runtime + Release + Deployment + Observability
```

不确定时先取最小集，导航中发现新关联再扩展。

## A2 — 从 Authoritative Navigation Surface 进入

每个项目必须存在一个导航入口（README / project.md / Portal / Catalog 均可），能稳定解析到：

```text
Current Scope
Module
Source / Build
Runtime / Deployment
Contract
Data
Cross-dimension Mapping
Active Transition / Exception
Structure Health Finding
```

入口不存在或解析失败 → 这本身是 Foundation Finding（见 §10）。

## A3 — 逐 Concern 解析 Current Reference

对每个适用 Concern 取得：

```text
Reference     指向专项事实源的稳定引用
Revision      具体版本 / SHA / Baseline ID
Scope         该 Reference 适用的范围
Resolved-At   解析时间
```

[MUST][BASELINE] Reference 必须可解析到 Revision 粒度；只解析到"latest / main / 最新文档"不算完成。

## A4 — 解析 Authority 与 Owner

对每个 Concern + Scope 回答：

```text
谁有权接受这个领域的语义变化？
谁有权批准这个 Scope 的 Current Transition？
找不到时 → Missing Authority Finding
找到两个都自称 Authority → Authority Conflict Finding（见 §10）
```

## A5 — 解析 Evidence Pointers

记录支撑各 Current 的 Observed Evidence 位置：

```text
CI run / test report
artifact digest
deployment record
runtime telemetry
```

Evidence 只是证据，不自动取得 semantic Authority（GI-07、第一篇 4.6）。

## A6 — 比对 Accepted 与 Observed

对关键 Concern 抽查声明与现实是否一致。[MUST][BASELINE] 必须显式列出本次执行了比对的 Concern + Scope 清单及各自依据的 Evidence；比对集为空本身必须作为带理由的显式声明记录——"没有已知分歧"不得来自"没有比对"。

发现分歧：

```text
形成 Structure Health Finding
按 Finding Type 分类（Drift / Dangling / Conflict / ...）
不就地"顺手改掉"——Current 的修改走 Change / SP-19
```

## A7 — 标注 Truth Status

对 Current Context 每一项标注（GI-02）：

```text
known fact    → fact（带 Reference + Revision）
unknown       → Unknown / Gap
not exist     → absent / none
future        → Target / Intent
```

[MUST NOT][BASELINE] 不得把 Unknown 伪装成 fact；`Unknown / Gap` 不自动等于 Ready / PASS / Accepted Exception。

## A8 — 产出 Current Context

汇总为一份可被下游引用的 Current Context（载体不限：Change Record 字段、Issue、YAML、导航页快照）。它随后成为：

```text
SP-03 的 Starting Baseline Context 来源
SP-04 Impact 的判断基础
SP-05 Design 的现实约束
Review / Verification 的对照基准
```

---

# 8. Control Mode

| 动作 | 控制模式 |
|---|---|
| 导航面链接解析、Revision 提取、Reference 完整性检查 | Automation |
| Accepted vs Observed 自动比对（有可靠 probe 时） | Automation |
| Dangling Reference / Duplicate Identity / Kind Mismatch 检查 | Automation |
| Truth Status 标注 | Automation-Assisted——`fact` 标注若仅由"解析成功"推出，只是 Proposal，需工程确认（GI-07） |
| Unknown/Gap 存在时是否允许建立 Change | Guardrail / Hard Gate |
| Authority Conflict 的裁决 | Engineering Decision |
| Health Finding 的严重度与处置 | Engineering Decision |
| "现实已经变了，Current 该怎么校准" | Engineering Decision → Change / SP-19 |

Hard Gate：

```text
[MUST NOT][BASELINE] 不得基于未标注的 Unknown / Gap 建立 Starting Baseline。
Unknown 可以存在，但必须显式声明，由 SP-03 的规则判断是否允许继续。
```

```text
[MUST NOT][BASELINE] 工具扫描结果不得被自动提升为 Current Authority（GI-07）。
扫描只能产生 Observed Evidence 与 Finding 候选。
```

---

# 9. PASS Exit

SP-01 完成的判据：

```text
[ ] 每个适用 Concern 的 Current Reference 解析到 Revision 粒度并带 Scope
[ ] 每个适用 Concern 的 Authority / Owner 可解析，或存在显式 Finding
[ ] 每项都有 Truth Status；Unknown / Gap / absent / Target 无伪装
[ ] Accepted 与 Observed 的比对已按声明的比对集执行；发现的 Divergence 已形成 Health Finding（比对集为空须带理由声明）
[ ] 导航入口可解析；或 Foundation Finding 已显式登记且本次解析路径已在 Finding 中说明
[ ] Current Context 可被下游 Procedure 稳定引用
```

完成不代表：

```text
Current 是健康的
Current 是最新 Observed 的
Change 已被允许建立
```

---

# 10. FAIL / NOT_READY Return Path

```text
Navigation Entry 不存在 / 失效
→ Foundation Finding
→ 修复导航面（SP-02 Revalidation / 相应 Remediation Change）

Current Reference Dangling / Duplicate Identity
→ Structure Health Finding（Registry / Mapping Integrity Defect）
→ 按第三篇 Finding 处置流程修复
→ 修复前，下游使用此 Reference 必须带 health-affected 标注

Missing Authority
→ Authority Finding
→ 由项目治理指定 designated Authority 后才能接受语义变化

Authority Conflict
→ STOP 使用该 Concern 的争议语义
→ 由 designated owner 按 Concern + Scope 裁决（GI-12）
→ 裁决前不得"两份折中"

Accepted ≠ Observed
→ Drift Finding
→ 走 Calibration（Change / SP-19）
→ SP-01 不得自行改写 Current
```

---

# 11. Exception / Alternative Path

## 11.1 Greenfield / Bootstrap

`absent / none` 是合法 Current Fact：

```text
Business implementation = absent
Accepted release = none
```

不得为了"看起来完整"编造未来事实（第一篇 7.1）。

## 11.2 Emergency / Incident

时间受限时允许最小 Current Context：

```text
Runtime / Release / Deployment / affected Module 的最小集合
+ 显式标注未解析部分为 Unknown
```

事后必须补齐完整 Current Context 并 Reconcile（SP-19 / SP-21）。

## 11.3 长周期 Change 的再解析

Current Context 是 Point-in-Time 结果。长周期 Change 中 Current 变化时：

```text
重新执行 SP-01（可只针对受影响 Concern）
→ 形成 Working Baseline Context 更新
→ 留下 Reason / Impact Decision / Updated Reference（第四篇 §46）
```

Working Baseline 更新的唯一追加点 = 该 Change Record 的 Working Baseline 段（append-only）——任何规程（SP-01 / SP-04 / SP-06）产生的更新都追加到同一处，不留分散副本。

不得静默把旧 Reference 改成新 Reference。

---

# 12. Evidence

Evidence by Work——正常导航自然产生：

```text
Navigation query / 导航路径记录
Pinned Reference + Revision（写进 Change Record 即成为 Evidence）
CI / deployment / telemetry 的 Observed Evidence 指针
Structure Health Finding 记录
Authority 裁决记录（仅 Decision / Rationale 需额外记录）
```

不要求额外维护一份独立 `current-context-evidence.md`。

Current Context 本身成为下游的 Starting Baseline 组成部分后，其历史必须保留（第四篇 §38），不得覆盖。

---

# 13. Current Update Obligation

SP-01 自身**不更新任何 Current**。它只可能产生：

```text
Structure Health Finding
Authority Finding
Foundation Finding
Unknown / Gap 声明
```

这些 Finding 的修复经由：

```text
正常 Engineering Change（第四篇）
SP-19 Calibration / Current Update
SP-02 Foundation Revalidation
```

> 注：SP-19 已随组3 落地为正式 Current 校准 / 更新规程（SEALED；见《第五篇-CurrentBaseline总索引》）——此前的临时路径（Domain Authority 以显式记录的 Change 执行校准）由 SP-19 正式承接。SP-21 仍为 pending-definition（组5）。本规程自身不更新 Current 的规则不变。

---

# 14. Theory Trace

```text
Part I:
GI-02 Truthful Starting Context
GI-04 Current Is Scoped
GI-05 Distinct States Must Not Collapse
GI-07 Tool ≠ Semantic Authority
GI-11 Semantic Ownership Concern + Scope
4.6 Evidence / 4.7 Authority

Part II:
Project / Architecture / Module / Contract / Data 要求（决定 Concern List）

Part III:
Ch1 结构总则 / Ch2 Scope 与边界
Ch7 Cross-dimension Mapping
Ch8 §7 Accepted vs Observed
Ch8 §9 Authority 分散
Ch8 §10-11 Authoritative Navigation Surface
Ch8 B/C Structure Health Finding / Integrity

Part IV:
Ch1 §C Starting / Working Baseline Context
Ch1 §44-46 Context Reconciliation
Ch2 Change Establishment（Starting Baseline 消费方）
```

---

# 15. Executable Asset References

```text
EA-01 Execution Navigation / Docs      导航入口本身
EA-17 Current Navigation / Update Tooling  Reference 解析与健康检查工具
```

工具可以实现：Reference 解析、Revision 提取、Dangling 检查、Accepted/Observed 比对、Finding 生成草案。Finding 的定级与处置仍是 Engineering Decision。

---

# 16. Reference Profile Bindings

```text
RP-ONLINE-API-PY-GH:
  Navigation Entry = README + docs/current/project.md
  Source Current   = git SHA
  Data Current     = alembic head revision
  Release Current  = GitHub Environment deployment record

RP-B / RP-C（CLI / SDK Shape）:
  Release Current  = 已发布 artifact 版本 + channel
  Runtime Current  = N/A（无服务端运行时）→ 显式 absent，不得伪造
```

Profile 只决定载体，不改变本规程语义。

---

# 17. Example

任务：给 work-order-service 增加 `transferReason` 字段。

```text
A1 Scope/Concern: Contract + Data + Module + Source + Runtime
A2 入口: README → docs/current/project.md
A3 解析:
   Contract Current = openapi baseline v2.3 (public API scope)
   Data Current     = migration M041 (production DB)
   Module Current   = module-registry R9 (workorder module)
   Source Current   = main @ a1b2c3
   Runtime Current  = deploy rev 88 (production)
A4 Authority:
   Contract → API Authority (team-work-order + external consumer owner)
   Data     → Data Owner (team-work-order)
A5 Evidence: CI run #1123, image digest sha256:…, deploy record #88
A6 比对: Registry declares search module uses artifact:X,
        production shows artifact:Y
        → Finding SF-017 (Drift), workorder 模块不受影响但同库带病
A7 Truth Status:
   以上各项 = fact
   Consumer list for v2.3 = Unknown / Gap → 显式声明
A8 产出 Current Context → 供 SP-03 建立 CHG-WO-017 的 Starting Baseline
```

Unknown/Gap（Consumer list 不全）被显式带入 SP-03；由 SP-03 / SP-04 规则决定这是否阻塞 Contract Evolution。

---

# 18. 最终原则

> **任何工程动作的第一步，是诚实地知道"现在是什么"：分 Scope 解析 Current、找到真正的 Authority、区分 Accepted 与 Observed、把 Unknown 标成 Unknown。SP-01 不创造真相、不批准变化——它保证后续所有 Impact、Design、Implementation、Verification 都站在可追的真实地基上。导航工具可以帮你找到事实，但永远不能替 Authority 宣布事实。**
