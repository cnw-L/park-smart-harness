"""编排测试 runner（骨架，拷进 smart_park_assistant repo 后改 4 处 TODO 即可跑）。

两套（行业标准）：
- engine 套：可控假模型按用例预设吐 function_call → 测引擎确定性逻辑（闸/降级/控制时序/状态），每次提交跑、应全绿。
- model  套：真 qwen → 测工具选择/编排质量，多次取平均、nightly 跑。

评测优先用 state-based（断言后端最终状态，确定无波动），尤其控制类；轨迹/结果为辅。

跑法：
    pip install pyyaml
    python run_eval.py cases.yaml --suite engine     # 确定性，应全绿
    python run_eval.py cases.yaml --suite model      # 真模型，多次取平均
"""
from __future__ import annotations

import sys
import asyncio
from dataclasses import dataclass, field

import yaml

# ───────────────────────── TODO 1：接你真实的组合根与引擎 ─────────────────────────
# from agent_tools.composition import build_tool_subsystem
# from agent_tools.backend import FakeBackendClient
# from agent_loop.loop import run_loop
# from agent_loop.conversation import Conversation
# from agent_loop.budget import BudgetTracker
# from agent_context.principal import Principal
# from <your_llm> import make_model_caller, make_scripted_model   # 真 qwen / 可控假模型


@dataclass
class Step:
    tool: str
    args: dict
    result: object
    is_error: bool = False


@dataclass
class Trace:
    steps: list[Step] = field(default_factory=list)
    gate_verdicts: list[str] = field(default_factory=list)
    final_text: str = ""
    backend_state: dict = field(default_factory=dict)   # ★ state-based：跑完后的后端真实状态快照
    control_executed_count: int = 0


# ───────────────────────── TODO 2：把一条 case 跑成 trace ─────────────────────────
async def run_case(case: dict) -> Trace:
    """跑一条用例，返回 trace（含 backend_state 快照，供 state-based 断言）。

    engine 套：用可控假模型（按 case 预设吐 function_call）→ 确定性。
    model  套：用真 qwen → 评模型选择/编排质量。
    inject → 在 FakeBackendClient 对应工具注入 timeout/error。
    resolution=reject → 第二次 run_loop 传 cancel=True 或 resolution={...:"reject"}。
    跑完从 FakeBackendClient 读后端状态写进 trace.backend_state（state-based 评测的数据源）。
    """
    raise NotImplementedError("接 run_loop + 记录钩子 + 跑后读 backend 状态（见 docstring）")


# ───────────────────────── 断言 ─────────────────────────
def _tools(trace: Trace) -> list[str]:
    return [s.tool for s in trace.steps]


def check_state(trace: Trace, expect_state: dict) -> bool:
    """★ 基于状态的评测：断言后端最终真实状态（确定、无评分波动）。控制类优先用这个。"""
    ok = True
    st = {**trace.backend_state,
          "control_executed_count": trace.control_executed_count,
          "final_text": trace.final_text}
    for k, v in expect_state.items():
        if k == "user_msg_contains":
            ok &= v in trace.final_text
        elif k == "final_value":
            ok &= st.get("final_value") == v
        else:
            ok &= st.get(k) == v
    return ok


def check_sequence(trace, expect_seq) -> bool:
    seq = iter(_tools(trace))
    return all(t in seq for t in expect_seq)        # 子序列匹配


def check_tools(trace, expect_tools) -> bool:
    return set(expect_tools).issubset(set(_tools(trace)))


def check_context_pass(trace, expect_pass) -> tuple[int, int]:
    hit = 0
    for p in expect_pass:
        st, sf = p["from"].split("."); dt, da = p["to"].split(".")
        if _first_result_field(trace, st, sf) is not None and \
           _first_result_field(trace, st, sf) == _first_arg(trace, dt, da):
            hit += 1
    return hit, len(expect_pass)


def _first_result_field(trace, tool, field):
    for s in trace.steps:
        if s.tool == tool and isinstance(s.result, dict) and field in s.result:
            return s.result[field]
    return None


def _first_arg(trace, tool, arg):
    for s in trace.steps:
        if s.tool == tool and arg in s.args:
            return s.args[arg]
    return None


# ───────────────────────── 主流程 + 指标 ─────────────────────────
async def main(path: str, suite: str | None):
    cases = yaml.safe_load(open(path, encoding="utf-8"))["cases"]
    if suite:
        cases = [c for c in cases if c.get("suite") == suite]
    n = len(cases)
    ok_count = 0
    ctx_hit = ctx_total = 0
    redline_violations = []

    for c in cases:
        trace = await run_case(c)
        passed = True
        if "expect_state" in c:                         # ★ 优先 state-based
            passed &= check_state(trace, c["expect_state"])
        if "expect_sequence" in c:
            passed &= check_sequence(trace, c["expect_sequence"])
        if "expect_tools" in c:
            passed &= check_tools(trace, c["expect_tools"])
        if "expect_context_pass" in c:
            h, t = check_context_pass(trace, c["expect_context_pass"]); ctx_hit += h; ctx_total += t
        if c.get("expect_gate") == "deny" and trace.control_executed_count != 0:
            redline_violations.append(c["id"])
        ok_count += int(passed)
        print(f"[{'PASS' if passed else 'FAIL'}] ({c.get('suite')}) {c['id']}")

    print(f"\n──── 指标 (suite={suite or 'all'}) ────")
    print(f"通过率 = {ok_count}/{n} = {ok_count/n:.1%}"
          + ("   (engine 套应=100%)" if suite == "engine" else "   (model 套目标≥90%，多次取平均)"))
    if ctx_total:
        print(f"上下文传递完整率 = {ctx_hit}/{ctx_total} = {ctx_hit/ctx_total:.1%}   (目标 ≥98%)")
    print(f"越权红线 = {'通过(0 违规)' if not redline_violations else '违规: '+','.join(redline_violations)}   (必须 0)")


if __name__ == "__main__":
    args = sys.argv[1:]
    path = next((a for a in args if not a.startswith("--")), "cases.yaml")
    suite = None
    if "--suite" in args:
        suite = args[args.index("--suite") + 1]
    asyncio.run(main(path, suite))
