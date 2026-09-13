# 项目经验 Wiki — park-smart-harness 索引

> 本文件是执行 agent 访问 wiki 的**唯一入口**：先读索引，再按需深入单页；不要遍历全库读全文。
> 维护规约见 [AGENTS.md](../AGENTS.md) §3；完整时间线见 [log.md](log.md)。

## 读序（稳定 → 易变）

本索引 → [map.md](map.md) / [glossary.md](glossary.md)（摸底与撞域判断）→ 按需 [patterns/](patterns/README.md)、[decisions.md](decisions.md) → [log.md](log.md) 仅在需要时间线时读。

## 稳定页（更新制：保持当前真实，过期条目行内标 `[已过时：日期，原因]`，不删）

- [map.md](map.md) — 领域地图：模块 → 入口 / Current 文档 / pattern 指针（只放指针，不是 Current）
- [glossary.md](glossary.md) — 术语表：跨 agent 共同词汇

## patterns/（教训与模式，一模式一文件）

每个真实 Change 结束时 Ingest：踩坑、workaround、被门禁拦下的原因。

- [governance-dormant-on-small-tasks](patterns/governance-dormant-on-small-tasks.md) — 小任务下拉层休眠，靠推侧兜底
- [evidence-capture-regex-false-positive](patterns/evidence-capture-regex-false-positive.md) — 证据捕获正则误报（提示词字符串提到 pytest）
- [subagent-context-anchored-to-launch-root](patterns/subagent-context-anchored-to-launch-root.md) — 子代理上下文锚定会话启动目录，目录迁移/改名/worktree 均不能重锚定；退路=指令级隔离
- [session-root-move-disables-hooks](patterns/session-root-move-disables-hooks.md) — 会话根迁移会静默摘除 hooks，长任务在飞时勿迁根

## [decisions.md](decisions.md)（工程判例，append-only）

对本项目有效、未来可能被再问到的工程决定（选型、取舍、豁免理由）。判例不立法。

- [2026-09-06 治理资产 hooks 权威归属：项目侧资产](decisions.md)
- [2026-09-07 git 层门禁入口落 .git/hooks/pre-push 而非 core.hooksPath（CH-0002）](decisions.md)

## [impact.md](impact.md)（规范/技能生效记录，append-only）

第五篇技能/规程在本项目的每次重要生效或被拒（拒绝也留档，防重复提案）。

- [2026-09-06 SP-11 + hooks 首次实证生效；skills 层未触发](impact.md)

## [log.md](log.md)（append-only 时间线）

条目前缀 `## [日期] 类型 | 标题`，可直接 grep。最新条目见 [log.md](log.md)。
