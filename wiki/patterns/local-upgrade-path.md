# 本地安装路径升级（避免插件双写）与门禁多入口布局

**现象**：治理工具链（适配层）持续演进（v1.0.0→v1.1.0），试点项目停在首装版；升级有两条路——插件安装（`--package` 产物装进 Claude Code）与本地安装路径（`generate_skills.py --install` + 文件同步）。

**根因**：同一项目内插件 hooks 与本地 hooks 注册并存会双写（evidence 落两条、门禁双跑）——包 README「单边切换警告」。

**Workaround（已实证 CH-0002）**：试点期升级走本地路径，四步——
1. `--install <项目根>`（只动 `.agents/skills` + `.claude/skills`，AGENTS.md 明确不自动覆盖）；
2. hooks 权威同步：复制后用 `diff --strip-trailing-cr` 逐字节比对（Windows CRLF 噪音必须剥离再比）；
3. settings.json 增量注册新钩子事件（如 SessionStart）；模拟 stdin 验证（注意：命令串含 `git push` 字面量会被权限沙箱拦——改走测试矩阵验证路径）；
4. git 层门禁 shim 写 `.git/hooks/pre-push`，用 `git rev-parse --show-toplevel` 解析项目侧脚本路径（包模板 shim 是包布局专用，不通用）。

**适用边界**：单项目本地模式。多项目分发或非 Claude harness（Codex）→ 插件/安装器路径（installer/install_codex.py），届时按单边切换清单先卸本地注册。

**证据**：CH-0002（23/23 技能、5 hooks 逐字一致、513 passed/24 skipped 零产品影响）。
