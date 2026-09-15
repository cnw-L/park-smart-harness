"""harness_rag 查询改写解析行为锚定（issue #18）。

二轮修复检索直接消费 parse_rewrite_plan 的产物（rewritten_queries[0] 成为
repair policy 的检索 query），解析错则二轮检索整体失效——这里的用例按
prompts.QA_QUERY_REWRITE_PROMPT 承诺的输出格式逐分支锚定真实行为。
"""

from harness_rag.evidence import EvidenceItem, RetrievalDiagnostics
from harness_rag.policy import QueryRewriteStrategy
from harness_rag.prompts import QA_QUERY_REWRITE_PROMPT
from harness_rag.rewrite import LlmQueryRewriter, parse_rewrite_plan


def test_standard_key_value_output():
    plan = parse_rewrite_plan(
        "strategy: subquestions\n"
        "query: 园区门禁怎么配置\n"
        "query: 访客通行权限如何开通\n"
        "reason: 首轮无命中",
        original_query="门禁",
        max_queries=5,
    )
    assert plan.strategy is QueryRewriteStrategy.SUBQUESTIONS
    assert plan.rewritten_queries == ["园区门禁怎么配置", "访客通行权限如何开通"]
    assert plan.reason == "首轮无命中"
    assert plan.original_query == "门禁"


def test_chinese_keys_and_full_width_colon():
    plan = parse_rewrite_plan(
        "策略：回溯\n检索词：园区停车收费标准\n问题： Visitor parking fee\n原因：首轮分数过低",
        original_query="停车",
        max_queries=5,
    )
    assert plan.strategy is QueryRewriteStrategy.BACKTRACK
    assert plan.rewritten_queries == ["园区停车收费标准", "Visitor parking fee"]
    assert plan.reason == "首轮分数过低"


def test_strategy_aliases_and_case_insensitive():
    cases = [
        ("subquestions", QueryRewriteStrategy.SUBQUESTIONS),
        ("Subquestion", QueryRewriteStrategy.SUBQUESTIONS),
        ("子问题", QueryRewriteStrategy.SUBQUESTIONS),
        ("SPECIFICATION", QueryRewriteStrategy.SPECIFICATION),
        ("specific", QueryRewriteStrategy.SPECIFICATION),
        ("具体化", QueryRewriteStrategy.SPECIFICATION),
        ("backtrack", QueryRewriteStrategy.BACKTRACK),
        ("回溯", QueryRewriteStrategy.BACKTRACK),
    ]
    for value, expected in cases:
        plan = parse_rewrite_plan(
            f"Strategy: {value}\nQUERY: q", original_query="oq", max_queries=5
        )
        assert plan.strategy is expected, value
        assert plan.rewritten_queries == ["q"]


def test_unknown_strategy_keeps_previous_or_default():
    default = parse_rewrite_plan("strategy: expand\nquery: q", original_query="oq", max_queries=5)
    assert default.strategy is QueryRewriteStrategy.BACKTRACK

    kept = parse_rewrite_plan(
        "strategy: specification\nstrategy: 不知道的策略\nquery: q",
        original_query="oq",
        max_queries=5,
    )
    assert kept.strategy is QueryRewriteStrategy.SPECIFICATION


def test_pipe_format_with_and_without_strategy():
    with_strategy = parse_rewrite_plan(
        "subquestions | 园区门禁如何授权 | 访客如何申请通行",
        original_query="oq",
        max_queries=5,
    )
    assert with_strategy.strategy is QueryRewriteStrategy.SUBQUESTIONS
    assert with_strategy.rewritten_queries == ["园区门禁如何授权", "访客如何申请通行"]

    without_strategy = parse_rewrite_plan(
        "园区门禁如何授权 | 访客如何申请通行", original_query="oq", max_queries=5
    )
    assert without_strategy.strategy is QueryRewriteStrategy.BACKTRACK
    assert without_strategy.rewritten_queries == ["园区门禁如何授权", "访客如何申请通行"]


def test_plain_lines_strip_list_markers():
    plan = parse_rewrite_plan(
        "- 园区访客如何登记\n* 停车月卡怎么办\n1. 食堂营业时间\n2、门禁权限申请流程",
        original_query="oq",
        max_queries=5,
    )
    assert plan.rewritten_queries == [
        "园区访客如何登记",
        "停车月卡怎么办",
        "食堂营业时间",
        "门禁权限申请流程",
    ]


def test_marker_stripped_kv_line_still_parsed():
    plan = parse_rewrite_plan(
        "- strategy: backtrack\n- query: 园区应急处置流程", original_query="oq", max_queries=5
    )
    assert plan.strategy is QueryRewriteStrategy.BACKTRACK
    assert plan.rewritten_queries == ["园区应急处置流程"]


def test_query_value_split_on_separators():
    plan = parse_rewrite_plan(
        "queries: 园区开放时间；食堂几点开门，健身房收费吗; 游泳池",
        original_query="oq",
        max_queries=5,
    )
    assert plan.rewritten_queries == ["园区开放时间", "食堂几点开门", "健身房收费吗", "游泳池"]


def test_only_first_colon_splits_key_value():
    plan = parse_rewrite_plan("query: 值班时间: 周一到周五", original_query="oq", max_queries=5)
    assert plan.rewritten_queries == ["值班时间: 周一到周五"]


def test_dedup_preserves_order_and_truncates_to_max_queries():
    plan = parse_rewrite_plan(
        "query: 园区导航\n"
        "query: 车位查询\n"
        "query: 园区导航\n"
        "query: 访客登记\n"
        "query: 报修流程\n"
        "query: 缴费",
        original_query="oq",
        max_queries=3,
    )
    assert plan.rewritten_queries == ["园区导航", "车位查询", "访客登记"]


def test_empty_output_falls_back_to_original_query():
    for text in ["", "   \n  ", "strategy: backtrack\nquery:\n"]:
        plan = parse_rewrite_plan(text, original_query="园区停车怎么收费", max_queries=5)
        assert plan.strategy is QueryRewriteStrategy.BACKTRACK, repr(text)
        assert plan.rewritten_queries == ["园区停车怎么收费"], repr(text)
        assert plan.reason == ""


def _capture_chat(output: str):
    captured = {}

    async def chat(*, system: str, user: str) -> str:
        captured["system"] = system
        captured["user"] = user
        return output

    return captured, chat


async def test_llm_rewriter_wires_prompt_and_parse():
    captured, chat = _capture_chat("strategy: specification\nquery: 具体化后的检索词")
    evidence = [
        EvidenceItem(id=f"e{i}", chunk_text=f"{'0' * 180}-TAIL{i}" if i == 0 else f"片段{i}")
        for i in range(4)
    ]
    diagnostics = RetrievalDiagnostics(best_rerank_score=0.42)

    plan = await LlmQueryRewriter(chat=chat).rewrite(
        query="原问题",
        reason="首轮分数过低",
        evidence=evidence,
        diagnostics=diagnostics,
        max_queries=3,
    )

    assert plan.strategy is QueryRewriteStrategy.SPECIFICATION
    assert plan.rewritten_queries == ["具体化后的检索词"]
    assert captured["system"] == QA_QUERY_REWRITE_PROMPT
    assert "原问题" in captured["user"]
    assert "首轮分数过低" in captured["user"]
    assert "0.42" in captured["user"]
    assert "最多改写 query 数量：3" in captured["user"]


async def test_llm_rewriter_prompt_truncates_evidence_to_three_snippets():
    captured, chat = _capture_chat("query: q")
    evidence = [
        EvidenceItem(id=f"e{i}", chunk_text=f"{'0' * 180}-TAIL{i}") for i in range(4)
    ]

    await LlmQueryRewriter(chat=chat).rewrite(
        query="原问题",
        reason="r",
        evidence=evidence,
        diagnostics=RetrievalDiagnostics(),
        max_queries=5,
    )

    # 每条片段只保留 answer_text 前 180 字符，最多取前 3 条
    assert "- e0: " in captured["user"]
    assert "-TAIL0" not in captured["user"]
    assert "-TAIL1" not in captured["user"]
    assert "-TAIL2" not in captured["user"]
    assert "- e3:" not in captured["user"]


async def test_llm_rewriter_prompt_without_evidence():
    captured, chat = _capture_chat("query: q")

    await LlmQueryRewriter(chat=chat).rewrite(
        query="原问题",
        reason="r",
        evidence=[],
        diagnostics=RetrievalDiagnostics(),
        max_queries=5,
    )

    assert "首轮片段：\n无" in captured["user"]
