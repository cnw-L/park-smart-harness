# CH-0001 — evidence_capture 验证命令识别收紧（段首匹配 + 引号感知）

- **状态**：CLOSED（2026-09-06 收口，见文末 Calibration）
- **建立日期**：2026-09-06
- **所有者**：执行 agent（Claude），用户试点委托链（"你全部帮我搞定吧" → "继续"）
- **场景路由**：JG-02（修改现有能力），主线 SP-01 → SP-03 → SP-04/05 → SP-06 → SP-11 → SP-12(自审) → SP-13 → SP-19

## 触发（Engineering Trigger）

A/B 试验（2026-09-06 14:30）实测：`evidence_capture.py` 把"验证词仅出现在引号字符串里"的命令也捕获为验证证据（实例：`claude -p "...pytest -q..."`，evidence/runs.jsonl 第 3 行）。超越原 wiki 处置"暂不动作"的新事实：**push_gate 只做时间新鲜度比较，一条误记录即可在无真实验证的情况下满足门禁**——严重度从"低频噪音"升为"门禁完整性缺陷"。

## Starting Baseline

- **提交**：`da1f75f`（治理首装工件入库：22 SP 技能 ×2 镜像 + AGENTS.md/CLAUDE.md + wiki/ + evidence/ + .claude/hooks/）
- **产品代码基线**：`0738587` + 用户未提交 WIP（src/agent_context、src/agent_loop、tests/ 9 文件 + src/telemetry.py）——如实登记，**不纳入本变更**，不被本变更提交
- **基线验证**：da1f75f 提交前全量 pytest `476 passed, 24 skipped`（evidence/runs.jsonl 有运行时绑定记录）
- **缺陷锚点**：`.claude/hooks/evidence_capture.py:15-24,36`（VERIF_PATTERNS 对整条命令正则搜索）
- **缺陷记录**：wiki/patterns/evidence-capture-regex-false-positive.md（处置"暂不动作"被本变更超越）

## SP-01 Current Context 摘要（事实状态）

| 项 | 状态 | 内容 |
|---|---|---|
| 缺陷机理 | fact | 整串正则匹配，引号内文本（提示词/commit message/echo）与引号外同权 |
| 消费方影响 | fact | push_gate 时间新鲜度可被误记录满足；人读证据流被污染 |
| 钩子权威源 | fact | **项目侧资产**：generate_skills.py 无 hooks 源码，D:\软件规范 全域无 hooks 文件，README 明示"项目侧落点"；当前唯一存在形态 = 本仓安装副本（原未入库，已随 da1f75f 物化） |
| 钩子常驻测试 | absent | 安装期仅 7 例临时 stdin 仿真，无持久测试文件 |

## 范围假设

**纳入**：`.claude/hooks/evidence_capture.py` 匹配逻辑重写；新增常驻测试 `tests/test_evidence_capture_hook.py`；wiki 处置更新与判例登记（收口时）。

**排除**：push_gate.py 自身逻辑（时间-only 判定是已登记的已知边界，非本缺陷）；适配层生成器（无 hooks 源码，权威在本仓）；用户 WIP；`.tmp-abtest/`。

## 开放问题（分类）

- 无 blocking-question。
- managed-unknown：匹配收紧的假阴性风险（真实验证被漏记）——缓解：常驻测试矩阵覆盖直接调用/管道/包装器形态；本仓工作流验证命令为直接调用（AGENTS.md §0）。可回解：测试红即回退。
- backlog（不阻塞）：hooks 权威是否上移适配层普适化（git 层 pre-push 候选已在适配层 README 登记）→ 收口时记 wiki/decisions.md。

## 执行条件

READY（impact entry 满足：触发有效、基线可绑定、无未解阻塞问题）。

## SP-04 影响剖析（最小执行，tailoring）

- 唯一机械消费方：`push_gate.py`（读 runs.jsonl 末条 ts 做新鲜度比较）。**记录行格式零变更** → 无 Source/Wire/语义契约影响；效果 = 误记录减少（门禁更难被无验证满足）。
- 人读消费方：证据流可信度上升。
- 数据：runs.jsonl append-only 保持，历史行不动。
- 依赖/配置/安全：无新依赖（纯 stdlib），无秘密面。
- 假阴性失败方向分析：漏记真实验证 → push 被拒（要求重跑验证）——失败模式是"更严"而非"更松"，安全性方向正确。

## SP-05 设计（Accepted Design）

`is_verification_command(command)` 替换整串正则：

1. **分段**：按 `&&`、`||`、`;`、`|`、换行切分。
2. **每段**：剥离前缀（`env`、`VAR=value` 赋值、`sudo`/`nohup`/`nice [-n N]`/`timeout N`/`command`）→ 取有效首 token 的 basename。
3. **段首判定**：
   - 直接命令集：pytest / py.test / tox / nox / ruff / mypy / flake8 / pylint / tsc / eslint / vitest / jest；
   - `python*`：`-m` 模块 ∈ {pytest, unittest, py.test}；
   - npm/yarn/pnpm：test / lint 形态；cargo：test/clippy；go：test/vet；make/gradle：目标含 test；mvn：test；
   - **执行包装器例外** {bash, sh, zsh, dash, ksh, ssh, docker, podman, kubectl, powershell, pwsh, cmd, uv, poetry, pipenv, hatch}：该段退化为旧式整段正则（引号保留，**宁可多记**——`bash -c "python -m pytest"` 是真实执行通道）。
4. 任一段命中 → True。

**关键裁决**：`claude` 不进包装器集——嵌套 agent 的验证由它自己会话的钩子捕获，本段只承载提示词文本（A/B 事故即此形态）。

**验证设计（SP-11 预定 Feedback Runs）**：新增常驻 `tests/test_evidence_capture_hook.py`——匹配器单测矩阵（正例 12：含本仓自身调用形态 `python -X utf8 -m pytest`、管道、赋值前缀、`bash -c`、`uv run`；反例 7：含 A/B 事故命令原文形态、`git commit -m "pytest"`、`echo`/`grep`/`cat|grep`）+ 子进程端到端 5 例（stdin JSON → SPEC_EVIDENCE_DIR 隔离断言；非 Bash 工具忽略；坏 JSON 不崩）。

## 工作包

WP-1 匹配器重写（单文件）；WP-2 常驻测试（单文件）；WP-3 全量回归 + 提交；WP-4 Ingest。无跨包依赖，串行执行。

## Calibration（SP-19，2026-09-06）

**Actual vs Accepted**：WP-1..4 全部交付，无实质性偏差。

- 基线物化：`da1f75f`（192 文件；用户产品 WIP 未触碰、未提交）
- 修复候选：`843d81f`（钩子重写 + 37 例常驻测试 + 本记录）
- 收口提交：本笔（wiki Ingest + 本记录 CLOSED + evidence 增量）

**验证绑定**：聚焦 37 passed（runs.jsonl 记录 18）；全量 513 passed / 24 skipped（记录 19）；真实数据回溯——19 条历史记录：17 真实验证零漏判、2 误捕获（记录 3、17）全剔除；修复提交自身含 "pytest" 字样未被捕（新匹配器活体自证）。

**N/A 显式登记（红线 5）**：SP-12 以自审代替（单人项目无第二评审人）；SP-14/15/17 无构建工件/发布/部署/目标环境面（仓内工具资产变更）；SP-08/09/10 无数据/依赖/安全面。

**Current 更新**：钩子匹配行为以 843d81f 后状态为 Current（evidence/README.md 的捕获范围描述仍然如实，无需修订）；wiki 判例与处置同步更新（见 wiki/decisions.md、wiki/patterns/evidence-capture-regex-false-positive.md）。
