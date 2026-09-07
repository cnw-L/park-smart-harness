# CH-0002 — pilot 治理面升级到适配层 v1.1.0（23 技能 + hooks 权威同步 + 进化引擎入料口）

> 本记录自 templates/change-record-template.md 实例化（v1.1.0 新模板，含 Ingest 行）。

- **状态**：CLOSED（2026-09-07 收口）
- **建立日期**：2026-09-07
- **所有者**：执行 agent（Claude，受用户"你来完成吧"指令委托）
- **场景路由**：JG-05（治理工具链/配置受控升级）；主线 sp-00 分诊 → SP-01 → SP-03 → SP-09 → SP-11 → SP-19（分诊结论：major——治理载体全量替换，但产品代码零触碰）

## 触发（Engineering Trigger）

用户指令完成剩余目标。盘点发现 pilot 停在首装版（2026-09-06 da1f75f）：22 技能无 sp-00、push_gate 为 spec_gate_core 抽取前的旧架构、无 git 层门禁、无会话恢复；v1.0.1 起的消费侧改进（薄道分诊/会话恢复/change-record 模板/audit/R10 Ingest 核对）pilot 均未享受。适配层为权威源（hooks 注释明示"项目侧副本为安装投影"）。

## Starting Baseline

- **提交**：130605d
- **未纳入的现场**：工作区 src/agent_* 等未提交 WIP 为用户在途工作，如实登记，不被本变更提交
- **基线验证**：适配层 73 例全绿 + audit CH-0001 PASS（升级前判定面健康，evidence/runs.jsonl 记录 34）；pilot 产品套件 513 passed/24 skipped 为 CH-0001 收口时点状态

## 范围

- **纳入**：.agents/skills + .claude/skills（23 技能重装）；.claude/hooks（5 脚本权威同步）；.claude/settings.json（+SessionStart）；.git/hooks/pre-push（git 层门禁 shim）；AGENTS.md 技能数行；changes/ + wiki/ + evidence/（本记录与 Ingest）
- **排除**：src/ 与产品测试（用户 WIP，非本缺陷）；适配层与包仓（各自仓库提交，见包仓 ingest/R10 提交）

## 开放问题

- blocking-question：无
- managed-unknown：settings.json SessionStart 对已开会话不生效（自新会话起）——平台语义，登记为已知边界；个别证据行缺 exit_code 字段（行 37-45，R6/R8 不依赖，见 wiki/log 教训三）
- backlog：pilot 若改用插件安装需按包 README 单边切换清单执行（防双写）

## SP-04 影响剖析（最小执行，tailoring）

受影响对象：治理载体（skills/hooks/settings/git-hooks）；消费方：后续所有 Claude Code 会话与手动 git push；数据/依赖：无；安全面：门禁拒伪逻辑不变（SPEC_GATE_DISABLE 逃生阀保留）。失败方向分析：门禁变严（新增 git 层入口，手动终端 push 也被核）——变严方向，符合预期。

## SP-05 设计（Accepted Design）

走本地安装路径（`--install` + 文件同步），**不走插件安装**——避免插件 hooks 与本地 hooks 并存双写（包 README 单边切换警告）。git 层 shim 用 `git rev-parse --show-toplevel` 解析项目侧脚本路径（包模板 shim 是包布局专用）。判例见 wiki/decisions.md。

## 工作包

WP-1 技能重装（--install，23/23 双目录）；WP-2 hooks 权威同步（5 脚本 + 逐字比对）；WP-3 SessionStart 注册 + git pre-push shim；WP-4 进化引擎入料口验证（audit R10 实战 + /ingest 命令 + 新模板 Ingest 行——本记录即模板首用）。

## 执行记录（做了才记：追加，不改写）

- WP-1：--install 完成，.agents/skills 与 .claude/skills 各 23 目录；AGENTS.md 内核 §1-§4 与模板逐字一致（diff 证实），仅修技能数行 22→23
- WP-2：5 hooks 自适配层权威源复制，--strip-trailing-cr 逐字节比对一致；门禁/捕获矩阵 58 passed（evidence/runs.jsonl 记录 41）
- WP-3：settings.json +SessionStart（模拟 stdin 验证 4 行引导含 sp-00 分诊行）；.git/hooks/pre-push shim 落位（判例：不走 core.hooksPath）
- WP-4：audit R10 实战 CH-0001 PASS（wiki/log、decisions、impact 三处引用）；ingest.md 命令 + R10 四例测试；两端 85+85 passed、check-fresh FRESH（evidence/runs.jsonl 记录 42、43）

## Calibration（SP-19，2026-09-07）

- **Actual vs Accepted**：全部交付。偏差一：门禁 deny 路径未在 pilot 真实模拟（权限沙箱拦 `git push` 字面量），以权威源测试矩阵 58 例代证——已登记 wiki/log 教训二；偏差二：audit.md/ingest.md 插件命令 pilot 本地模式不可用（命令属插件分发），audit 走适配层跨项目调用（本文档审计即实证）。
- **验证绑定**：pilot 常驻套件 513 passed / 24 skipped（evidence/runs.jsonl 记录 45）；适配层 85 passed + 包内 85 passed（记录 43）；check-fresh FRESH（记录 37、38、40）。全绿后收口。
- **N/A 显式登记（红线 5）**：SP-02 不适用（项目已初始化）；SP-06 折叠进 WP 执行（单线变更无工作包依赖）；SP-07 无契约面；SP-08 无持久数据面；SP-10 无新增安全面（门禁逃生阀不变）；SP-12 以自审代替（单人项目，沿 CH-0001 先例）；SP-13/14 无候选/制品面（治理工件随仓版本化）；SP-15/16/17/18 无发布/暴露/恢复面；SP-21 非事件；SP-20 无弃用面（旧 hooks 被同路径覆盖，无残留）。
- **Current 更新**：本变更收口提交为 pilot 治理面 Current（23 技能 + hooks v1.1.0 权威投影 + git 层门禁）。
- **残余责任**：managed-unknown 两项（SessionStart 新会话生效；exit_code 字段完整性）转 wiki/log 观察；插件单边切换留 backlog（用户决策）。
- **Ingest**：wiki/log.md「[2026-09-07] Ingest | CH-0002」+ patterns/local-upgrade-path.md（新页）+ decisions（pre-push 判例）+ impact（本条）。
