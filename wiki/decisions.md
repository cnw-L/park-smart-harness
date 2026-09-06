# 工程判例

> 条目格式：`## [日期] 上下文 | 决定`，正文写结论 + 理由 + 影响面。
> 判例不立法：只对本项目有效；发现规范级问题走 SP-22 提案回流。

（暂无条目）

## [2026-09-06] 治理资产 | hooks 权威归属：项目侧资产，暂不上移适配层

- **结论**：`evidence_capture.py` / `push_gate.py` 以本仓为权威源（已随 `da1f75f` 版本化）；适配层 `generate_skills.py` 不含 hooks 源码（全域 grep 无匹配），README 亦定位为"项目侧落点"。
- **理由**：钩子语义与具体 harness 强耦合（stdin payload 形态、settings.json 注册）；普适化需按 harness 分型，git 层 `pre-push`（core.hooksPath）是适配层 README 已登记的候选路径；仓内版本化已消除"无权威源"漂移风险。
- **影响面**：钩子缺陷修复走仓内 Change（CH-0001 为首例）；未来若适配层接管 hooks 生成，本判例由 SP-22 资产变更取代。
