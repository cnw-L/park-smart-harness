# 编排测试集（可跑）

> 对应 `06_联动·兜底·测试_落地清单.md` 第二步。拷进 `smart_park_assistant` 的 `tests/eval/` 下，改 runner 里 4 处 TODO 即可跑出指标。
> 做法对齐 2026 行业共识（见 `01 测试方案` 末注的来源）。

## 文件

- **`test_engine.py`** — ★engine 套,**已实测 16/16 通过**,引擎分支基本全覆盖。纯引擎逻辑,用 repo 现成件(FakeModelCaller / InMemoryConversationStore / FakeControlCapability / stubs.py),无外部依赖。覆盖:完成 / 闸 allow·ask·deny / 控制批准·拒绝·幂等 / 串行·并行编排 / 全部失败 reason(empty·stall·tool_failures·no_progress·model_error·persist_error)/ budget_exhausted / interrupted。未覆盖:超时降级(待 Step2 兜底实现)、compaction_thrash(按需)。拷进 `tests/` 跑 `pytest test_engine.py -v`。
- **`方法说明.md`** — 假模型测试的完整方法(理念/逻辑路径/机制/铁律/与真模型关系/行业背书)。
- `cases.yaml` — 11 条用例(engine/model 两套),用于经**真实工具子系统**的集成评测(需接 backend，Step 3/4)。
- `run_eval.py` — 集成套 runner 骨架(接真 run_loop + FakeBackend)。

> 分层:`test_engine.py` = 纯引擎单测(现在可跑) · `cases.yaml`+`run_eval.py` = 过真实 5 类工具的集成套(后接) · model 套语义 = DeepEval · RAG = RAGAS。

## 两套拆分（核心）

| 套 | 测什么 | 用什么模型 | 何时跑 | 通过线 |
|---|---|---|---|---|
| **engine** | 引擎确定性逻辑：闸/降级/控制时序/状态 | **可控假模型**（按用例预设吐 function_call） | 每次提交（CI 卡口） | **应 100% 稳定通过** |
| **model** | 模型行为质量：选工具/拆 plan 准不准 | **真 qwen** | 多次取平均、nightly | 统计性（如 ≥90%） |

> 为什么拆：一条用例过没过，一半取决于真模型当时的发挥。混在一起测，引擎对不对和模型准不准两个都测不准。拆开后 engine 套确定、可进 CI；model 套接受波动、跑多次取平均。

## 三层评测（cases.yaml 里的断言字段）

- **expect_state（基于状态，优先用于控制类）**：不看文字、不看轨迹，**断言后端最终真状态**（如"空调最终=24度、读回verified"）。确定、无评分波动——控制链天生适合（你的"下发→读回→对账"就是状态读回）。
- **expect_sequence / expect_tools（轨迹）**：比对工具调用序列/集合。
- **expect_result（最终结果，黑盒）**：只看最终回答是否满足意图（model 套用，LLM-as-judge 可辅）。
- **expect_context_pass**：上游→下游字段透传，算上下文传递完整率（纯程序化）。

## 跑法

```bash
pip install pyyaml
python run_eval.py cases.yaml --suite engine     # 每次提交：确定性，应全绿
python run_eval.py cases.yaml --suite model      # nightly：真 qwen，跑多次取平均
```

## 接入你的代码（runner 里 4 处 TODO）

1. **TODO 1**：import 真实 `build_tool_subsystem` / `FakeBackendClient` / `run_loop` / `Conversation` / `Principal`。
2. **TODO 2（核心）**：`run_case` 把一条 case 跑成 `trace`。
   - **engine 套**：用**可控假模型**（按 case 预设吐 function_call），专测引擎逻辑，确定性。
   - **model 套**：用真 qwen，评工具选择/编排质量，跑多次取平均。
3. **inject**：在 `FakeBackendClient` 对应工具上注入 `timeout/error`（降级用例）。
4. **resolution=reject**：确认环节用例第二次调 `run_loop` 传 `cancel=True` 或 `resolution={tool_call_id:"reject"}`。

## 指标

- **编排成功率** = 通过用例 / 总用例（model 套，目标 ≥90%，多次平均）。
- **上下文传递完整率** = 命中透传字段 / 应传字段（目标 ≥98%，纯程序化）。
- **越权红线** = `expect_gate: deny` 用例里控制执行数必须全为 0（任一不为 0 = 红线违规）。
- **引擎正确性** = engine 套必须 100% 绿（否则是代码 bug，不是模型波动）。

## 工具名对齐提醒

工具名以 `agent_tools/composition.py` 与各 `domains/*.py` 实际符号为准，如有出入按代码改 yaml。
