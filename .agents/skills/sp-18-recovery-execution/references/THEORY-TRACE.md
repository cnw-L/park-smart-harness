# SP-18 Theory Trace（回溯到第一~四篇）

来源：第五篇-SP18-RecoveryExecution-正式操作规程.md §Theory Trace

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
