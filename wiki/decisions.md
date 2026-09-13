# 工程判例

> 条目格式：`## [日期] 上下文 | 决定`，正文写结论 + 理由 + 影响面。
> 判例不立法：只对本项目有效；发现规范级问题走 SP-22 提案回流。

（暂无条目）

## [2026-09-06] 治理资产 | hooks 权威归属：项目侧资产，暂不上移适配层

- **结论**：`evidence_capture.py` / `push_gate.py` 以本仓为权威源（已随 `da1f75f` 版本化）；适配层 `generate_skills.py` 不含 hooks 源码（全域 grep 无匹配），README 亦定位为"项目侧落点"。
- **理由**：钩子语义与具体 harness 强耦合（stdin payload 形态、settings.json 注册）；普适化需按 harness 分型，git 层 `pre-push`（core.hooksPath）是适配层 README 已登记的候选路径；仓内版本化已消除"无权威源"漂移风险。
- **影响面**：钩子缺陷修复走仓内 Change（CH-0001 为首例）；未来若适配层接管 hooks 生成，本判例由 SP-22 资产变更取代。

## [2026-09-07] 判例 | git 层门禁入口落 .git/hooks/pre-push 而非 core.hooksPath（CH-0002）

- **结论**：pilot 的 git 层门禁 shim 写入 `.git/hooks/pre-push`，`exec python ... "$(git rev-parse --show-toplevel)/.claude/hooks/push_gate_git.py"`。
- **理由**：单项目本地模式下 core.hooksPath 指向包布局目录（包模板 shim 依赖 `../scripts/` 相对结构）；直指项目侧脚本零布局依赖，且与 Claude 钩子共用 spec_gate_core 单一权威。
- **影响面**：手动终端 push 与 Claude 会话 push 同受一门禁；SPEC_GATE_DISABLE=1 逃生阀不变。多项目/包布局场景由 installer 的 core.hooksPath 路径覆盖。

## [2026-09-13] 判例 | 钩子权威上移适配层/插件（兑现 2026-09-06 判例预留方向，CH-0003）

- 场景：包 v1.2.2 用户级安装后与项目本地 hooks 并存，证据双写、门禁双跑（单边切换警告）。
- 决定：执行包 README 单边切换清单——删 `.claude/hooks/` 与 settings hooks 段、删 sp-* 技能镜像（保留自有四技能）、措辞改「插件提供」；推侧/拉侧权威统一为用户级插件（v1.2.2）。
- 代价：钩子行为随包版本走（本项目不再单独热修钩子）；规范级修正须回流适配层（GI-13 纪律，正是设计意图）。
