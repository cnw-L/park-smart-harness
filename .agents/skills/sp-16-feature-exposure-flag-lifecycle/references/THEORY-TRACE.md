# SP-16 Theory Trace（回溯到第一~四篇）

来源：第五篇-SP16-FeatureExposureFlag-正式操作规程.md §Theory Trace

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05 / GI-13；Deployed ≠ Launched 是 GI-05 的直接应用

Part II:
Ch11 §2.5（Launch / Enable 与四分离）、§3（为什么区分 Deploy 与 Release）、
  §36-42（Rollout 策略按风险 / Canary / 渐进停止条件 / Feature Flag §40 /
  Flag 非免费消除器 §41 / Config Change 是 Release §42）、
  §68-70（复杂 Rollout 状态 / Partial 识别 / Canary 可观察）
Ch12 §14（Additive Maintenance：交付后新增 Feature 的暴露语境）

Part III:
Ch3 §31（Flag 是 Runtime Behavior 决定因素，Mapping 追到 Flag Reference）、
  §42-44（Mixed / Target / Transition Runtime Structure）、
  §71.7（服从第二篇 Build / Release 基线，不重定义交付语义）
Ch6 §49（Feature Flag Platform 是外部能力承载，不入结构主模型）
Drift 章 §61（Flag 是 Observation 误判的解释来源之一）

Part IV:
Ch7 §46-59（Rollout / Slice / Signal Attribution / Representativeness /
  Proceed / Pause / Concurrent）、§86-87（Launch / Feature Exposure 分离、
  Feature Exposure Change）、§88（Client 同类语义）、§114-116（Authority
  Token 约束 feature disable / traffic revert / Outdated Attempt）、
  §137（Feature Flag 反例）、§139（Minimum Requirements 暴露相关条）

Journey:
JG-07 部署后验证、扩大暴露或恢复（SP-15 → SP-16 → SP-17；异常 SP-18；
完成 SP-19）
```

---
