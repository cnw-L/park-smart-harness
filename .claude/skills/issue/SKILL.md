---
name: issue
description: 把一句自然语言需求转换成可开发的 GitHub Issue。先读仓库（AGENTS.md、相关代码、现有测试），从代码事实推导 Goal/Constraints/Acceptance，再用 gh issue create 落成 Issue。适用触发：用户用自然语言提出新需求或改进；开始一项新工作前。边界：只产出 Issue，不写代码、不建分支。
---

# issue — 需求 → Issue

## 输入

用户的一句话目标 + 当前仓库。

## 方法（判断必须成立，顺序自主）

1. 读 AGENTS.md / README：项目是什么、怎么验证。
2. 定位相关模块：读现有实现与现有测试，搞清**当前真实行为**（写错 Current = 没读懂代码）。
3. 从代码事实推导 Goal / Current / Expected / Constraints / Likely affected / Acceptance。
4. `gh issue create --title ... --body ...`。

## Issue 正文格式（保持短）

```text
Title: 动词开头一句话
Goal: 用户视角的可观察结果
Current: 代码今天的真实行为
Expected: 目标行为
Constraints: 必须保持不变的现有行为 / 兼容性
Likely affected: 模块/接口清单（读完代码再写，不猜）
Acceptance: 每条都能被测试表达
```

## 纪律

- Acceptance 每条必须可验证；不能验证的移进 Constraints 或删掉。
- 不发明代码里没有依据的额外需求；发现的相邻问题另开 Issue。
- **升级判据**：范围触及公共 API/Contract、数据库 Schema、依赖/工具链、安全面
  → 打标签 `major` 并注明（implement 阶段必须拉对应专项 skill）。
- 拿不准是否 major → 按 major 标记（宁重勿漏）。
