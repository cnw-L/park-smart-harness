# -*- coding: utf-8 -*-
"""SessionStart 钩子：向会话注入 software-spec-guide 引导（≤5 行）。

superpowers 式引导：让 agent 一开局就知道规范技能包在场、入口是哪个技能。
- SPEC_GUIDE_DISABLE=1 → 静默（仍 exit 0）。
- 会话恢复：检测 <项目>/changes/ 下未收口（OPEN）的变更记录并提示恢复现场——
  跨会话链条不断线（做了才记：只认记录里的显式状态行）。
- 任何异常吞掉：引导钩子绝不阻断会话启动。
"""
import os
import re
import sys

LINES = [
    '[software-spec-guide] 软件开发规范技能包已启用（第五篇执行规程 SP-01..SP-22）。',
    '工程任务开始时先调用 software-spec-guide:sp-00-journey-router：第零步分诊（薄道/全链），再判定场景（JG-00..09）按链调用 SP 技能。',
    '验证类命令自动落盘 evidence/runs.jsonl；git push 前需存在晚于 HEAD 的验证记录（绕过：SPEC_GATE_DISABLE=1，事后补记 wiki/log.md）。',
    '项目未接入规范工件（AGENTS.md/wiki/evidence）时，可用 /software-spec-guide:init 引导安装。',
]

_STATE_RE = re.compile(r'\*\*状态\*\*：\s*(OPEN|CLOSED)')


def find_open_changes():
    """扫描 <root>/changes/*.md，返回仍为 OPEN 的 (变更号, 标题, 文件名) 列表。"""
    root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    chdir = os.path.join(root, 'changes')
    if not os.path.isdir(chdir):
        return []
    found = []
    for name in sorted(os.listdir(chdir)):
        if not name.endswith('.md'):
            continue
        try:
            with open(os.path.join(chdir, name), encoding='utf-8', errors='ignore') as f:
                text = f.read(64 * 1024)
        except OSError:
            continue
        m = _STATE_RE.search(text)
        if not m or m.group(1) != 'OPEN':
            continue
        title = next((l.lstrip('# ').strip() for l in text.splitlines()
                      if l.startswith('# ') and 'CH-' in l), name[:-3])
        found.append((title.split(' — ')[0].strip(), title, name))
    return found


def restore_lines():
    """未收口变更提示：≤1 行（聚合同一批），绝不展开全文（渐进披露）。"""
    opens = find_open_changes()
    if not opens:
        return []
    if len(opens) == 1:
        cid, title, name = opens[0]
        return [f'[software-spec-guide] 未收口变更：{cid}（changes/{name}）——'
                f'继续前先读它恢复现场，再走 sp-00 第零步。']
    ids = '、'.join(cid for cid, _, _ in opens[:6])
    more = f' 等 {len(opens)} 条' if len(opens) > 6 else ''
    return [f'[software-spec-guide] 未收口变更 {len(opens)} 条：{ids}{more}——'
            f'继续前先读对应 changes/ 文件恢复现场。']


def main():
    try:
        sys.stdin.buffer.read()  # SessionStart payload 当前不需要，读掉即可
        if os.environ.get('SPEC_GUIDE_DISABLE') == '1':
            return
        out = LINES + restore_lines()
        sys.stdout.write('\n'.join(out) + '\n')
    except Exception:
        pass


if __name__ == '__main__':
    main()
    sys.exit(0)
