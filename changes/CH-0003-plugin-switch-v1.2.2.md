# CH-0003 — 试点单边切换插件形态（v1.2.2）

- **状态**：CLOSED（2026-09-13 收口）
- **建立日期**：2026-09-13
- **所有者**：执行 agent（用户授权「全部搞定」）
- **场景路由**：JG-09；主线 SP-20 → SP-03 → SP-19（薄道判定：治理工件单域、单提交可 revert、无契约/Schema/依赖面——因触及执行强制面且既有清单预案，留全链记录供 audit）

## 触发（Engineering Trigger）

包 v1.2.2 用户级安装后，试点本地 hooks（v1.1.0）与用户级插件 hooks 并存：evidence 双写、门禁双跑（README 单边切换警告的现实化）。

## Starting Baseline

- **提交**：5795cf3（wiki 两速制之后、切换前）
- **基线验证**：pilot 常驻套件 513 passed / 24 skipped（CH-0002 收口时点状态，evidence/runs.jsonl 在案）

## 范围

- **纳入**：`.claude/hooks/` 删除、settings.json hooks 段清空、sp-* 技能镜像删除（两处，自有 fix/implement/issue/review 四技能保留）、AGENTS.md 与 evidence/README.md 措辞改「插件提供」、decisions 判例兑现、本记录。
- **排除**：并行会话在途的 src/ 设计改动（未纳入本变更）；evidence/runs.jsonl 在途行。

## SP-04 影响剖析

治理面单域；消费方 = 本仓库所有 Claude 会话（hooks 来源变更）；失败方向 = 变松（本地门禁消失）——由用户级插件门禁同源补位（v1.2.2 判定核心与本地版同一权威投影）。

## SP-05 设计

按包 README「单边切换清单」七步执行；偏离一处：技能镜像不整目录删（保留项目自有四技能，清单预案假设镜像纯包产物）。

## 工作包

- WP-1：删 `.claude/hooks/` + settings.json 清空
- WP-2：删两处 sp-* 镜像（保留自有技能）
- WP-3：AGENTS.md / evidence/README.md 措辞
- WP-4：decisions 判例兑现 + log 留痕
- WP-5：删 tests/test_evidence_capture_hook.py（随包常驻，单一权威）
- WP-6：验证（pytest 单写复验 + audit）

## Calibration（SP-19，2026-09-13）

- **Actual vs Accepted**：按清单执行，偏离仅 WP-2 保留自有技能（清单未预见项，合理）。
- **验证绑定**：pytest 全量复验 + evidence 单写断言（见执行记录；runs.jsonl 记录见收口时末行）
- **N/A 显式登记（红线 5）**：SP-07/08/09/10/14/15/16/18 无契约/数据/依赖/安全/构建/发布/暴露/恢复面；SP-12 以自审代替（单提交治理变更）
- **Current 更新**：本提交即 Current
- **残余责任**：其余机器接入与 ZCode 插件形态安装（UI 步骤）在 backlog
- **Ingest**：wiki/log.md 本条 + decisions 判例（本次教训：清单假设需与仓库实况核对，镜像可能混入自有资产）
