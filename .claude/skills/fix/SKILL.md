---
name: fix
description: 按 Review 意见修复当前 PR：逐条确认问题、重读对应代码、最小修复、重跑验证、push 回同一 PR。适用触发：收到 REQUEST_CHANGES；CI 失败需要修复。边界：不静默改掉 reviewer 没提的东西；不同意意见时用评论说理而不是绕过。
---

# fix — Review → 更新 PR

## 方法

1. 逐条读 Review comments：先确认自己理解的问题与 reviewer 指出的一致（拿不准先在 PR 里问清）。
2. 重读对应代码——以代码为准，不以自己上次的记忆为准。
3. 只修 Blocking + 顺手可修的 Non-blocking；新发现的无关问题另开 Issue。
4. 跑标准验证；自检 diff；commit（引用 review 意见）；push 回**同一 PR**。
5. 不同意某条意见：在 PR 评论里给理由（代码事实 / 权衡），由 reviewer 复裁。不静默绕过，也不无脑顺从。
6. 请求复审 → 回到 review。

## 纪律

- 不为了过 review 把测试改弱 / 删断言；测试表达行为，改测试必须说明为什么行为定义本身变了。
- 每轮 push 都是新证据轮次：失败历史保留在 PR 对话里，**不 force-push 掩盖**。
