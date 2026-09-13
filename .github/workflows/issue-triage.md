---
emoji: 🧭
description: 新 Issue 分诊（sp-00 第零步投影）——三问判定薄道/全链，评论建议不代裁决
intent: 每个新开的工程 Issue 收到一条可核对的分诊建议；路线选择可由人随时改判
engine:
  id: claude
  env:
    ANTHROPIC_BASE_URL: "https://open.bigmodel.cn/api/anthropic"
    ANTHROPIC_MODEL: "glm-5.3-flash"
on:
  issues:
    types: [opened]
permissions:
  contents: read
  issues: read
tools:
  github:
    mode: gh-proxy
    toolsets: [issues]
safe-outputs:
  add-comment:
---

# Issue 分诊（薄道/全链三问）

## Task

对新打开的 Issue 做路由分诊，以一条评论给出建议。你的输出是建议，人是终审——评论末尾始终写明可由维护者改判。

### 分诊三问（对照仓库事实作答，不猜）

1. **影响面**：是否单一模块，且不触及公共 API/Contract、数据库 Schema、依赖/工具链、安全面？
2. **载体**：单个 PR 能承载全部改动，且本地验证（测试/lint/build）完整可跑？
3. **回退**：revert 这个改动是否干净、无残留（无迁移、无新增配置项、无外部状态）？

判定：

- 三条全为"是" → **薄道**：issue/implement/review/fix 四技能闭环，PR 四行描述（触发/范围/验证/收口），不建变更记录。
- 任一为"否"，或拿不准 → **全链**：按 AGENTS.md §1 场景路由表判定 JG 场景（JG-00..JG-09）走对应 SP 链，建 changes/ 变更记录；触及 major 判据（公共 API/Contract、Schema、依赖/工具链、安全面）注明并建议打 `major` 标签。
- 宁重勿漏：分诊不确定时一律建议全链。

### 评论格式

```text
分诊：<薄道 | 全链（JG-0x，SP 链）>
三问：影响面 <是/否 + 一句依据> / 载体 <…> / 回退 <…>
理由：<两三句，引用 Issue 内容与仓库事实>
（分诊是建议，可由维护者改判）
```

### noop

以下情况调用 noop 并附一句原因：Issue 与工程变更无关（纯问答/讨论/致谢）；Issue 明显重复（noop 原因中给出已有 Issue 编号）；Issue 信息不足以分诊时不要 noop——改用 add-comment 请作者补充目标与验收标准。

## Safe Outputs

- 分诊结论用 add-comment（恰好一条）。
- 缺信息时同样用 add-comment 请求补充。
- 其余情况用 noop + 原因，不写任何东西，不打标签。
