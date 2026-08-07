# 智慧园区 AI 服务 · 可观测性(监测)设计规范(Observability Design Specification)

> 版本 **V1.1** · 2026-06-24 · 密级:内部 · 项目:smart_park_assistant(自研 Agent Harness)
> 与《AI 服务测试与评测规范》在线评测章节互为配套。
> **V1.1 变更(基于 2026 行业校准,详见《13 规范校准与优化》)**:① 平台开销"12–15%"软化为深度相关;② 栈补 **trace 存储后端 Grafana Tempo**,并评估 SigNoz/ClickStack;③ vLLM 自动埋点首选 **OpenLLMetry**;④ spanmetrics 派生 RED 须采样前从 100% 流量派生;⑤ OTel GenAI 约定已拆独立仓库 + v1.37 消息记录重构;⑥ SLO 补 multi-window burn-rate 三档;⑦ PII"源头+Collector 双层";⑧ 补 MCP tracing / OTel Weaver。

---

## 1 引言

**1.1 目的**　定义本 AI 服务的可观测性体系:用何标准件、如何埋点、监测哪些指标、如何设 SLO 与告警、如何保障数据安全与可扩展。目标是把延迟、成本、错误、质量、漂移变成**可见、可告警、可回流**的信号,而非事后凭日志排查。

**1.2 范围**　覆盖 harness(内圈/中圈/工具治理)、RAG、控制链、语音外壳的 traces/metrics/logs 三支柱 + 在线评测/漂移/回流。聚焦监测层标准件与架构,不含业务功能设计。

**1.3 现状**　当前仅有审计(PgAuditLog,合规留痕)与零散日志,**无真正监测**(无 trace/metrics/dashboard)。监测层为新建(greenfield),本规范为其设计基线。

## 2 引用文件与术语

**2.1 引用**　OpenTelemetry 规范与 GenAI 语义约定(CNCF,**已拆独立仓库** `open-telemetry/semantic-conventions-genai`)· OTel Collector 部署模式 · 《AI 服务测试与评测规范》· 腾讯园区 V6 附录A(性能/可用性借鉴源)。

**2.2 术语表**

| 术语 | 定义 |
|---|---|
| OTel | CNCF 厂商中立可观测标准:埋点一次、换后端不改码 |
| OTLP | OTel 线协议(gRPC 4317 / HTTP 4318);后端收 OTLP 即可对接 |
| 三支柱 | traces / metrics / logs;缺一不算完整可观测 |
| span | 一次操作的追踪单元;带属性、时长、父子关系 |
| Collector | OTel 聚合/采样/路由/脱敏中枢;agent(近应用)与 gateway(中心)两种部署 |
| SLO / burn-rate | 服务等级目标 / 错误预算消耗速率;告警绑 burn-rate 而非裸阈值 |
| quality-aware 告警 | 对在线评测分/漂移告警,抓 APM 看不见的"静默质量失败" |

## 3 设计原则

1. **标配优先 + 标准接口**:监测组件一律业界标准件,组件间只用标准协议(OTLP/PromQL)解耦;**绝不写私有/非标监测路径**(唯一会设天花板、retrofit 贵的错)。
2. **完整三支柱**:traces + metrics + logs 缺一不可。
3. **为规模设计、按当下供给**:拓扑按完整标准搭(Collector 可演进到 gateway+HA);几十人先最小供给,上规模只加容量、不改设计。
4. **等保**:全栈自托管、数据不出域、判官本地;监测数据含对话(PII)→ 监测本身也是治理对象。
5. **复用已有接缝**:harness 边界(audited_store)与 Protocol 接缝即 span/metric 落点;审计与监测互补,各走各 sink。

## 4 总体架构

**4.1 三层 × 三支柱**

| 层 | Traces | Metrics | Logs | 标准件 |
|---|---|---|---|---|
| ③ 质量评测 | span 挂在线 eval 分 | 在线 faithfulness/完成/漂移 | badcase 详情 | Langfuse + DeepEval/RAGAS(本地判官) |
| ② LLM 遥测 | model/tool/RAG span(gen_ai.*) | TTFT/TPOT/token/成本/工具成功率 | 模型 I/O(脱敏) | OTel + OpenLLMetry → Langfuse |
| ① 基础设施 | 服务调用 span | RED + USE + GPU 占用 | 系统日志 | OTel → Prometheus/Grafana + **Tempo**(trace 存储)+ Loki |

**4.2 标准拓扑(Collector 居中,可演进)**

```
应用(OpenLLMetry 自动埋 LLM + 手埋 harness 自定义 span)
   │  OTLP
   ▼
[OTel Collector]  ← 适配中枢:换后端/采样/脱敏/路由全在此
   ├─▶ Langfuse              (LLM trace + 在线 eval + prompt 版本 + 成本)
   ├─▶ Tempo                 (trace 存储,大规模 trace 后端)
   ├─▶ Prometheus            (metrics)─▶ Grafana(看板 + Alertmanager 告警)
   └─▶ Loki                  (logs)
```
> **★ 关键:用 `spanmetrics` connector 派生 RED 指标,必须在采样前从 100% 流量派生**(forward connector 分两步),否则指标只反映被采样子集、失真。

**4.3 演进路径**　现在(几十人):应用直连 Langfuse 或单 Collector;后端单机自托管。上规模:Collector 转 agent(sidecar/daemonset)→ gateway(中心聚合)两层,gateway ≥2 实例 + LB(去单点);需采样时 **tail-sampling 仅在 gateway**(`loadbalancingexporter` 按 `routing_key:traceID` 一致性路由,确保同 trace 所有 span 到同实例)。此步不改应用、不改埋点。
> **可评估的统一替代**:**SigNoz / ClickStack**(单 ClickHouse 存储 + SQL,免 PromQL/LogQL/TraceQL 三套查询语言)——几十人自托管可评估以降运维(LGTM 维护约占平台工程 20–30% 时间)。

## 5 埋点规范

**5.1 LLM 调用 → 自动埋点**　用 **OpenLLMetry**(Traceloop,Apache 2.0,原生 emit `gen_ai.*`、显式支持 vLLM)包 qwen 的 OpenAI 兼容调用,每次自动出 `gen_ai.*` span(含 input/output_tokens、模型、延迟)。不手写 model span。(注:vLLM 暴露 OpenAI 兼容端点,靠 OpenAI client 自动埋点拦截。OpenInference 是 `gen_ai.*` 的 superset,若严格要 gen_ai.* 用 OpenLLMetry 更直。)

**5.2 harness 自定义边界 → 手埋 span**

| span | 落点(代码) | 关键属性 |
|---|---|---|
| 会话/agent(根) | run_loop 入口 / audited_store 边界 | session.id=thread_id、agent.name、principal(脱敏) |
| iteration | loop while 每轮 | 轮序、budget 余量、是否压缩 |
| tool 执行 | dispatch.execute_one | gen_ai.tool.name、disposition(allow/ask/deny)、ok/error、超时/重试 |
| gate 决策 | CatalogGate.classify | allow/ask/deny、capability、是否越权 |
| RAG 检索 | retrieve_evidence | 召回条数、best_rerank_score、是否二轮、insufficient |
| 控制 | propose / execute | grounding 通过/拒、是否真生效(读回)、幂等命中 |

**5.3 命名约定**　LLM:OTel GenAI 语义约定 `gen_ai.*`——**仍 experimental、未冻结**;约定已拆到独立仓库 `open-telemetry/semantic-conventions-genai`(主仓 `model/gen-ai`/`openai`/`mcp` 废弃,**CI 引用指新仓**);**v1.37 起消息记录重构**(`gen_ai.input.messages`/`output.messages`/`system_instructions` 属性);**钉 `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`**。服务指标:RED(Rate/Errors/Duration)+ USE(资源)。自定义维度带分区键(tenant/thread),为多租户/分片预留。

## 6 指标体系与 SLO

**6.1 指标四类(映射附录A)**

| 类 | 具体指标 | 标准件 | 参考阈值(借鉴附录A) |
|---|---|---|---|
| 延迟 | TTFT / TPOT / 端到端 / Goodput | Prometheus 直方图 | 简单首Token≤2s/完整≤5s;复杂≤3s/≤10s |
| 用量/成本 | token(in/out)/ 请求数 / 每会话成本 | OTel + Langfuse | 成本归因(网关侧) |
| 错误/可用 | 错误率 / 超时率 / 降级率 / 可用性 | Prometheus + RED | 月度≥99.9%;降级切换≤3s |
| 质量/安全 | 在线 faithfulness/完成/漂移/越权次数 | Langfuse 在线 eval(本地) | 幻觉≤5%/越权=0/安全幻觉≤0.1% |
| 资源(GPU) | GPU 占用 / 并发分档 | Prometheus + DCGM exporter | 并发 500/2000/5000 分档 |

> GPU 路径并发上限远低于纯文本 → 单独记 GPU 占用、并发分档诚实标,不混报一个并发数。
> **指标定义(V1.1)**:TTFT=请求到首 token;TPOT=(端到端−TTFT)/(out−1);Goodput=满足 SLO 的成功吞吐。**阈值无通用标准、按业务 SLO 定;vLLM 默认 SLA TTFT 3000ms/TPOT 100ms 仅作基线。**

**6.2 SLO 定义 + 告警绑定**　可用性 SLO:月度 ≥99.9%(错误预算约 43 分钟/月)· 延迟 SLO:简单 TTFT p95 ≤2s、复杂 ≤3s · 安全 SLO(硬):越权 = 0。
> **multi-window multi-burn-rate(Google SRE 标准,30 天预算)**:**1h 窗口 14.4×→页面**、**6h 窗口 6×→页面/工单**、**3d 窗口 1×→工单**。多窗口避免漏掉低速但显著的劣化。

## 7 告警

- 告警绑 **SLO burn-rate(非裸阈值)**→ 降噪、抓持续劣化;告警带上下文(受影响 feature/模型版本/最近变更),发企微/Slack。
- **quality-aware 告警**(APM 抓不到的静默失败):在线 eval 分跌破阈值 / 漂移 / 越权≠0 / 降级率骤升 → 告警。

## 8 在线评测、漂移与生产回流

- **采样**:100% 跑启发式(规则)+ **5–15% 采样 + 错误/异常 trace 100%** 跑本地 LLM-judge。
- **漂移**:prompt/模型/用户行为变 → embedding 漂移 + 在线分分布漂移。
- **回流**:生产 trace 一键转回归用例(补 gold/断言/脱敏)→ 进编排测试集 → CI 重测;自建 trace→case 转换器。
- **判官校准**:在线分须地板 5–10% 人审抽检,**绑 Cohen's kappa(地板 0.6)**、持续跟一致率、kappa 跌即告警,否则在线数字不可信(详见《测评规范》§10)。

## 9 安全与等保

- **全栈自托管**:Langfuse/Prometheus/Grafana/Tempo/Loki/Collector 全部 VPC 内,对话数据不出域;判官本地 qwen。
- **PII 脱敏(V1.1 分层)**:**双管齐下**——① 源头(instrumentation 层)不记录敏感内容(官方最佳实践:尽早过滤);② Collector processor 层兜底(`redactionprocessor` / `transformprocessor` OTTL / `attributesprocessor`),**须在 routing/export 前**,一处治理跨所有后端生效。
- **保留期 + 访问控制**:trace/日志设保留窗口 + 角色化访问(**监测台也要 RBAC**);日志保留参考 ≥180 天。
- **审计 vs 监测**:PgAuditLog(合规留痕、写边界、模型不可写)与 OTel trace(可观测)互补;**别用 trace 替审计**(trace 可采样/会过期,审计要完整不可篡改)。
- **监测是治理对象**:Collector/Langfuse 接入同样 deny-first,别当可信内部。

## 10 扩展性(为规模设计,无天花板)

唯一会撞墙的:写了**非 OTLP 的私有监测路径**。只要全程 OTLP + 标准件,扩容 = 加机器 + 改 Collector 配置。

| 维度 | 现在(几十人) | 上规模 | 改设计? |
|---|---|---|---|
| Collector | 单实例/直连 | agent→gateway 两层 + LB + ≥2 HA | 否,只加容量 |
| 采样 | 全量 | gateway tail-sampling(按 trace_id)| 否,配置项 |
| 存储 | 单机 | Prometheus→Mimir/Thanos、Tempo/Loki 分片、Langfuse 多副本 | 否,标准件横扩 |
| 上层接入 | — | 吐 OTLP + Prometheus 远程写 | 否,标准协议 |

## 11 落地分期

| 期 | 做什么 | 依赖 | 产出 |
|---|---|---|---|
| M0 | OTel SDK + OpenLLMetry + harness 手埋 span;ConsoleExporter 本地验证 | 零(纯库) | span 树本地可见 |
| M1 | 自托管 Langfuse(traces+在线eval)+ Prometheus/Grafana/Tempo(RED+TTFT 看板) | 部署后端 | 延迟/成本/trace + 看板 |
| M2 | Loki(logs)+ 告警(burn-rate + quality-aware)+ badcase 回流转换器 | M1 | 告警 + 回流闭环 |
| M3 | Collector agent→gateway + tail-sampling + HA(规模到了再上) | 负载增长 | 高可用监测 |

## 12 选型总表

| 角色 | 标准件(自托管/本地) | 备注 |
|---|---|---|
| 埋点标准 | OpenTelemetry(SDK + GenAI semconv,钉版本) | OTLP 事实协议 |
| LLM 自动埋点 | **OpenLLMetry**(原生 gen_ai.*、含 vLLM);OpenInference 备选 | 免手写 model span |
| 适配中枢 | OTel Collector | 换后端/采样/脱敏/路由 |
| LLM trace + 在线 eval | Langfuse(自托管,可选 v4 OTel-native SDK) | prompt 版本/成本/在线 eval 最强 |
| trace 存储 | **Grafana Tempo**(或 SigNoz/ClickStack 统一替代) | 补齐三支柱的 trace 后端 |
| 指标 + 看板 + 告警 | Prometheus + Grafana + Alertmanager | RED/USE/SLO 标准 |
| 日志 | Loki / OpenSearch | 结构化日志 |
| 判官模型 | 本地混元 / qwen | 数据不出域 |

## 13 角色与职责

| 角色 | 职责 |
|---|---|
| AI 工程 | 埋点(自动+自定义 span)、在线 eval 接入 |
| 运维(SRE) | 部署后端、SLO/告警、漂移、回流转换器 |
| 安全/合规 | PII 脱敏策略(源头+Collector)、保留期、监测台 RBAC |
| 架构评审 | 标准件/标准接口把关、无天花板审查 |

---

## 附录A 诚实标注

- OTel GenAI agent 语义约定**未冻结**(钉版本、预期小变;已拆独立仓库)。
- 平台开销**与埋点深度强相关**,深度 step-level 典型 ~15%(单一基准、场景依赖,异步/批量导出可显著降)——**非普适常数**。
- tail-sampling 有复杂度(gateway 需见全 trace),规模没到别提前上;spanmetrics 须采样前派生。
- OTel 只给 trace,不算 eval 分;质量层仍靠 DeepEval/RAGAS 判官(本地)。
- SigNoz/ClickStack 降运维比例为单一来源,宜自核。

## 附录B 参考文献

OpenTelemetry GenAI Semantic Conventions(独立仓库)· OTel Collector Architecture / Gateway / tail-sampling / spanmetrics · Google SRE《Alerting on SLOs》· Langfuse(自托管)· OpenLLMetry(Traceloop)/ OpenInference(Arize)· Grafana Tempo / SigNoz / ClickStack · OTel《Handling Sensitive Data》· DCGM exporter · OTel AI Agent Observability(MCP tracing / OTel Weaver)。

## 变更记录

| 版本 | 日期 | 作者 | 变更 |
|---|---|---|---|
| V1.0 | 2026-06-24 | AI 工程 / SRE | 首版:三支柱标配栈 + OTel 埋点 + SLO/告警 + 等保 + 扩展性 + 分期 |
| **V1.1** | 2026-06-24 | AI 工程 / SRE | 行业校准:补 Tempo;OpenLLMetry 首选;spanmetrics 采样前派生;GenAI 拆仓+v1.37;burn-rate 三档;PII 双层;开销软化;补 MCP tracing/OTel Weaver/SigNoz |
