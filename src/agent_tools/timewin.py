"""自然语言时间窗解析 —— 把"今天/本月/最近7天"解析成后端要的 `beginTime/endTime`。

确定性规则解析(闭域、无额外 LLM 调用),覆盖常见说法;解析不出→返回空窗(调用方据此
诚实降级成累计口径,不冒充区间)。格式 `yyyy-MM-dd HH:mm:ss`(后端 java.util.Date 要求)。
时间锚定 `datetime.now()`(服务器当前时间),非写死。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

_FMT = "%Y-%m-%d %H:%M:%S"


def _begin(d: datetime) -> str:
    return d.replace(hour=0, minute=0, second=0, microsecond=0).strftime(_FMT)


def _end(d: datetime) -> str:
    return d.replace(hour=23, minute=59, second=59, microsecond=0).strftime(_FMT)


def parse_time_window(text: str | None, *, now: datetime | None = None) -> tuple[str | None, str | None, str]:
    """NL 时间 → (begin, end, label)。解析不出→(None, None, "")。"""
    t = (text or "").replace(" ", "")
    if not t:
        return (None, None, "")
    now = now or datetime.now()

    if "今天" in t or "今日" in t:
        return (_begin(now), _end(now), "今天")
    if "昨天" in t or "昨日" in t:
        y = now - timedelta(days=1)
        return (_begin(y), _end(y), "昨天")
    # "最近N天" 先于"一周/一个月"关键词,使"最近7天"如实标"最近7天"(非"最近一周")
    m = re.search(r"(?:最近|近|过去)(\d+)天", t)
    if m:
        n = int(m.group(1))
        return ((now - timedelta(days=n)).strftime(_FMT), now.strftime(_FMT), f"最近{n}天")
    # "最近一个月" 要先于 "本月"(避免 "月" 字误命中)
    if "最近一个月" in t or "近一个月" in t:
        return ((now - timedelta(days=30)).strftime(_FMT), now.strftime(_FMT), "最近一个月")
    if "最近一周" in t or "近一周" in t or "过去一周" in t:
        return ((now - timedelta(days=7)).strftime(_FMT), now.strftime(_FMT), "最近一周")
    if "本月" in t or "这个月" in t or "当月" in t:
        return (_begin(now.replace(day=1)), now.strftime(_FMT), "本月")
    if "上月" in t or "上个月" in t:
        last_end = now.replace(day=1) - timedelta(days=1)
        return (_begin(last_end.replace(day=1)), _end(last_end), "上月")
    if "本周" in t or "这周" in t or "这一周" in t:
        monday = now - timedelta(days=now.weekday())
        return (_begin(monday), now.strftime(_FMT), "本周")
    if "今年" in t or "本年" in t:
        return (_begin(now.replace(month=1, day=1)), now.strftime(_FMT), "今年")
    return (None, None, "")
