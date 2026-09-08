# AgentOps 全景做法

> 用途:本项目 **AgentOps(agent 运维)的完整做法**——7 大件,每件给「行业做法 + 你已有 + 要补」。全部经行业查证(来源附后)。
> 配套:`08 测评方案` · `09 兜底设计` · `测评方法_续聊交接包` · `编排测试集/`。
> 贯穿原则:**自托管 + 判官本地 + 走 OTel 不锁死 + 几十人规模按需上**。
> 日期 2026-06-24。

---

## 0. 生命周期 + 全景

**4 阶段闭环**:开发(Development)→ 测试(Testing,sandbox)→ 监控(Monitoring,session/trace/span)→ 反馈(Feedback,回流)→ 循环。

**7 件 × 你的覆盖 × 优先级**:

| 件 | 你的位置 | 优先级 |
|---|---|---|
| 1 评测 Continuous Evaluation | 🟢🟢 深 | 维持 |
| 2 观测 Observability | 🟢 设计 | **高(接 Langfuse)** |
| 3 反馈/回流 Feedback | 🟢 概念 | 中 |
| 4 治理 Governance | 🟢 判定逻辑强 | 补运行时层 |
| 5 优化 Optimization | 🟡 手动 | 中 |
| 6 成本 Cost | 🟡 引擎熔断有 | 中高 |
| 7 版本/发布 Versioning | 🟡 需求有 | **高(工具语义版本)** |

---

## 0.5 落地控制面(行业"具体怎么接",不是手搓)

**大实话:行业不手写成本/路由/版本这些,而是引入两个现成的"控制面"。**

### 控制面 A:LLM Gateway(网关)—— 成本/路由/缓存/熔断/打标/护栏全在这层

夹在「应用 ↔ 模型」之间,统一 OpenAI 兼容 API,**所有 LLM 调用都过它**。自托管 = **LiteLLM**(MIT)。
- **成本归因/打标**:每团队/用户/服务发一个 **virtual key**,网关按 key 记真实 spend;请求带 metadata(user/session/agent)。LiteLLM 设 `OTEL_EXPORTER` → **每请求吐一条 OTel span**(model/延迟/token/cost/key)。→ "请求创建时打标"由网关自动做。
- **预算熔断**:virtual key 配 budget 上限,**超额在计费前拦**(per team/user/key)。
- **模型路由**:配 fallback chain / 路由规则(主+备、按延迟错误切、按规则路由便宜模型),70/20/10。
- **语义缓存**:Portkey 自带(模糊匹配相似 prompt)。
- **限流 + 护栏**:per-key 限流;Portkey 网关层 PII 脱敏/越狱检测/审计。
- 选型:**LiteLLM**(自托管路由+预算,走 OTel)· Portkey(语义缓存+护栏+prompt 版本)· Helicone(成本归因 UI)。

### 控制面 B:Prompt Registry(注册表)—— 版本/灰度/回滚靠 label

prompt 存 registry、运行时按 label 拉。自托管 = **Langfuse Prompt Management**。
- **版本**:每改自动版本号;
- **灰度/部署**:用 **label**(production/staging/实验)指版本;运行时 `get_prompt("name")` 默认拉 production;SDK **缓存 60s**(stale-while-revalidate,保可用);
- **★回滚 = 重贴 label**:production label 重指旧版 → 运行中 agent **60s 内自动切回,不改代码、不重部署**。

### eval 门 + %灰度 + 工具版本
- **eval 门**:prompt/config 入 registry/git → PR 触发 **CI 跑 eval 套 → 掉基线 2% block merge**;
- **%灰度**:新版上 **5%→(自动门:错误率/延迟/工具模式/质量)→25%→100%**(网关/feature flag 切流量);
- **工具版本**:工具 schema/契约打 **语义版本 + 向后兼容**(你已有 output 契约 → 加版本号字段)。

### "事 → 在哪 → 怎么接"速查

| 要做的事 | 在哪层 | 具体怎么接 |
|---|---|---|
| 成本归因/打标 | LLM Gateway | virtual key + metadata,自动记 spend、吐 OTel span |
| 预算熔断 | LLM Gateway | virtual key 配 budget,计费前拦 |
| 模型路由 | LLM Gateway | fallback/路由规则,70/20/10 |
| 语义缓存 | LLM Gateway(Portkey) | 模糊匹配相似 prompt |
| 限流/PII/越狱 | LLM Gateway | per-key 限流 + 网关护栏 |
| prompt 版本/回滚 | Prompt Registry(Langfuse) | label 指版本,回滚=重贴 label,60s 生效 |
| eval 门 | CI | PR 跑 eval,掉 2% block |
| %灰度 | 网关/feature flag | 5%→25%→100% + 自动门 |
| 工具版本 | 注册表/契约 | 语义版本 + 向后兼容 |

### 你的自托管栈(落地形态)

```
应用 → LiteLLM 网关(成本/路由/缓存/熔断/打标/限流,走 OTel)→ 模型(本地 qwen/混元)
Langfuse(自托管):观测 trace + Prompt Registry(版本/回滚)+ badcase 回流
CI:engine 套 + model 套 当 eval 门(掉 2% block)
工具:你的注册表 + output 契约 → 加语义版本
```

> **一句话:成本/路由/缓存/熔断 = 接 LLM Gateway(LiteLLM);版本/回滚 = 接 Prompt Registry(Langfuse);质量门 = CI 跑 eval;工具稳定 = 语义版本。接两个现成控制面,不手搓。**

---

## 1. 评测 Continuous Evaluation

**行业做法**:
- **假模型立基线**(engine 套):假模型按脚本驱动真引擎,验引擎分支(确定性,CI 每提交全绿,**追分支覆盖非全样本**)。
- **出题**:RAG → RAGAS TestsetGenerator(文档建图谱→persona×类型→合成 问题+标准答案+片段);Agent → 工具集+目标 → 强模型出(问题+候选 plan)→ **假模型逐样本认证(跑+断言)**→ critic 筛 + 人审。
- **诊断栈(outcome 优先)**:outcome(DeepEval TaskCompletion)→ trajectory(agentevals,superset 别用 strict)→ tool(DeepEval ToolCorrectness)→ state(自写断言,控制/agent 优先)→ RAG(RAGAS 四件套)。
- 真模型多跑 3–5 次取平均,统计阈值;**判官本地 + ensemble + 人校**。

**你已有**:`test_engine.py`(16 绿)、`方法说明.md`、`cases.yaml`。
**要补**:Agent 出题骨架、model 套 runner、RAG 的 Q-A 评测集。

## 2. 观测 Observability

**行业做法**:按 **OpenTelemetry GenAI 语义约定**(`gen_ai.*` 的 agent/workflow/tool/model span)埋点一次 → 自托管平台;**每 step / 工具调用 / RAG 检索 = 一个 span,带 timing + success/error code + token + 成本**。埋一次可换后端,不锁死。

**你已有**:审计/消息日志 = trace 数据底座。
**要补**:按 OTel 吐出 → 接**自托管 Langfuse**。

## 3. 反馈 / 回流 Feedback

**行业做法**(最可信 gold 来源):Langfuse 捞 badcase(在线低分/差评/降级/告警)→ 归因(诊断栈)→ **补 gold/断言 + 脱敏 → 进回归集 → 每次改动跑回测**(① 修复验证 ② 防回归)。**生产回流 > 合成**(实验室 vs 生产差 ~37%)。

**你已有**:概念。
**要补**:回流管线;**给 badcase 补 gold 的人审流程**(最花人力但必须)。

## 4. 治理 Governance(你的强项)

**行业做法**:**RBAC**(工具可见性,按角色)+ **ABAC**(数据级,按 身份/部门/区域/时段 属性动态过滤)+ HITL 审批 + 最小权限 + **短时凭据/vault** + **PII 脱敏/最小化** + **运行时策略执行**(限流/kill switch/范围监控)+ **意图越界监控** + 审计可追溯。

**你已有(判定逻辑很强)**:读/控分叉 + 三道闸(RBAC + HITL)+ 提议-执行分离 + execute 永 deny + 不可逆必确认 + 审计 append-only + 越权=0 + 身份透传后端(**工具可见性=RBAC,数据级=ABAC**,两层都有)。
**要补**:运行时执行(网关限流/kill switch)、凭据 vault、PII 脱敏管线、意图越界监控。

## 5. 优化 Optimization

**行业做法**:生产 trace 找失败模式 → 改 prompt/重设计工具/防回归;**自动 prompt 优化**(失败轨迹当标注数据,DSPy 式);**A/B at scale**;**模型路由 + 缓存**(见成本)。

**你已有**:手动四旋钮(系统提示/工具描述/超域组织/grounding)+ badcase 回流(**手动闭环**)。
**要补**:自动 prompt 优化、A/B 实验、模型路由。

## 6. 成本 Cost Management

**行业做法**:
- **归因**:per-user / per-task / per-tenant;**★请求创建时打标签**(事后从日志补会漏报长 agentic trace)。
- **失控熔断**:对 token / 工具调用数 / 重试数 / span 深度 设天花板 + kill switch;**★放 proxy/网关层**(放 LLM 调用处太晚,token 已计费)。
- **优化**:**模型路由** nano/mid/frontier 按 70/20/10 → 省 **60–80%**;**prompt 缓存**(cached input 省 90%)+ 语义缓存。

**你已有**:`BudgetTracker`(引擎熔断:迭代/token/深度 + stall 守卫)——防"一次 run 内失控"。
**要补**:请求创建时打成本标签、per-user 日上限、模型路由、缓存扩展。
**具体怎么接(见 §0.5)**:这些**全在 LLM Gateway(LiteLLM)层**——virtual key 记 spend + 配 budget、fallback 路由、语义缓存、走 OTel 打标;引擎 `BudgetTracker` 仍管 run 内熔断,两层配合。

## 7. 版本/发布 Versioning & Deployment

**行业做法**:
- **版本清单 manifest**:agent 版本 + code SHA + prompt 版本 + model id + **tool 版本** = 单一真相源。
- **Config-as-Code**:单一配置文件,所有改动走 code review,**禁 UI/CLI 直改生产**。
- **eval 门**:prompt 入 registry,新版自动跑 golden 集,**掉超基线 2% 就 block merge**。
- **灰度 canary**:5% / 6h → 自动门(错误率/延迟/工具调用模式/质量)→ 25% / 24h → 100% / 48h → 标 stable;或蓝绿。
- **回滚**:把生产 tag 重指到 known-good 版本(**配置变更,不重部署**;旧版不可变归档)。
- **★工具版本 = 60% 生产 agent 失败源**:工具契约要**严格 API 契约 + 语义版本 + 向后兼容**。

**你已有**:CI 评测门(engine/model 套,掉 2% block)、**工具注册表 + output 契约**、`实施计划` 发版/回滚预案。
**要补**:prompts/configs 入 git(Config-as-Code)、**工具契约加语义版本(对上 60% 失败,高 ROI)**、灰度发布、版本 manifest。
**具体怎么接(见 §0.5)**:prompt 版本/回滚 = **Langfuse Prompt Registry 的 label**(回滚=重贴 label,60s 生效);灰度 = 网关/feature flag 切 5%→25%→100%;eval 门 = CI 跑你的两套;工具语义版本 = output 契约加版本号字段。

---

## 8. 落到你 · 优先级(性价比排序)

1. **接自托管 Langfuse**(走 OTel)——**一次补 观测 + 成本归因 + prompt 版本管理 三块**,最高 ROI。
2. **工具契约加语义版本**——对上"工具版本=60% 失败",且是你工具治理强项的延伸。
3. **Config-as-Code**(prompts/工具描述/配置入 git)——省力、收益大。
4. **Agent 出题骨架 + model 套 runner**——把评测从 engine 套扩到真 qwen。
5. **回流管线 + badcase 补 gold 流程**。
6. 中等:模型路由(省成本)、灰度发布、A/B。
7. 按需/规模:运行时网关(限流/kill switch)、凭据 vault、PII 脱敏、自动 prompt 优化、意图越界监控。

**最强可深讲(简历/面试)**:评测(假/真模型、RAGAS、DeepEval/agentevals)+ 治理判定逻辑(读控分叉/三道闸/越权=0)。
**诚实分层**:成本/版本/优化的"自动化"部分多为设计/规划,别说全做了。

---

## 来源

- 评测/出题:RAGAS 文档 · DeepEval 文档 · langchain-ai/agentevals · tau2-bench(arXiv 2506.07982)· APIGen-MT(2504.03601)· Anthropic《Demystifying evals for AI agents》。
- 观测:OpenTelemetry GenAI Semantic Conventions · Langfuse(langfuse/langfuse)· IBM AgentOps(建于 OTel)。
- 成本:[LLM Agent Cost Attribution 2026 — DigitalApplied] · [Track LLM costs 2026 — Braintrust] · [Cost Optimization with Routing — Requesty]。
- 版本/发布:[AI Agent Versioning & Rollback — BuildMVPFast] · [Version & Rollback Prompts — Arthur.ai] · [LLMOps CI/CD & Eval Gates]。
- AgentOps 学科:IBM《What is AgentOps》· ZBrain AgentOps Guide · 综述(LLMOps/AgentOps/MLOps Review)。
