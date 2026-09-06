# 会话根迁移会在任务运行中途静默摘除 hooks

## 症状

A/B 两臂异步子代理运行期间，主会话通过 change_directory 把根从 park-smart-harness 迁到 repo-a；此后 evidence_capture / push_gate 全部失效——runs.jsonl 在臂运行期零追加，无任何报错或提示。治疗臂的修复前后 pytest 均未落证据。

## 根因

hooks 随会话根的项目设置（.claude/settings.json）解析；repo-a 无 settings → 无 hooks。迁移对正在运行的子代理无通知，推侧机械兜底静默消失。另外：change_directory 的"回合结束即迁移"语义不可靠——两次授权均未自动兑现，仅用户在应用侧动作后落地一次。

## 处置

- 长任务（异步子代理）运行期间不要迁移会话根；迁移前确认无在飞子代理。
- 证据闭环不能依赖单一捕获通道：任务起点先跑一次留痕验证（本次臂前 15:25 两条 3-failed 记录保住了起点证明）；事后用独立复跑 + git diff 复核，结果写入报告/wiki 正文——不回填 runs.jsonl（红线 4）。
- 迁回主根后 hooks 恢复；根漂移期间产生的验证输出只能作为报告引文，不是 runs.jsonl 证据。
