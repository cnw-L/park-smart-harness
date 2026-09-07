# AGENTS.md — park-smart-harness（智慧园区 agent harness）

> 本仓库按《软件项目开发工程规范指南》（五篇，SEALED 2026-09）第五篇执行规程开发。
> 技能源在 `.agents/skills/`（23 个技能：sp-00 场景路由 + 22 个 SP 规程，Agent Skills 开放标准；Claude Code 原生镜像在 `.claude/skills/`）：按需自动调取，不要通读。
> 角色不混淆：本仓库自身是一个 agent harness 产品（内圈控制循环 / 上下文组装 / 工具治理 / RAG）；开发它时，你是执行第五篇规程的工程 agent。

## 0. 项目速览

- 栈：Python；源码 `src/`，测试 `tests/`，依赖与工具配置在 `pyproject.toml`。
- 本地验证入口（SP-11）：`python -m pytest tests/ -q`。
- `wiki/` 是项目经验层（§3），`evidence/` 是证据层（§4）：随仓库走，勿删。

## 1. 场景路由（JG）

开始任何任务前，先确定当前场景，按主线走对应 SP 链（技能会自动按需加载）：

| 场景 | SP 主线 |
|---|---|
| JG-00 进入已有项目并找到 Current | SP-01 → SP-03 |
| JG-01 新项目从 0 到第一条正常 Change | SP-02 → SP-01 → SP-03 → SP-04 → SP-05；按需 SP-07 / SP-08 / SP-09 / SP-10 |
| JG-02 开发一个新能力 / 修改现有能力 | SP-01 → SP-03 → SP-04 → SP-05 → SP-06 → SP-11 → SP-12 → SP-13 → SP-14 → SP-15 → SP-17 → SP-19；按需 SP-07 / SP-08 / SP-09 / SP-10 / SP-16 / SP-18 |
| JG-03 修改公共 API / Event / Contract | SP-01 → SP-03 → SP-04 → SP-07 → SP-05 → SP-06 → SP-11 → SP-12 → SP-13 → SP-15 → SP-17 → SP-19 |
| JG-04 修改数据库 / Schema / Durable Data | SP-01 → SP-03 → SP-04 → SP-08 → SP-05 → SP-06 → SP-11 → SP-13 → SP-15 → SP-17 → SP-19 |
| JG-05 新增或升级 Dependency / Toolchain / Config | SP-01 → SP-03 → SP-04 → SP-09 → SP-10 → SP-11 → SP-12 → SP-13 → SP-14 → SP-15 → SP-17 → SP-19 |
| JG-06 构建并发布一个版本 | SP-13 → SP-14 → SP-15 → SP-17 → SP-19；按需 SP-18 |
| JG-07 部署后验证、扩大暴露或恢复 | SP-15 → SP-16 → SP-17；按需 SP-18 / SP-19 |
| JG-08 处理线上 Incident / Emergency | SP-21 → SP-18 → SP-17 → SP-19；按需 SP-03 |
| JG-09 维护、弃用、替换或 Retirement | SP-20 → SP-03 → SP-19 |

按需插入：SP-07 契约演进、SP-08 数据迁移、SP-09 依赖/工具链/配置、SP-10 安全/供应链、SP-16 暴露控制、SP-18 恢复。

## 2. 红线（GI 级，任何情况下不豁免）

1. **禁止直接写 Current**——Current 的唯一更新通道是 SP-19 Calibration（SP-15/SP-17 的 Ch7 域执行期提交与 SP-22 资产面除外，见各规程）。
2. **硬门禁不可跳过**——技能里的 hard-gate 条目（如 SP-11 的 no-rerun-until-green、material-feedback-bound-at-runtime）违反即返回重来，没有"这次特殊"。
3. **失败不当成功**——跳过的检查不是通过；平台 UI 绿灯、exit 0 不等于验证完成（SP-11 G-SP11-01..10）。
4. **证据运行时绑定**——证据在动作发生时产生，禁止事后补造（backfilled bindings are not evidence）。
5. **N/A 必须显式登记并给理由**，不得静默丢弃义务（GI-17）。
6. **投影分歧修投影不改源**（GI-13）；研究报告/中间文档不是规范正文（GI-14）。

## 3. 项目经验层（wiki/）使用规约

- 执行 agent 访问 wiki 的**唯一入口是 `wiki/index.md`**（先读索引，再按需深入单页；不要 ls 全库读全文）。
- `wiki/log.md` append-only，条目前缀 `## [日期] 类型 | 标题`。
- 每个真实 Change 结束时执行 Ingest：把本次教训（踩坑、workaround、被门禁拦下的原因）提炼进 `wiki/patterns/`，判例进 `wiki/decisions.md`。
- 探索中产生的好答案（对比结论、排查结论）回填 wiki，不留在聊天记录里。
- **判例不立法**：wiki 是本项目经验，不是规范；发现规范级问题走 SP-22 提案回流，不改本地技能正文。
- 技能/规程在本项目的每次重要生效或被拒，记入 `wiki/impact.md`（拒绝也留档，防重复提案）。

## 4. 证据层（evidence/）

- 验证类命令（测试/构建/lint）的真实输出由 hooks 自动落盘到 `evidence/runs.jsonl`——这是 Evidence by Work 的载体，不可手改。捕获范围与规约详见 [evidence/README.md](evidence/README.md)。
- `git push` 前置门禁会检查是否存在晚于 HEAD 提交的验证记录（SP-11 纪律）；无记录时先跑验证。临时绕过：环境变量 `SPEC_GATE_DISABLE=1`（事后须补记原因到 log.md）。
- 本仓库当前有未提交的工作区改动时，push 门禁只看时间先后（最小机械投影），改没改对、绿不绿仍由 SP-11/SP-12 的规程判断承担。
