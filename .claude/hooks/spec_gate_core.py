# -*- coding: utf-8 -*-
"""spec-gate 判定核心：证据路径解析 + 时间新鲜度检查（单一判定权威）。

规则（SP-11 纪律的最小机械投影）：push 前必须存在晚于 HEAD 提交时间的
本地验证记录（evidence/runs.jsonl）。这是存在性检查，不是绿色判定——
跑没跑是机械事实，绿不绿是 SP-11 的工程判断。

两个入口都是薄壳，拒绝语义各随其主：
- Claude 钩子入口 push_gate.py   → stderr + exit 2
- git 层 pre-push 入口 push_gate_git.py → stderr + exit 1

不拦截的情形（职责外放行）：无提交 / 非 git 环境 / HEAD 时间不可解析。
绕过：SPEC_GATE_DISABLE=1（事后必须在 wiki/log.md 补记原因）。
测试重定向：SPEC_EVIDENCE_DIR 指定证据目录。
"""
import json
import os
import subprocess
from datetime import datetime

BYPASS_HINT = '确需绕过：SPEC_GATE_DISABLE=1，并在 wiki/log.md 补记原因。'


def parse_aware(s):
    """ISO 时间戳 → aware datetime（naive 视为本地时区）。"""
    dt = datetime.fromisoformat(s)
    return dt.astimezone() if dt.tzinfo is None else dt


def evidence_runs_path(project_root=None):
    """证据文件路径：SPEC_EVIDENCE_DIR > CLAUDE_PROJECT_DIR > project_root > cwd。"""
    root = os.environ.get('CLAUDE_PROJECT_DIR') or project_root or os.getcwd()
    return os.path.join(
        os.environ.get('SPEC_EVIDENCE_DIR') or os.path.join(root, 'evidence'),
        'runs.jsonl')


def head_info(cwd=None):
    """(原始时间串, aware datetime)。无提交/非 git/不可解析 → ('' 或 raw, None)。"""
    try:
        r = subprocess.run(['git', 'log', '-1', '--format=%cI'],
                           capture_output=True, text=True, cwd=cwd)
    except OSError:
        return '', None
    raw = (r.stdout or '').strip()
    if not raw:
        return '', None
    try:
        return raw, parse_aware(raw)
    except ValueError:
        return raw, None


def repo_toplevel(cwd=None):
    """git rev-parse --show-toplevel；非 git 环境返回 None。"""
    try:
        r = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                           capture_output=True, text=True, cwd=cwd)
    except OSError:
        return None
    return (r.stdout or '').strip() or None


def last_evidence_ts(runs_path):
    """末条记录的 ts（坏行跳过）；文件缺失/无有效 ts → None。"""
    last = None
    try:
        with open(runs_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ts = json.loads(line).get('ts')
                except json.JSONDecodeError:
                    continue
                if ts:
                    last = ts
    except OSError:
        pass
    return last


def gate(cwd=None, runs_path=None):
    """门禁判定。返回 (ok, msg)：ok=True 放行；False 时 msg 为拒绝理由。"""
    head_raw, head_dt = head_info(cwd)
    if head_dt is None:
        return True, ''  # 无提交/非 git/HEAD 时间不可解析：不在本门禁职责内
    ts = last_evidence_ts(runs_path or evidence_runs_path(cwd))
    if ts is None:
        return False, ('[spec-gate] push 被拦：evidence/runs.jsonl 没有验证记录。'
                       '先跑本地验证（SP-11，如 python -m pytest tests/ -q）再 push。'
                       + BYPASS_HINT)
    try:
        last_dt = parse_aware(ts)
    except (ValueError, TypeError):
        return False, '[spec-gate] evidence/runs.jsonl 时间戳不可解析——证据层异常，先修复再 push。'
    if last_dt <= head_dt:
        return False, (f'[spec-gate] push 被拦：HEAD（{head_raw}）之后没有新的验证记录'
                       f'（no-old-green-for-new-revision，SP-11 G-SP11-01 精神）。'
                       f'先跑本地验证再 push。' + BYPASS_HINT)
    return True, ''
