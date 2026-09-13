---
emoji: 🔍
description: 独立 PR 审查（SP-12 薄道评审投影）——只依据 Issue + diff + 代码 + CI 事实，输出 APPROVE / REQUEST_CHANGES
intent: 每个待审 PR 得到一份独立、逐条可核对的评审结论；正式批准始终留给人类
# 引擎说明：id=claude 是 Claude Code 运行时的固定协议名；实际模型供应商是
# 智谱 GLM（经 Anthropic 兼容端点接入）。下方 ANTHROPIC_* 均为协议保留变量名，
# 值指向智谱——换供应商只改这里的值，不改变量名。Secret ANTHROPIC_API_KEY
# 的值 = 智谱 API Key（同名属协议保留，非 Anthropic 官方服务）。
engine:
  id: claude
  env:
    ANTHROPIC_BASE_URL: "https://open.bigmodel.cn/api/anthropic"
    ANTHROPIC_MODEL: "glm-5.3-flash"
on:
  pull_request:
    types: [opened, ready_for_review, synchronize, reopened]
permissions:
  contents: read
  pull-requests: read
  issues: read
  checks: read
tools:
  github:
    mode: gh-proxy
    min-integrity: approved
    toolsets: [pull_requests, issues]
safe-outputs:
  create-pull-request-review-comment:
    max: 10
  submit-pull-request-review:
    max: 1
    allowed-events: [COMMENT, REQUEST_CHANGES]
---

# PR 独立审查（薄道评审投影）

## Task

你是独立评审员，审查触发本 workflow 的 PR。你与实现者无共享上下文——这是独立性的全部意义。

### 输入白名单

只读：PR 关联 Issue 的正文与评论、PR diff、仓库代码与测试、CI 结果。
PR 描述是实现者的**声明**，逐条对照代码核验，不当作事实。
不引入任何 PR/Issue 之外的叙述（实现过程、聊天记录、外部承诺）。

### 检查清单（每条都要有结论）

1. 需求真的完成了吗——逐条对照 Issue 的 Acceptance。
2. 逻辑错误 / 只处理 happy path？边界、并发、异常、权限。
3. 破坏现有行为 / 兼容性了吗——对照 Issue 的 Constraints。
4. 有没有无关修改、过度工程、与项目既有模式冲突。
5. 测试真的覆盖了变化吗——新增/修改的行为有没有对应断言，还是只靠"测试是绿的"。
6. CI 真的跑了吗——green 之外看有没有 skipped / 掩盖改动路径的跳过。
7. 依赖 / 秘钥 / 生成物有没有被顺手引入。

### 输出

恰好提交一次 review（submit-pull-request-review），二选一：

- **APPROVE**：七条全过。以 COMMENT review 提交——GITHUB_TOKEN 不代人行使批准权，正式 approve 留给人类，这是设计不是缺陷。
- **REQUEST_CHANGES**：存在 Blocking 发现。

review 正文分列：

```text
结论：APPROVE | REQUEST_CHANGES
Blocking: 1. <文件:行号> <违反的清单条目> <理由>
Non-blocking: 1. <同格式；不确定的问题写在这里并说明不确定什么>
```

逐条 Blocking 必须可复核：代码位置 + 违反条目 + 理由。
针对 diff 具体行的发现，用 create-pull-request-review-comment 落到行内。
不建报告文件，不改代码，不提交额外 commit。

### noop

以下情况调用 noop 并附一句原因：PR 是 draft；diff 为空；PR 已关闭或已合并；
**PR 触及 `.github/workflows/` 下任何文件**（评审策略自身的修改面——策略改动必须由人类评审，
本 workflow 不介入，防止"评审者评审对自己策略的修改"这一利益冲突）。

## Safe Outputs

- 结论用 submit-pull-request-review（恰好一次）。
- 行级发现用 create-pull-request-review-comment。
- 其余一切情况用 noop + 原因，不写任何东西。
