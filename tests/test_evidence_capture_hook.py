# -*- coding: utf-8 -*-
"""CH-0001：evidence_capture 钩子的常驻验证。

两层：
- 匹配器单测（is_verification_command）：正例 = 真实执行位形态，
  反例 = 验证词仅出现在提示词/说明文本里的形态（含 A/B 试验误捕获事故命令）。
- 子进程端到端：stdin JSON → SPEC_EVIDENCE_DIR 隔离落盘断言，
  不触碰正式 evidence/runs.jsonl。
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / '.claude' / 'hooks' / 'evidence_capture.py'


@pytest.fixture(scope='module')
def hook():
    spec = importlib.util.spec_from_file_location('evidence_capture_under_test', HOOK_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


POSITIVES = [
    'python -m pytest tests/ -q',
    'python -X utf8 -m pytest tests/ -q',
    'pytest -q',
    'cd somewhere && python -m pytest tests/ -q',
    'python -m pytest tests/ -q 2>&1 | tail -3',
    'FOO=1 python -m pytest',
    'env SPEC_EVIDENCE_DIR=/tmp/x python -m pytest -q',
    'timeout 300 python -m pytest',
    'sudo python -m pytest -q',
    'bash -c "python -m pytest -q"',
    'sh -c "pytest -q | tail -2"',
    'uv run pytest -q',
    './venv/bin/pytest -q',
    'python3 -m unittest discover -s tests',
    'npm test',
    'npm run test:ci',
    'yarn test',
    'pnpm lint',
    'cargo test',
    'go test ./...',
    'make test',
    'mvn test',
]

NEGATIVES = [
    '',
    'ls -la',
    # A/B 试验误捕获事故的原始形态（2026-09-06 14:30，runs.jsonl 第 3 行）
    'claude -p "这个项目 pytest -q 有测试失败。请修复，让测试全部通过。" --allowedTools "Read Write Edit Glob Grep Bash"',
    'git commit -m "fix pytest failure"',
    'git commit -m "让 cargo test 不再挂"',
    'echo pytest',
    'grep -n pytest src/rounding.py',
    'cat evidence/runs.jsonl | grep pytest',
    'grep -c "go test" Makefile',
    'git push origin main',
    'python -c "print(\'pytest\')"',
]


@pytest.mark.parametrize('command', POSITIVES)
def test_matcher_accepts_real_verification(command, hook):
    assert hook.is_verification_command(command), command


@pytest.mark.parametrize('command', NEGATIVES)
def test_matcher_rejects_non_execution_mentions(command, hook):
    assert not hook.is_verification_command(command), command


def _run_hook(stdin_text, evidence_dir):
    env = dict(os.environ)
    env['SPEC_EVIDENCE_DIR'] = str(evidence_dir)
    env['CLAUDE_PROJECT_DIR'] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, '-X', 'utf8', str(HOOK_PATH)],
        input=stdin_text.encode('utf-8'),
        capture_output=True,
        env=env,
        timeout=60,
    )


def _payload(command, stdout='', exit_code=0):
    return json.dumps({
        'tool_name': 'Bash',
        'tool_input': {'command': command},
        'tool_response': {'stdout': stdout, 'exitCode': exit_code},
    })


def test_end_to_end_records_verification(tmp_path):
    proc = _run_hook(_payload('python -m pytest tests/ -q', stdout='476 passed', exit_code=0), tmp_path)
    assert proc.returncode == 0
    lines = (tmp_path / 'runs.jsonl').read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec['command'] == 'python -m pytest tests/ -q'
    assert rec['exit_code'] == 0
    assert '476 passed' in rec['output_tail']
    assert rec['tool'] == 'Bash'
    assert rec['ts']


def test_end_to_end_skips_quoted_mention(tmp_path):
    # 事故命令不再落盘
    proc = _run_hook(_payload('claude -p "...pytest -q..."'), tmp_path)
    assert proc.returncode == 0
    assert not (tmp_path / 'runs.jsonl').exists()


def test_end_to_end_ignores_non_bash_tool(tmp_path):
    proc = _run_hook(json.dumps({
        'tool_name': 'Read',
        'tool_input': {'file_path': 'tests/test_x.py'},
        'tool_response': {},
    }), tmp_path)
    assert proc.returncode == 0
    assert not (tmp_path / 'runs.jsonl').exists()


def test_end_to_end_survives_malformed_stdin(tmp_path):
    proc = _run_hook('not-json{{', tmp_path)
    assert proc.returncode == 0
    assert not (tmp_path / 'runs.jsonl').exists()
