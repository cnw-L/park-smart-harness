# -*- coding: utf-8 -*-
"""PreToolUse(Bash) 钩子：git push 前置门禁（SP-11 纪律的最小机械投影）。

判定逻辑在 spec_gate_core（单一权威，git 层 pre-push 入口共用）；
本文件只是 Claude 钩子薄壳：stdin JSON → 匹配/逃生 → deny 时 exit 2。
不拦截：git push --dry-run / -n。
绕过：SPEC_GATE_DISABLE=1（事后必须在 wiki/log.md 补记原因）。
测试重定向：SPEC_EVIDENCE_DIR 指定证据目录。
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import spec_gate_core  # noqa: E402


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
    ok, msg = spec_gate_core.gate(cwd)
    if not ok:
        sys.stderr.write(msg + '\n')
        sys.exit(2)


if __name__ == '__main__':
    main()
    sys.exit(0)
