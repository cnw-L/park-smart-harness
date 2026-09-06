# -*- coding: utf-8 -*-
"""PreToolUse(Bash) 钩子：git push 前置门禁（SP-11 纪律的最小机械投影）。

规则：push 前必须存在晚于 HEAD 提交时间的本地验证记录（evidence/runs.jsonl）。
这是存在性检查，不是绿色判定——跑没跑是机械事实，绿不绿是 SP-11 的工程判断。
不拦截：git push --dry-run / -n。
绕过：SPEC_GATE_DISABLE=1（事后必须在 wiki/log.md 补记原因）。
测试重定向：SPEC_EVIDENCE_DIR 指定证据目录。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime


def deny(msg):
    sys.stderr.write(msg + '\n')
    sys.exit(2)


def parse_aware(s):
    dt = datetime.fromisoformat(s)
    return dt.astimezone() if dt.tzinfo is None else dt


def main():
    try:
        raw = sys.stdin.buffer.read().decode('utf-8', 'replace')
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return
    command = (payload.get('tool_input') or {}).get('command', '')
    if not re.search(r'\bgit\b[^|;&]*\bpush\b', command):
        return
    if os.environ.get('SPEC_GATE_DISABLE') == '1':
        return
    if re.search(r'--dry-run|(?<![\S])-n(?![\S])', command):
        return

    cwd = payload.get('cwd') or os.getcwd()
    root = os.environ.get('CLAUDE_PROJECT_DIR') or cwd
    runs = os.path.join(
        os.environ.get('SPEC_EVIDENCE_DIR') or os.path.join(root, 'evidence'),
        'runs.jsonl')

    head = subprocess.run(['git', 'log', '-1', '--format=%cI'],
                          capture_output=True, text=True, cwd=cwd).stdout.strip()
    if not head:
        return  # 无提交/非 git 环境：不在本门禁职责内
    try:
        head_dt = parse_aware(head)
    except ValueError:
        return

    last_ts = None
    try:
        with open(runs, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ts = json.loads(line).get('ts')
                except json.JSONDecodeError:
                    continue
                if ts:
                    last_ts = ts
    except OSError:
        pass

    bypass = '确需绕过：SPEC_GATE_DISABLE=1，并在 wiki/log.md 补记原因。'
    if last_ts is None:
        deny(f'[spec-gate] push 被拦：evidence/runs.jsonl 没有验证记录。'
             f'先跑本地验证（SP-11，如 python -m pytest tests/ -q）再 push。{bypass}')
    try:
        last_dt = parse_aware(last_ts)
    except (ValueError, TypeError):
        deny('[spec-gate] evidence/runs.jsonl 时间戳不可解析——证据层异常，先修复再 push。')
    if last_dt <= head_dt:
        deny(f'[spec-gate] push 被拦：HEAD（{head}）之后没有新的验证记录'
             f'（no-old-green-for-new-revision，SP-11 G-SP11-01 精神）。'
             f'先跑本地验证再 push。{bypass}')


if __name__ == '__main__':
    main()
    sys.exit(0)
