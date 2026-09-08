# 智慧园区 AI 服务 · 测试与评测规范(Test & Evaluation Specification)

> 版本 **V1.1** · 2026-06-24 · 密级:内部 · 项目:smart_park_assistant(自研 Agent Harness)
> 本规范为活文档;权威靶子见附录,落地状态以代码库为准。
> **V1.1 变更(基于 2026 行业校准,详见《13 规范校准与优化》)**:① 样本量由"≥500 硬门槛"改为"按效应量 + 95% CI 反推";② judge 校准绑定 Cohen's kappa(地板 0.6)+ 错误 trace 100% 送 judge;③ 自动优化首选 GEPA(强证据);④ 补 τ²-bench-Verified / TAU3-Bench / Terminal-Bench / GAIA;⑤ ARES 标"信息不足、待核"。

---

## 1 引言

**1.1 目的**　定义本 AI 服务(Agent + RAG + 控制安全)的测试与评测体系:确定性测试与统计性评测如何分层、用何方法与工具、达到何种通过线、如何嵌入研发与运维全周期。目标是能力**可度量、可归因、可回归**,而非一次性人工抽查。

**1.2 范围**　覆盖:对话质量(意图/路由/编排/多轮)、知识检索(RAG)、控制安全红线、性能与可用性、在线评测与生产回流。不覆盖纯前端 UI、CMS、硬件与定位精度等非 AI 层(借鉴其"应有验收标准"思路,不在本规范设指标)。

**1.3 读者**　AI 工程、测试/QA、运维(SRE)、架构评审。

**1.4 约定**　"engine 套"=确定性引擎测试;"model 套"=真模型行为评测;"判官"=LLM-as-judge 评测模型。阈值标"参考"者为借鉴行业标准、按本项目实际定基线,非硬性承诺。

## 2 引用文件与术语

**2.1 引用**　ISO/IEC/IEEE 29119、IEEE 829(分层与文档借鉴)· 腾讯园区 V6《需求说明书》附录A(指标借鉴源)· OpenTelemetry GenAI 语义约定(在线评测埋点,见《可观测性设计规范》)。

**2.2 术语表**

| 术语 | 定义 |
|---|---|
| 假模型(ScriptedModel) | 按预设序列吐"模型决定"的复读机,顶替真模型使运行确定;**只喂决定、不喂结果** |
| gold / 参考轨迹 | 期望动作序列;候选 gold 须经假模型跑过认证(可达+正确)方算数 |
| 诊断栈 | outcome→trajectory→component 分层定位,**outcome 优先** |
| state-based 评测 | 断言后端最终状态(执行前后 diff),确定、无评分波动;控制类优先 |
| trajectory match | 比对工具调用序列;用 **superset**(含主干、允许多走)而非 strict |
| RAGAS 四件套 | Context Recall/Precision(检索面)+ Faithfulness/Answer Relevancy(生成面) |
| LLM-as-judge | 用模型评主观项;有偏差,须**本地化 + 人审校准(kappa)+ ensemble** |
| EDD | 评测驱动开发:评测嵌入研发运维全周期,非上线前补一次 |

## 3 测试总体策略

**3.1 三条铁律**
1. **离线先行,再上在线**:先建离线基线达标,最后才加在线/持续评测。
2. **评测驱动开发(EDD)**:每能力上线前先有测试集与通过线。
3. **用公认框架的公认指标,不自造**:RAG 用 RAGAS,Agent 用 tool correctness / task completion / trajectory,控制用 state-based。

**3.2 五条原则**　① 基准独立于被测(gold 来自文档/认证,不来自被测)② 先焊代码、再考模型(先假模型 engine 套,后真模型 model 套)③ outcome 优先的诊断栈 ④ 生产回流为主、合成为辅 ⑤ 判官不可靠 → 全本地 + 人校 + ensemble,数据不出域。

**3.3 两轴定位**　按"阶段(离线/在线)× 层级(组件/端到端/系统)":

| | 组件级 | 端到端 | 系统级 |
|---|---|---|---|
| 离线 | 意图/RAG/工具单测 | 编排/任务/轨迹/兜底 | 压测/并发/可用性 |
| 在线 | span 级在线评测(漂移) | 会话级在线/A·B/满意度 | 延迟/成本/漂移告警 |

## 4 测试分层(L0–L4)

| 层 | 对象 | 方法 |
|---|---|---|
| L0 单元/契约 | 每模块 + 工具输出契约 | pytest 断言 |
| L1 子系统 | 内圈循环/上下文/RAG/上下行 | 子系统达标测试 |
| L2 集成/端到端 | 跨 Agent 联动 + 语音↔大脑接缝(语音待落地后启用) | engine 套 + model 套 |
| L3 非功能 | 并发压测/安全攻击/降级 | 压测 + 故障注入 |
| L4 验收(UAT) | 试运营统计 | 在线 + 满意度 |

## 5 核心方法:假模型立基线 → 真模型 → 诊断栈

**5.1 假模型 engine 套(立可信基线)**　把"期望工具序列"写成剧本(list[ModelTurn])喂假模型,跑真引擎(真工具/Fake 后端/内存 store),验两件:① 代码能正确走完流程(可达性);② 闸/确认/降级/状态机走对(引擎规矩)。全绿即把该轨迹认证为可信基线(gold)。铁律:**只喂决定、不喂结果**——结果由引擎跑真工具产生,测的才是"接住决定去干活"。
> 现状:engine 套已实测 **16/16 绿**(完成判定/闸 allow·ask·deny/控制批准·拒绝·幂等/串并/全失败 reason/budget/中断)。

**5.2 真模型 model 套(统计)**　同一批场景真 qwen 跑,实际轨迹比对基线:trajectory match(superset)+ 最终状态 state-based + 任务完成 LLM-as-judge(判官本地);多跑 3–5 次取平均、按统计阈值。

**5.3 诊断栈(outcome 优先)**　outcome(任务完成,DeepEval)→ trajectory(agentevals)→ tool(DeepEval Tool Correctness)→ state(自写后端状态断言)→ RAG(RAGAS)。不一致 → engine 绿即代码无罪,锅在模型/设计 → 调四旋钮(系统提示/工具描述/超域组织/grounding),不动代码。

**5.4 认证 = 执行 + 断言**　候选 gold 须假模型按脚本跑(执行)+ 判"最终状态==目标"(断言)。**执行省不掉**:中间 handle/id 只有跑才知道、到没到目标只有跑完才能判。断言替代的是"存 gold 轨迹 + 逐步比对",**不是替代执行**。

## 6 评测维度与判定方法

**6.1 维度全景**

| 维度 | 测什么 | 方法/工具 | 参考阈值 |
|---|---|---|---|
| 意图/路由 | 选对工具+参数 | DeepEval Tool Correctness | 路由≥95% |
| 编排/规划 | 多工具串并条件、轨迹 | agentevals(superset) | 编排≥90% |
| 任务完成 | 是否真办成 | DeepEval Task Completion | 完成率≥75%(核心≥85%) |
| RAG 质量 | 检索+生成两面 | RAGAS 四件套 | 召回≥90%/幻觉≤5% |
| 控制安全(红线) | 越权=0、误操作=0、对账 | engine 套 state-based | 越权=0、安全幻觉≤0.1% |
| 多轮/上下文 | 10 轮上下文、指代 | DeepEval multi-turn | 10 轮≥90% |
| 兜底/降级 | 超时降级、不静默 | 故障注入 + 状态断言 | 降级 100%/切换≤3s |

**6.2 三种判定方法**

| 方法 | 适用 | 本项目用在 |
|---|---|---|
| 规则/确定性 | 字段透传、工具序列、参数 | 上下文传递率、工具序列 |
| state-based(后端状态 diff) | 有副作用/控制类 | 控制链、越权、降级(优先) |
| LLM-as-judge | 主观/语义:任务完成、忠实度 | 任务完成、RAG、回答质量 |
| 人工抽检 | 高风险/主观 | 安全关键、急救内容 |

> 约束:判官模型必须本地(混元/qwen),对话数据不出域。

## 7 工具链与判官

| 用途 | 选型(开源/自托管) | 理由 |
|---|---|---|
| 引擎单测 | 假模型 + pytest | 确定性,repo 现成件 |
| 语义评测 | DeepEval(Apache 2.0,本地判官) | pytest 式、Tool/Task/G-Eval、原生 CI |
| RAG 评测 | RAGAS(Apache 2.0,四件套 + KG 出题) | 检索/生成拆开、纯开源 |
| 轨迹评测 | agentevals(superset/unordered) | 现成 trajectory match |
| 红队/安全 | promptfoo(MIT,local-first) | 越权/注入对抗 |
| trace/在线 eval | Langfuse(自托管) | 等保友好、prompt 版本强 |
| 压测 | JMeter / k6 | 并发/延迟 |
| 判官模型 | 本地混元 / qwen | 数据不出域 |

> 排除纯 SaaS(LangSmith 云/Confident 云)做数据与判官——对话数据不外发。
> **ARES**(RAG 微调判官 + PPI 置信区间):2026 更新信息不足,**待核实后再纳入**。

## 8 数据集与样本量

- 数据集**版本化**;甲方提供集 + 自建集(多轮/编排/注入/越权/降级)。
- **样本量(V1.1 修正)**:不存在"≥500 硬门槛"。样本量应由**目标效应量 + 95% 置信度反推**:95%CI/80%power 下,分辨 ~7pp 差异约需 480 条/组、4pp≈1580、2pp≈6300。**500 仅为分辨 ~7pp 差异的下限**;评测结果须**报告 95% CI(±1.96·SE)**。注意 LLM eval 样本高度相关、非独立,**样本 <几百条时不应套用 CLT 构造 CI**。engine 套追求引擎分支全覆盖,不在样本量之列。
- **Agent 出题**(无 turnkey):强模型合成(问题+候选 plan)→ **假模型逐样本认证(跑+断言,APIGen 思路)**→ 筛 + 人审。
- **RAG 出题**:RAGAS TestsetGenerator(文档→知识图谱→Persona×题型→合成 问题+答案+参考片段)。

## 9 CI 门与 EDD 生命周期

| 套 | 模型 | 频率 | 通过线 |
|---|---|---|---|
| engine | 假模型 | 每次提交 | 100% 绿(红=代码 bug,阻断) |
| model | 真 qwen | nightly | 统计阈值(如 ≥90%),3+ 次取平均 + 报 CI |

生命周期:建离线基线 → CI 门(engine 每提交 + model nightly)→ 上线门(engine 全绿 + model 达线 + 安全集人审)→ 在线监控 → badcase 回流 → 补集 → 迭代。

## 10 在线评测与生产回流

- 全链路 trace(Langfuse 自托管),记录每 span 输入/输出/延迟/成本。
- **在线 evaluator**:100% 跑启发式;**5–15% 采样 + 错误/异常 trace 100%** 送本地 LLM-judge;judge 成本控在生产 LLM 成本 10–15% 内;embedding/分数漂移检测。
- **badcase 回流**:生产 trace 一键转回归用例(补 gold/断言/脱敏)→ 进编排测试集 → CI 重测;自建 trace→case 转换器。
- **判官校准(V1.1 强化)**:抽 100–300 条生产 trace、2–3 名标注者建 gold-set;跟 **Cohen's kappa**(>0.8 强 / **>0.6 可接受/地板** / <0.4 rubric 有歧义需重写);**月度跑、kappa 跌即告警、季度刷 gold-set**;否则在线数字不可信。

## 11 行业延伸(2026,已并入方法)

- **代理状态评测(proxy state-based,arXiv 2602.16246)**:LLM 从交互 trace 推断后端终态、不查后端 → 解控制评测"无读回端点"之困;论文自报人-LLM 一致 >90%、默认配置幻觉近零。**前沿、单一来源,需自验**;仅用于业务结果,安全红线仍走确定性 engine 套。
- **自动优化首选 GEPA(arXiv 2507.19457,ICLR 2026 Oral)**:反思式、读失败 trace 诊断、Pareto 前沿;**聚合 +13% vs MIPROv2 +5.6%、少用 35x rollouts**;`pip install gepa` / `dspy.GEPA` 本地可跑。用失败轨迹反哺。
- **RAG 两条腿**:RAGAS(输出侧)+ 入库抽取可观测(输入侧,RAGAS 看不见的语料质量盲区)。
- **学术对照物**:τ²-bench(dual-control/state-based)及其修正版 **τ²-bench-Verified**、**APIGen**(执行验证出题)、**TAU3-Bench**(长程多轮+模拟用户)、**Terminal-Bench**(出口码/文件 diff 确定性评分)、**GAIA**(真实多步助手)。**提醒:不同 benchmark 测不同维度,不应合并成单一排名。**

## 12 本项目落地基线(借鉴附录A)

借鉴腾讯 V6 附录A 相关指标当参考标尺,落到 harness 实际能力。纳入与 harness 相关约 20 条(对话/路由/编排/多轮 + RAG 召回/幻觉/拒答 + 控制安全红线 + 性能可用 + 工程基线);别人层不设指标。
建设序(杠杆×可自闭环):**M0** 安全红线 engine 套入 CI(零依赖,先)→ **M1** model 套 + RAGAS 出对话/RAG 质量(需 qwen,出题为大头)→ **M2** 监测出性能可用 → **M3** 压测/兜底。

## 13 角色与职责

| 角色 | 职责 |
|---|---|
| AI 工程 | 写 engine/model 套、出题、调四旋钮 |
| 测试/QA | 数据集版本化、CI 门、人审校准(kappa) |
| 运维(SRE) | 在线评测、漂移、回流(见《可观测性设计规范》) |
| 架构评审 | 上线门把关、红线判定 |

---

## 附录A 指标 × 测法对照(本项目纳入项)

| 指标 | 参考阈值 | 测法 | 优先级 |
|---|---|---|---|
| 子 Agent 路由准确率 | ≥95% | DeepEval Tool Correctness | P0 |
| 服务编排成功率 | ≥90% | agentevals(superset) | P1 |
| 多轮上下文理解 | ≥90%(10 轮) | DeepEval multi-turn | P1 |
| RAG 召回命中率 | ≥90% | RAGAS Context Recall | P0 |
| 整体幻觉率 | ≤5% | RAGAS Faithfulness | P0 |
| 越权动作率 | =0(红线) | engine 套 state-based | P0 |
| 安全关键幻觉率 | ≤0.1% | 白名单核验 + 人审 | P0 |
| 响应(简单/复杂) | 首Token≤2s/≤3s | 监测直方图(需部署) | P1 |
| 降级切换耗时 | ≤3s | 故障注入 | P1 |

## 附录B 参考文献

Anthropic《Demystifying evals for AI agents》· A Survey on Evaluation of LLM-based Agents(arXiv 2503.16416)· RAGAS(explodinggradients/ragas)· DeepEval(confident-ai/deepeval)· agentevals(langchain-ai/agentevals)· τ²-bench(arXiv 2506.07982)+ τ²-bench-Verified · APIGen(arXiv 2406.18518)· Proxy State-Based Eval(arXiv 2602.16246)· GEPA(arXiv 2507.19457)· 样本量统计功效与 CLT 警告(arXiv 2503.01747)· TAU3-Bench / Terminal-Bench / GAIA。

## 变更记录

| 版本 | 日期 | 作者 | 变更 |
|---|---|---|---|
| V1.0 | 2026-06-24 | AI 工程 | 首版:统一测评方法论 + 行业对齐 + 本项目落地基线 |
| **V1.1** | 2026-06-24 | AI 工程 | 行业校准:样本量按效应量+CI 反推;judge 绑 kappa+错误 trace 100%;GEPA 首选;补 τ²-Verified/TAU3/Terminal-Bench/GAIA;ARES 待核 |
