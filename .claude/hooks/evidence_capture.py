# -*- coding: utf-8 -*-
"""PostToolUse(Bash) 钩子：验证类命令真实执行后自动落盘 evidence/runs.jsonl。

这是 Evidence by Work 的机械载体（第五篇 SP-11）：
- 只记录事实（命令、输出尾部、可得时的退出码），不判断绿红——
  判定与绑定是 SP-11 A3/A4 的工程判断，不归机械层。
- SPEC_EVIDENCE_DIR：重定向输出目录（自检/测试用，勿污染正式证据）。
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

VERIF_PATTERNS = [
    r'\bpython\s+-m\s+pytest\b', r'\bpytest\b', r'\bpy\.test\b',
    r'\bpython\s+-m\s+unittest\b', r'\btox\b', r'\bnox\b',
    r'\bruff\b', r'\bmypy\b', r'\bflake8\b', r'\bpylint\b',
    r'\btsc\b', r'\beslint\b', r'\bvitest\b', r'\bjest\b',
    r'\bnpm\s+(?:run\s+)?test\b', r'\byarn\s+test\b', r'\bpnpm\s+test\b',
    r'\bnpm\s+run\s+lint\b', r'\byarn\s+lint\b', r'\bpnpm\s+lint\b',
    r'\bcargo\s+(?:test|clippy)\b', r'\bgo\s+(?:test|vet)\b',
    r'\bmake\s+\S*test\S*\b', r'\bgradle\w*\s+\S*test\S*\b', r'\bmvn\s+test\b',
]


def main():
    try:
        raw = sys.stdin.buffer.read().decode('utf-8', 'replace')
        if not raw.strip():
            return
        payload = json.loads(raw)
        if payload.get('tool_name') != 'Bash':
            return
        command = (payload.get('tool_input') or {}).get('command', '')
        if not any(re.search(p, command) for p in VERIF_PATTERNS):
            return
        resp = payload.get('tool_response') if isinstance(payload.get('tool_response'), dict) else {}
        out = resp.get('stdout') or resp.get('output') or ''
        err = resp.get('stderr') or ''
        tail = (out + ('\n' + err if err else ''))[-2000:]

        rec = {
            'ts': datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'),
            'tool': 'Bash',
            'command': command[:2000],
            'exit_code': resp.get('exitCode'),
            'output_tail': tail,
        }
        root = os.environ.get('CLAUDE_PROJECT_DIR') or payload.get('cwd') or os.getcwd()
        evdir = os.environ.get('SPEC_EVIDENCE_DIR') or os.path.join(root, 'evidence')
        os.makedirs(evdir, exist_ok=True)
        with open(os.path.join(evdir, 'runs.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception:
        pass  # 捕获钩子绝不阻断会话：丢一条记录可接受，打断工作不可接受


if __name__ == '__main__':
    main()
    sys.exit(0)
