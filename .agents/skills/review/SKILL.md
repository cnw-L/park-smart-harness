---
name: review
description: 独立审查一个 PR：只依据 Issue + diff + 仓库 + CI 事实裁决，输出 APPROVE 或 REQUEST_CHANGES（Blocking/Non-blocking 分列）。必须在全新会话执行，不读实现者的过程记录。适用触发：PR 需要 review；fix 更新后复审。边界：不直接改代码；PR 描述写得漂亮不放行——描述是声明，代码是证据。
---

# review — 独立裁决

## 输入白名单（独立性纪律）

只读：Issue 正文与评论、PR diff、仓库代码、测试、CI 结果。
**不读**：实现 agent 的会话 / 聊天记录。PR 描述是实现者的**声明**，逐条对照代码核验，不当作事实。

## 检查清单（每条都要有结论）

1. 需求真的完成了吗——逐条对照 Issue 的 Acceptance。
2. 逻辑错误 / 只处理 happy path？边界、并发、异常、权限。
3. 破坏现有行为 / 兼容性了吗——对照 Issue 的 Constraints。
4. 有没有无关修改、过度工程、与项目既有模式冲突。
5. 测试真的覆盖了变化吗——新增/修改的行为有没有对应断言，还是只靠"测试是绿的"。
6. CI 真的跑了吗——green 之外看有没有 skipped / quarantined 掩盖改动路径。
7. 依赖 / 秘钥 / 生成物有没有被顺手引入。

## 输出（只有这两个形态，不建报告文件）

```text
APPROVE
或
REQUEST_CHANGES
Blocking: 1. <文件:行号> <违反的条目> <理由> …
Non-blocking: 1. …
```

用 `gh pr review --approve|--request-changes` 落到 GitHub，评论同步贴出。

## 纪律

- 每条 Blocking 必须可复核：代码位置 + 违反的条目；不确定的问题写 Non-blocking 并说明不确定什么。
- 连续多个 PR 零发现 ≠ 质量好，可能是 rubber-stamp——回头抽查自己是否真读了 diff。
