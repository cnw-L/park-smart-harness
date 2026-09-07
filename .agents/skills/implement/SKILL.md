---
name: implement
description: 从一个 GitHub Issue 交付一个 PR。读 Issue 和相关代码后做最小必要修改并补测试，跑项目标准验证，自检 diff 后创建 PR。适用触发：拿到 Issue 编号开始开发；继续未完成的实现。边界：不自行扩大范围；需求歧义回 Issue 评论澄清而不是猜。
---

# implement — Issue → PR

## 输入

Issue 编号 + 仓库。先读 Issue，再读 AGENTS.md 的验证入口。

## 方法

1. 读 Issue 与 Likely affected 对应的代码和现有测试；确认实现边界（Constraints 不可破坏）。
2. 新建分支 `feat|fix/<issue#>-<slug>`。
3. 修改最小必要代码；行为变化必须补测试；只改与本 Issue 相关的东西。
4. 跑 AGENTS.md 声明的标准验证（测试/lint/build）；失败先分类（产品缺陷 / 测试缺陷 / 环境）再修。
5. 自检 `git diff`：无无关改动、无调试残留、无意外文件。
6. Commit 引用 Issue（`(#128)`）；创建 PR。

## PR 描述（四行——它就是变更记录）

```text
触发：<issue# 一句话>
范围：改了什么、没改什么（含明确的"不改"清单）
验证：<实际执行的命令 + 结果 + 关键证据>
收口：<对照 Issue Acceptance 逐条；未竟事项如实列出>
```

## 纪律

- 验证不过不能声称完成；skipped / flaky 的测试不是通过。
- 不能自我裁决的取舍（回滚窗口、兼容策略）→ 写进 PR"收口"节向 reviewer / 人显式提问，不静默选。
- 范围变大（发现新的受影响面）→ 回 Issue 补记；触及 major 判据时改打标签。
- 一个 Issue 一个 PR；混合关注点拆开。
