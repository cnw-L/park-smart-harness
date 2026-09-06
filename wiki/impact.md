# 规范/技能生效记录

> 条目格式：`## [日期] SP-xx | 事件`。
> 生效与被拒同等留档：拒绝记录防止重复提案（skill-impact 思想，源自 WikiSkill 论文）。

## [2026-09-06] SP-11 + hooks | 首次实证生效；skills 层未触发

- evidence_capture（PostToolUse/Bash）在 A/B 试验中自动捕获两臂修复前/后的 pytest 真实输出，含失败与重试记录——运行时绑定（G-SP11-08 精神）机械成立；push_gate 此前 7 例仿真测试全过。
- 22 个 SP 技能在治疗臂全程可见但零调取（任务小、触发面窄）——拉层休眠是真实状态而非故障；当前治理可靠性主要承载在推侧。
- Ingest 义务未被代理自发执行（"修个测试"未被判定为 Change）——见 patterns/governance-dormant-on-small-tasks。

## [2026-09-06] SP-11 + hooks | 根稳定期照常生效；会话根迁移使其静默失效（负面实证）；拉层连续两轮休眠

- evidence_capture 在会话根稳定期照常工作（指令级隔离 A/B 复测的臂前基线态 2 条运行时绑定记录）；两臂运行期间根迁至无 hooks 目录后对在飞子代理静默失效——推侧兜底的前提是"会话根稳定"，已入 patterns/session-root-move-disables-hooks。
- 治疗臂治理全量可见（同批探针证实注入）但依旧零技能调取、零 Ingest——与首轮一致：小任务下拉层休眠是稳定状态而非故障，治理可靠性当前主要承载在推侧。
