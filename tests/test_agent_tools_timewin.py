"""NL 时间窗解析单测(锚定固定 now,确定性)。"""
from __future__ import annotations

from datetime import datetime

from agent_tools.timewin import parse_time_window

_NOW = datetime(2026, 6, 22, 14, 30, 0)   # 周一? 2026-06-22 是周一 → weekday()=0


def test_today():
    b, e, label = parse_time_window("今天的工单", now=_NOW)
    assert b == "2026-06-22 00:00:00" and e == "2026-06-22 23:59:59" and label == "今天"


def test_this_month():
    b, e, label = parse_time_window("本月报修", now=_NOW)
    assert b == "2026-06-01 00:00:00" and e.startswith("2026-06-22") and label == "本月"


def test_last_n_days():
    b, e, label = parse_time_window("最近7天的告警", now=_NOW)
    assert b == "2026-06-15 14:30:00" and label == "最近7天"


def test_recent_week_keyword():
    b, e, label = parse_time_window("最近一周新增多少工单", now=_NOW)
    assert b == "2026-06-15 14:30:00" and label == "最近一周"


def test_recent_month_before_this_month():
    # "最近一个月" 不应被 "本月" 误命中
    b, e, label = parse_time_window("最近一个月", now=_NOW)
    assert label == "最近一个月" and b == "2026-05-23 14:30:00"


def test_unparseable_returns_empty():
    assert parse_time_window("某个不确定的时间", now=_NOW) == (None, None, "")
    assert parse_time_window("", now=_NOW) == (None, None, "")
