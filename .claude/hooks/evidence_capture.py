# -*- coding: utf-8 -*-
"""PostToolUse(Bash) 钩子：验证类命令真实执行后自动落盘 evidence/runs.jsonl。

这是 Evidence by Work 的机械载体（第五篇 SP-11）：
- 只记录事实（命令、输出尾部、可得时的退出码），不判断绿红——
  判定与绑定是 SP-11 A3/A4 的工程判断，不归机械层。
- SPEC_EVIDENCE_DIR：重定向输出目录（自检/测试用，勿污染正式证据）。
- 匹配为段首判定（CH-0001，2026-09-06）：验证词必须出现在执行位
  （段首命令、python -m 模块、或执行包装器通道内）；引号里的提示词 /
  说明文本不再误捕获。历史：整串正则把 `claude -p "...pytest..."` 也
  记成验证证据，且一条误记录即可满足 push_gate 的时间新鲜度检查。

权威源说明（2026-09-06 打包）：本文件自 park-smart-harness 回流为适配层
权威源（CH-0001 修复版，逐字节），由 generate_skills.py --package 投影进
software-spec-guide 包；项目侧副本为安装投影，缺陷修复改这里再重装。
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

# 段首直接命中的验证命令
DIRECT_VERIF = {
    'pytest', 'py.test', 'tox', 'nox',
    'ruff', 'mypy', 'flake8', 'pylint',
    'tsc', 'eslint', 'vitest', 'jest',
}

# python -m <mod> 形态的验证模块
PYTHON_VERIF_MODULES = {'pytest', 'py.test', 'unittest'}

# 执行包装器：该段退化为整段正则（引号保留，宁可多记）——
# bash -c "python -m pytest" / ssh / docker exec / uv run 是真实执行通道。
# claude 不在此列：嵌套 agent 的验证由它自己会话的钩子捕获，
# 本段只承载提示词文本（A/B 试验误捕获事故即此形态）。
EXEC_WRAPPERS = {
    'bash', 'sh', 'zsh', 'dash', 'ksh', 'ssh',
    'docker', 'podman', 'kubectl',
    'powershell', 'pwsh', 'cmd',
    'uv', 'poetry', 'pipenv', 'hatch',
}

# 包装器段内的宽松正则（保持旧整串匹配的覆盖面）
VERIF_PATTERNS = [
    r'\bpython\d*(?:\.\d+)?\s+-m\s+(?:pytest|py\.test|unittest)\b',
    r'\bpytest\b', r'\bpy\.test\b', r'\btox\b', r'\bnox\b',
    r'\bruff\b', r'\bmypy\b', r'\bflake8\b', r'\bpylint\b',
    r'\btsc\b', r'\beslint\b', r'\bvitest\b', r'\bjest\b',
    r'\bnpm\s+(?:run\s+)?test\b', r'\byarn\s+test\b', r'\bpnpm\s+test\b',
    r'\bnpm\s+run\s+lint\b', r'\byarn\s+lint\b', r'\bpnpm\s+lint\b',
    r'\bcargo\s+(?:test|clippy)\b', r'\bgo\s+(?:test|vet)\b',
    r'\bmake\s+\S*test\S*\b', r'\bgradle\w*\s+\S*test\S*\b', r'\bmvn\s+test\b',
]

_SEGMENT_SPLIT = re.compile(r'&&|\|\||;|\||\n')
_PREFIX = re.compile(r'^(?:sudo|nohup|command|env|nice(?:\s+-n\s+\d+)?|timeout\s+\S+)\s+')
_ASSIGN = re.compile(r'^[A-Za-z_]\w*=\S*\s+')
_PY_MOD = re.compile(r'-m\s+([A-Za-z_][\w.]*)')
_PY_HEAD = re.compile(r'python\d+(?:\.\d+)?|python')


def _segment_is_verification(seg):
    s = seg.strip()
    while True:
        m = _PREFIX.match(s) or _ASSIGN.match(s)
        if not m:
            break
        s = s[m.end():]
    if not s:
        return False
    tokens = s.split()
    head = re.split(r'[\\/]', tokens[0])[-1]  # basename 化（./venv/bin/pytest 等）
    if head in EXEC_WRAPPERS:
        return any(re.search(p, s) for p in VERIF_PATTERNS)
    if head in DIRECT_VERIF:
        return True
    if _PY_HEAD.fullmatch(head):
        return any(mod in PYTHON_VERIF_MODULES for mod in _PY_MOD.findall(s))
    if head == 'npm':
        args = tokens[1:]
        if args[:1] == ['test']:
            return True
        return len(args) >= 2 and args[0] == 'run' and args[1].startswith(('test', 'lint'))
    if head in ('yarn', 'pnpm'):
        args = tokens[1:]
        if args[:2] == ['run'] and len(args) > 1:
            args = args[1:]
        return bool(args) and args[0].startswith(('test', 'lint'))
    if head == 'cargo':
        return len(tokens) > 1 and tokens[1] in ('test', 'clippy')
    if head == 'go':
        return len(tokens) > 1 and tokens[1] in ('test', 'vet')
    if head == 'make':
        return any('test' in t for t in tokens[1:])
    if head in ('gradle', 'gradlew'):
        return any('test' in t for t in tokens[1:] if not t.startswith('-'))
    if head == 'mvn':
        return len(tokens) > 1 and tokens[1] == 'test'
    return False


def is_verification_command(command):
    """验证词是否出现在执行位（任一 shell 段的段首 / 包装器通道内）。"""
    return any(_segment_is_verification(seg) for seg in _SEGMENT_SPLIT.split(command or ''))


def main():
    try:
        raw = sys.stdin.buffer.read().decode('utf-8', 'replace')
        if not raw.strip():
            return
        payload = json.loads(raw)
        if payload.get('tool_name') != 'Bash':
            return
        command = (payload.get('tool_input') or {}).get('command', '')
        if not is_verification_command(command):
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
