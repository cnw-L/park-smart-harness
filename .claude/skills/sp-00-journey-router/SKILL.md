---
name: sp-00-journey-router
description: 软件规范场景路由入口（软件项目开发工程规范指南·第五篇）：任何工程任务开始时先调用本技能做第零步分诊（薄道 minor / 全链 major），再判定 JG-00..JG-09 场景，按主线依次调用对应 SP 规程技能；含 6 条 GI 红线、evidence/push 门禁推侧护栏说明与项目接入自检。适用触发：任何开发任务开始；不确定走哪条 SP 链；JG 场景判定；项目尚未接入规范。边界：只做路由与收口规则，不替代任何 SP 规程本体。
metadata:
  spec.part5.kind: journey-router
  spec.part5.version: 1.1.0
  spec.part5.generated: generate_skills.py（产物不可手改，GI-13）
---

# 场景路由内核（JG）｜软件项目开发工程规范指南·第五篇

> 本技能是 AGENTS.md 路由内核的技能化投影（产物不可手改，GI-13）；
> 规范级变更走 SP-22 提案回流，不改本文件。
> 项目已定制 AGENTS.md 时，以项目版为准（项目规约压过通用内核）。

## 何时用我

任何工程任务的第一步：先做第零步分诊定深度，再判定场景（JG），按链调用 SP 规程技能。
不确定走哪条链、或进入一个陌生项目时，从下面的路由表开始。

## 第零步 · 分诊（先定深度，再定场景）

三个问题（约 2 分钟）：

1. **影响面**：是否只触及单模块/局部，且不触及对外契约、数据库 Schema、依赖/工具链、安全面？
2. **载体**：能否由单个 PR 承载并完整走完本地验证？
3. **回退**：出问题能否 revert 干净了结，无数据/部署迁移残留？

- 三条全是 → **薄道（minor）**：不建 changes/ 文件，变更记录折叠为 PR 描述四行
  （触发 / 范围 / 验证 / 收口 Calibration）；走 SP-06 实现 + SP-11 本地验证；push 门禁照常生效。
  薄道同样留痕——PR 描述就是记录。
- 任一为否 → **全链（major）**：按模板建立 changes/CH-xxx 变更记录
  （templates/change-record-template.md，做了才记：随执行逐段追加），再按下方场景表走主线。
- 拿不准 → 按全链。宁重勿漏：GI-03 裁剪改的是深度，不是义务；未收口的 changes/ 记录
  会在下次会话由 SessionStart 引导提示恢复现场。

## 第一步 · 判定场景（JG-00..09）

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

## 第二步 · 按链调用 SP 技能

| SP | 技能名 | 名称 | 工程动作 |
|---|---|---|---|
| SP-01 | sp-01-current-authority-navigation | Current / Authority 导航 | 找真实 Current、Owner、Authority、Evidence |
| SP-02 | sp-02-project-bootstrap-initialization-procedure | Project Bootstrap | 建立 truthful Bootstrap 与 Foundation |
| SP-03 | sp-03-change-establishment-starting-baseline | Change Establishment | 建立 Change、Starting Baseline |
| SP-04 | sp-04-impact-scope-analysis | Impact / Scope Analysis | 找受影响对象和深度 |
| SP-05 | sp-05-technical-design-decision | Technical Design / Decision | Target/Transition/Design |
| SP-06 | sp-06-work-package-implementation-control | 工作包实现控制 | 代码和工程实现 |
| SP-07 | sp-07-contract-evolution | Contract Evolution | API/Event/Schema 兼容演进 |
| SP-08 | sp-08-data-migration-evolution-controlled-execution | Data / Migration Evolution | Schema/Migration/Backfill |
| SP-09 | sp-09-dependency-toolchain-config-controlled-evolution | 依赖/工具链/配置受控变更 | 依赖、工具链、配置受控变更 |
| SP-10 | sp-10-security-supply-chain-control | 安全/供应链控制 | Secure env/check/provenance |
| SP-11 | sp-11-local-verification | 本地验证 | 本地/快速验证 |
| SP-12 | sp-12-review-shared-integration | Review / Shared Integration | Review、共享基线进入 |
| SP-13 | sp-13-candidate-evidence-binding | 候选与证据绑定 | Candidate 与 Required Verification |
| SP-14 | sp-14-build-artifact-provenance | 构建/工件/出处 | Canonical Build / Package |
| SP-15 | sp-15-release-deployment | 发布/部署 | Target-scoped delivery |
| SP-16 | sp-16-feature-exposure-flag-lifecycle | 暴露控制/Flag 生命周期 | Deployment 与 Launch 解耦 |
| SP-17 | sp-17-target-validation-release-completion | 目标验证/可观测 | 运行验证与真实观察 |
| SP-18 | sp-18-recovery-execution | 恢复执行 | Rollback/Rollforward/Compensation |
| SP-19 | sp-19-calibration-current-update-change-closure | 校准/Current/收口 | Actual vs Accepted、Current 更新、Change 收口 |
| SP-20 | sp-20-maintenance-debt-deprecation-retirement | 维护/弃用/退役 | 长期维护与退出 |
| SP-21 | sp-21-incident-emergency | 事件/应急 | Mitigate/Reconcile |
| SP-22 | sp-22-execution-asset-lifecycle | 执行资产生命周期 | Guide/Template/Workflow 自身治理 |

Claude Code 中技能带命名空间前缀 `software-spec-guide:<技能名>`；其他 harness（Codex 等）按技能名自动发现。

## 红线（GI 级，任何情况下不豁免）

1. **禁止直接写 Current**——Current 的唯一更新通道是 SP-19 Calibration（SP-15/SP-17 的 Ch7 域执行期提交与 SP-22 资产面除外，见各规程）。
2. **硬门禁不可跳过**——技能里的 hard-gate 条目（如 SP-11 的 no-rerun-until-green、material-feedback-bound-at-runtime）违反即返回重来，没有"这次特殊"。
3. **失败不当成功**——跳过的检查不是通过；平台 UI 绿灯、exit 0 不等于验证完成（SP-11 G-SP11-01..10）。
4. **证据运行时绑定**——证据在动作发生时产生，禁止事后补造（backfilled bindings are not evidence）。
5. **N/A 必须显式登记并给理由**，不得静默丢弃义务（GI-17）。
6. **投影分歧修投影不改源**（GI-13）；研究报告/中间文档不是规范正文（GI-14）。

## 推侧护栏（hooks，机械强制）

- 验证类命令（测试/构建/lint）真实执行后自动落盘 `evidence/runs.jsonl`——只记事实不判绿红，不可手改、不可事后补造。
- `git push` 前置门禁：必须存在晚于 HEAD 提交的验证记录；无记录先跑本地验证（SP-11）。
- 绕过：`SPEC_GATE_DISABLE=1`（事后必须补记 wiki/log.md）；测试重定向：`SPEC_EVIDENCE_DIR`。
- 其他 harness（无 hooks 机制）按 `source: manual-runtime` 同构补记（见 evidence 规约）。

## 项目接入自检

- 项目没有 AGENTS.md / wiki/ / evidence/ ？建议运行 `/software-spec-guide:init` 引导安装规范工件。
- 已接入？遵循项目 AGENTS.md（其 §1-§4 与本技能同源；冲突时项目版优先）。

## 维护

本技能与全部 SP 技能都是生成产物：规范变更 → SP-22 提案 → 修订正式规程 → 重新生成重装。
发现技能正文与规程分歧：修投影（重新生成），不手改（GI-13）。
