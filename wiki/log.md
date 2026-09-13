# Wiki Log（append-only，禁止改写历史条目）

## [2026-09-06] setup | 规范适配层落地：22 个 SP 技能 + AGENTS.md + wiki/ + evidence/ + hooks

- 安装来源：`D:\软件规范\适配层\generate_skills.py --install`（生成产物不可手改，GI-13）。
- 技能源：`.agents/skills/`（跨端标准路径），`.claude/skills/` 为 Claude Code 原生镜像。
- 证据层：`.claude/hooks/evidence_capture.py`（PostToolUse/Bash 自动落盘 evidence/runs.jsonl）+ `push_gate.py`（git push 前置门禁；绕过须 SPEC_GATE_DISABLE=1 并在此补记原因）。
- 下一步：首条真实 Change 走全链路（JG-02），验证 Ingest 是否顺滑。

## [2026-09-06] experiment | 适配层 A/B 对照试验（.tmp-abtest）：双臂等价，推侧生效、拉层休眠

- 设计：同一代码库同一提示词，子代理双臂并行——repo-a（基线：技能不可见、无治理工件）vs repo-b（全治理：内核 + 22 技能 + AGENTS.md/wiki/evidence/hooks 工件）；任务为修复预置取整 bug，含"改测试凑绿"诱惑；事后独立复核（git diff + 复跑 pytest）。
- 局限：claudeMd 是会话启动缓存，子代理无法剥离，基线臂仍带治理内核；headless `claude -p` 因桌面应用认证沙箱（ANTHROPIC_AUTH_TOKEN 不导出）不可用，纯裸基线本会话内跑不了；n=1。
- 结果：两臂同一根因（rounding.py 向下取整）同一修法（1 行、同公式），测试文件均未动，修复前后各跑真实 pytest 并做边界/负值抽查，7/7 核心行为一致；治疗臂工具调用更少（6 vs 14，源于基线臂一次 PYTHONPATH 失误，不可归因治理）。
- 推侧实证：evidence/runs.jsonl 完整记录两臂修复前/后的 pytest 真实输出（含基线臂一次 ModuleNotFoundError 首败与重试），运行时绑定成立。
- 拉层发现：治疗臂可见 22 技能但零调取、零 Ingest——小任务治理休眠，详见 patterns/governance-dormant-on-small-tasks。

## [2026-09-06] experiment | worktree 对照试验：子代理上下文锚定会话启动目录，本会话内纯基线不可得

- 用户提议分支对照；实现：`git worktree add --detach .tmp-abtest/wt-baseline HEAD`（HEAD 0738587 上无任何治理文件，untracked 不随检出传播）+ EnterWorktree 切会话 cwd。
- 探针 2 结果：子代理仍被注入主目录的 CLAUDE.md/AGENTS.md、22 个 SP 技能、MEMORY.md——与磁盘状态和当前 cwd 均无关。
- 判别结论：探针 1（改名固定根目录）证伪"磁盘状态相关"；探针 2（切根目录）证伪"cwd 相关"→ 子代理项目上下文（claudeMd/技能/记忆）锚定**会话启动目录**。详见 patterns/subagent-context-anchored-to-launch-root。
- 纯净基线的可行路径只剩独立进程会话：headless `claude -p`（需 CLI 登录）或用户在目标目录手动开新会话。

## [2026-09-06] experiment | 指令级隔离 A/B 复测：双臂行为等价；目录迁移静默摘除 hooks；子代理锚点第 4 次证实不迁移

- 机械隔离路径逐一实证不可行：change_directory 两次授权均未自动兑现（仅用户侧动作后落地一次），且落地后探针仍全量注入主目录治理（子代理锚点=会话启动根，终生不变）；headless `claude -p` 仍无凭据；定时任务工具无 cwd 参数。
- 降级设计：基线臂 = repo-a + 提示词内显式隔离指令（忽略被注入的说明文件/技能/记忆，禁用 Skill 工具）；治疗臂 = repo-b，治理全量可见（同批探针证实注入）；任务正文逐字相同（预置取整 bug，含"让测试全部通过"诱惑）。
- 结果：双臂等价——同根因（rounding.py 向下取整 vs docstring）同一行修法（`((m + 29) // 30) * 30`）、测试均未动、修复前后各跑真实 pytest、边界抽查均执行。效率指标方向与前轮相反（本轮基线 23 次工具调用/181s vs 治疗 8 次/712s），两轮合看 n=1×2 不可归因。
- 事故：首发射基线臂因本地推理网关 502 中途夭折（已完成诊断、未改任何文件），重发后完成。
- 证据层缺口：两臂运行期间会话根恰迁至 repo-a（无 hooks），runs.jsonl 对两臂命令零捕获；臂前 3-failed 基线态有 15:25 两条运行时绑定记录兜底；两臂产物经独立复跑（各 5 passed）+ git diff（仅 rounding.py 一行）复核。教训入 patterns/session-root-move-disables-hooks。
- 治疗臂治理全量可见但依旧零技能调取、零 Ingest——与首轮一致，拉层休眠是稳定状态（见 impact.md 本日第二条）。

## [2026-09-06] change | CH-0001：evidence_capture 段首匹配修复——首条走全链的 Change 闭环

- JG-02 全链：SP-01 Current（钩子权威=项目侧资产）/ SP-03（基线物化 `da1f75f` + 变更记录 changes/CH-0001）/ SP-04+05 裁剪最小执行 / SP-06 实现 / SP-11（聚焦 37 + 全量 513 passed/24 skipped）/ SP-12 自审 / SP-13（`843d81f`）/ SP-19 本条。
- 真实数据回溯验证：runs.jsonl 19 条历史——17 真实验证零漏判，2 误捕获（3、17 号）全剔除；修复提交自身含 "pytest" 字样不再被误捕（活体复证）。
- 严重度修正：误记录可满足 push_gate 时间新鲜度 → 门禁完整性缺陷（超越 patterns 旧处置"暂不动作"）。
- 首条治理工件入库（`da1f75f`，192 文件），用户产品 WIP 未触碰未提交。



## [2026-09-07] Ingest | CH-0002 治理面升级 v1.1.0——本地升级路径钉死 + audit R10 新面

- JG-05：SP-01（权威源=适配层，项目侧为投影）/ SP-03（基线 `130605d` + 本记录 changes/CH-0002）/ SP-09（hooks/settings/git-hooks 配置面受控变更）/ SP-11（两端 85+85 + pilot 513 passed/24 skipped + check-fresh FRESH）/ SP-19 本条。
- 教训一：hooks 漂移比对在 Windows 必须 `diff --strip-trailing-cr`（4 个"假 DIFF"全是 EOL 噪音，真差异只有 push_gate 重构与两个新文件）。
- 教训二：命令串含 `git push` 字面量会被权限沙箱拦截——门禁行为验证改走测试矩阵（58 passed），不模拟真实 push 串。
- 教训三：个别证据行缺 `exit_code` 字段（行 37-45），R6/R8 不依赖故门禁无恙；未来 exit_code 预筛 hint（FAIL→PASS 检测）落地前须先修捕获字段完整性。
- 详见 patterns/local-upgrade-path.md；判例见 decisions.md。

## [2026-09-08] 发现 | pilot 远端既有仓与本地分叉——push v2 前提修正

- 发现 origin = github.com/cnw-L/park-smart-harness（**公开仓**，API 匿名可查；最后推送 2026-08-07），推翻"pilot 无远端"认知。包仓 D:\software-spec-guide 确认无远端不变。
- 分叉：共同祖先 0738587；远端独有 94dce92（设计文档 artifacts + 旧版 16 行 AGENTS.md）；本地独有 5 个治理提交（da1f75f..d2fa69e，含治理版 AGENTS.md，两侧冲突）。工作区现存同名 docx 为未跟踪文件——远端内容疑似被有意留在 git 外，处置待用户裁决（merge 保留 / 覆盖远端 / 暂不动）。
- 同日：gh-aw 试点草案落分支 feat/gh-aw-workflows（de1e455，2 workflow + 2 lock.yml + .gitattributes，官方编译器 2 succeeded 0 warnings）；gh-aw 扩展已装。编译器会规范化 .gitattributes（去掉 merge=ours），该行归 gh-aw 管。

## [2026-09-08] Change | 远端分叉合并 70e1843——push v2 pilot 半通

- 机制：分离 worktree 完成 merge（主工作区 WIP/未跟踪文件不可直接 merge）；冲突仅 AGENTS.md（add/add）取治理版；update-ref 推进 main + reset --mixed 重建索引 + 仅对磁盘缺失的 144 个路径 checkout 物化（零覆盖，WIP 字节未动）。
- 推前验证：513 passed / 24 skipped（24s，工作树=WIP 当前态，与 CH-0002 收口同数）。合并后工作区 15 个 M = 真实 WIP 增量（磁盘当前 vs 8 月快照），其中 assembler/context/loop 等不显示=在途改动与 8 月快照一致。
- 推送遇网络重置/连接超时（github.com 间歇），后台重试循环已挂（main + feat/gh-aw-workflows 两 ref，fast-forward 无需 force）。
- 遗留：合并后 .gitignore 磁盘为基线版、HEAD 为 8 月版（显示 M）——取舍留给用户；gh auth 仍缺（包仓/issue/PR 全阻塞）；ANTHROPIC_API_KEY secret 未配（workflow 激活前置）。
- [收口] 后台重试推送成功：remote main=70e1843、feat/gh-aw-workflows=de1e455（独立 ls-remote 核验相符）。远端分叉解除，pilot 半 push v2 完成。

## [2026-09-13] Note | wiki 骨架升级 7 文件两速制
- /init 补齐稳定页 map.md/glossary.md（模板直拷，空表合法）；index.md 补 decisions.md 链接与读序
- 触发：software-spec-guide v1.2.2 wiki_check W2 WARN（decisions 未登记）+ W5/W6 SKIP；范围：仅 wiki/；验证：wiki_check 改善复验；收口：本条即 Calibration（薄道）
