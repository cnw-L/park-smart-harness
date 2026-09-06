# 软件项目开发工程规范指南
## 第五篇 软件项目开发执行与操作指南
# SP-02 Project Bootstrap / Initialization Procedure

> 类型：Specialized Procedure  
> 状态：正式候选（经 Concept Audit 修订）  
> 单一职责：建立 / 再验证 Project Engineering Foundation Readiness。  
> 不是项目状态机；可在 R0/R1/R2/R3 Checkpoint 分别调用。

---

# 1. Trigger

调用 SP-02：

```text
A. 创建 Greenfield 项目
B. Prototype 转正式治理
C. 已有项目做 Foundation Gap Assessment
D. First Change 到达 R1/R2/R3 Checkpoint
E. Foundation Context materially changed,需要 Revalidation
```

---

# 2. 输入

至少：

```text
Initialization Mode
Project Scope
Current / Bootstrap Reality
Owner
Foundation Applicability Profile
Reference Profile
Current Change ID（R1+ 通常存在）
Checkpoint = R0 / R1 / R2 / R3
```

---

# 3. 输出

可能输出：

```text
Readiness PASS
Readiness NOT_READY
Deferred Foundation Obligation
Foundation Finding
Foundation Remediation Change
Readiness Evidence
Continuation Handoff
```

SP-02 不输出：

```text
Candidate Accepted
Delivery Authorized
Target Validation PASS
Change Closed
```

---

# 4. R0 — Governance Bootstrap Ready

## 4.1 必须建立

```text
Stable Project Identity
Project / Technical Owner
Engineering Scope
Repository / Source location
Technical Entry
Truthful Bootstrap Current / Reality
Foundation Applicability Profile
Requirement / Trigger Authority navigation
```

## 4.2 Clean-environment Proof

至少执行：

```text
fresh clone
→ open technical entry
→ locate setup/run/test/build commands
→ resolve current / change navigation
```

Greenfield 可以只验证 Bootstrap Technical Shell。

## 4.3 PASS

```text
Project can establish a normal Engineering Change
without inventing Current facts
```

---

# 5. Engineering Governance Cutover

R0 PASS 后记录：

```text
effective_at
decision / owner
bootstrap baseline refs
```

Cutover 后：

```text
Material Current Change
→ Part IV Engineering Change
```

Bootstrap 特权仅允许：

```text
create initial controlled facts
```

不能无限延期。

---

# 6. R1 — Development Foundation Ready

在主要 Product Implementation 开始前检查。

## 6.1 Applicability

由：

```text
Accepted Requirement
Impact
Accepted Design / Design Direction
Delivery Shape
Risk
```

决定。

## 6.2 最低 Concern

```text
repeatable local environment
controlled dependency resolution
configuration rule
secret rule
test / verify entry
relevant source / boundary navigation
security/toolchain access
migration mechanism if persistent schema is introduced
contract source if public contract is introduced
```

## 6.3 Readiness Proof

在 clean/reproducible environment 执行适用命令。

例如：

```text
dependency sync
unit test
integration harness startup
migration empty-db smoke（适用）
application technical shell startup（适用）
```

## 6.4 NOT_READY

不能因为：

```text
files exist
docs say ready
```

而 PASS。

---

# 7. R2 — Shared Integration Foundation Ready

在 Product Implementation 首次进入共享受控 Baseline 前检查。

## 7.1 必须有

```text
Shared Source Authority
Controlled Integration Path
Required Fast Verification
CI / equivalent automation
Repeatable Build
Visible Check Result
Broken Baseline handling
Execution Asset Version Binding
```

## 7.2 Staged Control Activation

推荐：

```text
1. create verify / CI
2. run successfully
3. stabilize check identity
4. configure Hard Gate
5. intentionally prove a failing change is blocked
6. record control evidence
```

工具可以不是 GitHub。

## 7.3 Solo / Small Team

如果没有多人共享 Baseline：

```text
R2 may be lightweight / N/A
```

但一旦有：

```text
shared source
release branch
published package
```

仍需与风险匹配的受控集成路径。

---

# 8. R3 — Delivery Foundation Ready

在第一次 Target Delivery / Distribution 前检查。

## 8.1 必须有

```text
Output / Artifact Identity
Target / Channel / Environment Identity
Config / Secret Injection
Delivery / Distribution Entry
Migration Execution（适用）
Observation / Diagnostics
Target Validation Entry
Recovery / Withdrawal Direction
Delivery Authority
```

## 8.2 Online Service

通常：

```text
version
logs
health/readiness as applicable
critical error visibility
metrics/traces by risk
```

## 8.3 CLI / Library

可以是：

```text
package/binary identity
release channel
checksum / artifact
install/run smoke
diagnostic exit/error
withdraw / replace direction
```

不要求 server health。

## 8.4 R3 PASS 不代表

```text
release authorized
deployment succeeded
target validation passed
```

只代表：

```text
系统有能力安全执行这些动作
```

---

# 9. Foundation Applicability / Deferred

每项 Concern：

```text
Applicable
Deferred
N/A
```

Deferred 必须有：

```text
Activation Trigger
Owner
```

例：

```text
Migration:
Deferred

Trigger:
First persistent schema introduced
```

---

# 10. Execution Asset Version Binding

以下资产必须可识别版本：

```text
Starter
Reusable Workflow
Action
Build Image
Policy
Migration Template
Deployment Adapter
```

允许策略：

```text
immutable SHA
versioned tag
controlled stable channel
```

但必须明确：

```text
consumer
compatibility
upgrade
rollback
```

---

# 11. Execution Command Contract

每个 Profile 至少提供逻辑能力：

```text
setup/sync
run
test
verify
build/package
migrate
smoke/validate
```

不要求每个平台文字完全相同。

要求：

```text
Developer path
and
CI path
must be semantically aligned
```

---

# 12. Secret / Target Rules

Template：

```text
MAY:
.env.example
secret names
schema / sample non-secret values

MUST NOT:
production secrets
private keys
real tokens
```

Target：

```text
Profile default name
≠ real project target authority
```

---

# 13. Isolated Engineering Spike

R1 前可允许：

```text
isolated experiment
```

条件：

```text
no accepted current write
no production
no shared product baseline
evidence traceable
```

---

# 14. Revalidation

以下变化触发相应 Readiness Revalidation：

```text
dependency tool changed
CI workflow replaced
build platform changed
repository control removed
runtime packaging changed
deployment mechanism changed
secret model changed
new DB introduced
public contract introduced
```

Readiness 不是永久证书。

---

# 15. Small Team Profile

最小可以是：

```text
README
Repository
simple scripts
version control
automated tests
simple CI
package/build
```

不要求：

```text
IDP
Backstage
Kubernetes
CAB
multi-reviewer
```

---

# 16. Gate Matrix

| Checkpoint | Gate asks | PASS means |
|---|---|---|
| R0 | 能否建立第一条正常 Change？ | Governance Bootstrap Ready |
| R1 | 能否开始主要 Implementation？ | Development Foundation Ready |
| R2 | 能否进入共享受控 Baseline？ | Shared Integration Foundation Ready |
| R3 | 能否执行第一次 Target Delivery？ | Delivery Foundation Ready |

---

# 17. Return Paths

```text
R0 NOT_READY
→ fix bootstrap truth / owner / navigation

R1 NOT_READY
→ establish missing dev/test/migration/config foundation

R2 NOT_READY
→ repair CI / build / integration control

R3 NOT_READY
→ establish artifact/target/deploy/observe/recovery foundation

Material design changes applicability
→ Ch3 / Ch4 reconcile
```

---

# 18. 最终原则

> **Project Initialization 的完成标准不是“初始化 Checklist 全打勾”，而是每个真实动作在发生之前拥有与其风险匹配、可以执行并由 Evidence 证明的工程基础。R0–R3 只表示 Readiness，不表示 Project Lifecycle State，也不替代第四篇的 Change、Candidate、Release 或 Closure。**
