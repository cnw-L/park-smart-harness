# -*- coding: utf-8 -*-
"""git 层 pre-push 入口：无 hooks 机制的 harness 的推侧兜底（如 Codex）。

安装：git config core.hooksPath <包>/git-hooks（包内 pre-push shim 调本脚本）。
判定逻辑在 spec_gate_core——与 Claude 钩子入口同一权威。
git 约定：pre-push 以非零退出拒绝 push（与 Claude 钩子的 exit 2 各随其主）。
stdin 是 ref 行（<local ref> <local sha> <remote ref> <remote sha>）：
本门禁只做仓库级新鲜度检查，不解析 ref，读掉 stdin 防 SIGPIPE 即可。
git push --dry-run 同样触发 pre-push；存在性检查语义仍成立，不特判。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import spec_gate_core  # noqa: E402


def main():
    try:
        sys.stdin.buffer.read()
    except Exception:
        pass
    toplevel = spec_gate_core.repo_toplevel()
    if not toplevel:
        return  # 非 git 环境：不在本门禁职责内
    ok, msg = spec_gate_core.gate(toplevel)
    if not ok:
        sys.stderr.write(msg + '\n')
        sys.exit(1)


if __name__ == '__main__':
    main()
    sys.exit(0)
