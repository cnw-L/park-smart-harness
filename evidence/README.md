# evidence/ — Evidence by Work 载体

- `runs.jsonl` 由 `.claude/hooks/evidence_capture.py`（PostToolUse/Bash）在验证类命令（pytest / ruff / mypy / npm test / cargo test 等）真实执行后自动追加。每行一条 JSON：`ts`、`command`、`exit_code`（可得时）、`output_tail`（尾部摘录）。
- 机械层只记录事实，不判定绿红：跑没跑是门禁检查的事实；绿不绿、绑定是否成立、失效条件是否触发，是 SP-11 A3/A4/A5 的工程判断（见 `.agents/skills/` 中 SP-11 技能）。
- 本层不可手改、不可事后补造（backfilled bindings are not evidence）。
- 捕获范围当前仅限 Claude Code 的 Bash 命令；在其他 harness（如 Codex CLI）下运行验证时，由执行 agent 在运行当下以同构 JSON 行追加记录并注明来源字段 `source: manual-runtime`（仍是运行时产生，不是补造）。
- `git push` 前置门禁（`.claude/hooks/push_gate.py`）检查是否存在晚于 HEAD 提交时间的验证记录；绕过须 `SPEC_GATE_DISABLE=1`，事后在 `wiki/log.md` 补记原因。
- 建议随仓库提交（轻量尾部摘录，可回溯）；若体积失控再议裁剪策略（届时记入 wiki 判例）。
