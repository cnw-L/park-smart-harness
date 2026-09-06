# SP-21 Theory Trace（回溯到第一~四篇）

来源：第五篇-SP21-IncidentEmergency-正式操作规程.md §Theory Trace

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05 / GI-06 / GI-13（Evidence Gap ≠ PASS 是 GI-06 直接应用；
  最小不可消失事实是 GI-05 真实状态义务的极端场景下限）

Part II:
Ch12 §3（Incident Response / Operational Mitigation / Emergency
  Maintenance 三类边界——本规程 Trigger A 的判定基础）、§18-26
  （Emergency Maintenance 非最终 Closure / 非逃离流程许可证 / Hotfix
  基线 / Severity vs Priority / Triage / Symptom-Fault-RootCause /
  Follow-up Action / Postmortem 裁剪 / Blameless）、§56-57（Workaround
  / Temporary Mitigation 的 Owner 与退出条件）、§62（Repeated Incident）

Part III:
Ch3 Runtime / Deployment 面：Mixed / Recovering State 真实表达（§42、
  §60-64）——事故中系统状态不被压扁；Recovery Runbook 不可用反例
  （§67：结构状态未分开表达所致）；Ch8 Current / Drift（§61：Current
  结构是事故后重建工程事实的锚点）

Part IV:
Ch8 §7-25——Emergency 核心语义（§7 定义、§8 判定、§9 Mitigation
  Objective、§10 ≠链、§11-12 Compression Profile、§13-15 最小事实与
  Trace、§16-17 Stabilization、§18-19 Deferred≠Waived、§20 Exception
  退出、§21 Evidence Gap、§22-25 Reconciliation 与 Barrier）；
  §105-110（WorkOrder：INC-77 + CHG-WO-E17 Emergency 实例）；
  §131-134（Minimum Requirements Emergency 条 + 推荐最小字段）；
  Ch9 接口（§25 Closure 前最低判断的下游）

Journey:
JG-08 处理线上 Incident / Emergency：SP-21 → SP-18 Recovery /
  Stabilization → SP-17 Validation → SP-19 Reconciliation / Current；
  永久修复 → SP-03 normal / successor Change
```

---
