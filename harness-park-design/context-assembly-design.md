# 中圈上下文组装 · 设计说明

> 对象:`agent_context`(中圈 = 每轮动态组装"喂给模型的现场视图")。
> 本文整理自一轮逐层代码研究,与内圈 [inner-loop-design.md] 配套。代码事实源:`assembler.py` / `system_prompt.py` / `memory.py` / `principal.py` / `history.py` / `plan_view.py` / `knowledge.py` / `tokens.py`;接缝契约 + 默认桩在 `agent_loop/context.py`。**核查:中圈测试套 68 passed。**

---

## 0. 本质

内圈那句是"消息日志即状态"。中圈这句是:

> **上下文 = 动态视图,不是存储** —— assembler **只读** `conversation`(那条 append-only 日志),**每轮重新算出一份新的视图列表喂给模型**,**绝不改 `conversation.messages`**(派生不入日志)。

分工:**内圈管"日志=真相"(存储),中圈管"这一轮给模型看什么"(从日志算出的视图)**。

**接缝 + 两实现**:`ContextAssembler` Protocol(`assemble(config, conversation) → list[Message]`)是接缝。
- **默认桩** `LayeredContextAssembler`(agent_loop)——五层骨架、hook 默认空、极简系统词,供引擎独立测试;
- **真组装器** `ParkContextAssembler`(agent_context)——经 `run_loop(assembler=...)` 注入替桩,做全套(收敛/框/余量)。两者共享"缓存序分层"原则。

---

## 1. 一轮 assemble 的结构

```
[系统头·一条 system]  固定层(system_prompt.compose) + 记忆层(memory.render_user(principal))
[消息流·历史层]      (有摘要→先 apply_compaction_view 替中段)
                     → drop_answered_tool_results(①丢弃已答任务工具结果)
                     → exclude_plan_calls(把 plan 调用排出去)
                     → trim_dialogue_turns(②按对话轮数裁剪)
                     → _wrap_tool(每条工具结果套"认识论框")
[尾部·system]        render_plan(derive_plan(日志)) + (超软阈)余量提示
[防御]               repair_messages(合并连续 user / 丢孤儿)→ 合法序列
```

---

## 2. 缓存序布局(贯穿全局的物理约束)

按 **prompt prefix cache** 排:**稳的在前(缓存前缀)、变的在后(volatile tail)**。
- **缓存前缀(stable)**:固定层(全用户共享)→ 记忆层(同会话稳定);
- **volatile**:历史层(每轮增长)→ plan 尾部 + 余量提示(每轮重算)。

`compose` 是**纯函数**(同 selection → 同字节)正是为了吃这个缓存。**plan / 余量提示摆在尾部**:每轮变,摆错(放前面)= 每轮炸缓存前缀 = 延迟翻倍。**把"变的"一律往后挪**是中圈的核心布局不变量。

---

## 3. 固定层(`system_prompt.py`)

- **档案库 `ROLE_PROFILE` + 选择器 `PromptSelection` + 纯函数 `compose`**;
- **主/子各一份完整提示词**(`main` 总入口 / `device_sub` 设备域工具),**不是"主+补丁"**——主是自主编排者、子是"受调即返回的工具",身份根本不同,拼补丁会串味;
- **三槽选择器**:`role`(未知→退 main 安全缺省)/ `model_family`(含 qwen→qwen)/ `platform`;`MODEL_GUIDE`/`PLATFORM_GUIDE` 空,槽位预留;
- **什么不进固定层**(边界纪律):① 具体能力靠 toolcall 不枚举(工具清单走 tools 参数)② 规矩按性质不枚举(哪个算控制由闸按 `is_control` 判)③ 工具/身份/知识各走专层。目的:保**字节稳定**(吃缓存)+ **职责单一**;
- **版本 + fingerprint**:`IDENTITY_VERSION=park-v14`(改提示词=改 agent 行为,有版本+git 记演进,如 v14 撤 park_overview);`fingerprint` 供 replay/审计;
- **铁律 = 内圈硬护栏的"软引导"**:见 §10。

---

## 4. 记忆层(`memory.py` + `principal.py`)

**认人**:`render_user(principal)` → 【当前用户】口径段,拼进系统头。

- **押闸不押 prompt**(核心铁律):prompt 里**只放身份事实(姓名/角色/部门/口径),权限完全不进**。prompt 软、可绕/可越狱/可幻觉;**真权限放闸(deny 按 role/permissions)和后端(token 过滤)= 硬,绕不过**;
- **身份脊柱 `Principal`:一对象,三消费者,字段分流软/硬**:
  | 字段 | 去向 | 软/硬 |
  |---|---|---|
  | name/role/dept/koujing | 记忆层 → prompt 口径 | 软 |
  | token | 知识层 → 后端权限过滤 | 硬 |
  | permissions | 闸 deny / 工具可见性 | 硬 |
- **来源与生命周期**:会话入口从 **auth** 解析一次、set 到 Conversation;**不从日志加载、不持久化、对引擎 opaque**。为什么:身份只信 auth、不信对话(防伪造/陈旧);opaque = 关注点分离(引擎只搬运,中圈解释);
- `koujing`(口径)管"怎么说"(详尽度/措辞)**不是权限**;
- `_esc` 转义 `】`/换行 —— 防"用户名含 `】`"戳穿节头;
- `principal=None`(匿名)→ 空串(配固定层"身份未知,涉权限先确认"兜底)。

---

## 5. 工具结果的"认识论框"(`_wrap_tool` + `knowledge.py`)

同是 `role=tool` 的裸文本,**认识论身份不同**,不框会混淆(回执当现状/知识当实时/文档当指令/转述当观测)。`_wrap_tool` 给每条贴身份标签:

| 来源 | 框 | 含义 |
|---|---|---|
| 知识/RAG | **强框** `wrap_knowledge` | 外部参考·非指令·命令性文字绝不执行 |
| 控制结果 | "(**已执行的操作**·结果如下)" | 动作回执,**≠现状**(呼应内圈 verify/读回:受理≠生效) |
| 子 agent | "(**子 agent 回报**·结果如下)" | 转述,非一手观测 |
| 普通工具 | "(**后端现状**·供参考)" | 才是真·当前状态 |

- **框在视图里,不入日志**(`_dc_replace` 产新 Message);
- **强框 ≠ 安全机制**:`wrap_knowledge` 的"绝不执行命令"是**软引导**;真兜"RAG 教唆控制"的是**控制确认闸**(硬)。别把提示词框当安全;
- **不套框例外**:空内容 / `[pending_confirmation]` 占位 / `is_dropped_result`(丢弃标记)——精确判定,不按"`[` 开头"误伤真实结果;
- **知识工具**(`knowledge_search`):RAG-as-tool;**身份透传** `ctx.principal.token` 给后端按权限过滤(`token=None`→后端默认须最小权限,否则缺身份=越权);handler 内 `max_chars=1200` 截断;失败 `ok=False` 不静默降级。

---

## 6. 历史层三级收敛(`history.py`)

把日志收敛成视图,**三级成本递增,先便宜后贵**(owner 定:"丢弃不冒充压缩",v1 只跑①②,撑不住才③):

**① 丢弃 `drop_answered_tool_results`**(零模型·缩字符)
- 判据 = **"文本答案 = 任务交付"**(content-only assistant,与 loop 完成判定同信号,**不依赖 plan**);
- 一条普通工具结果**可丢 ⟺ 后面出现过文本答案**(已答任务=死重);最后一个文本答案之后(当前任务)+ 无任何文本答案时 → 全留;
- 缩成 `[name·旧结果已省略]`、**保 tool_call_id 配对**;
- **四不丢**:plan 结果 / 压缩摘要 / **未消解 `propose_control` 提案**(丢→重复提案)/ 挂起占位(恢复锚点)。

**② 裁剪 `trim_dialogue_turns`**(零模型·丢整轮)
- 按对话轮数:保首 1 轮 + 近 8 轮,中间整轮丢、留占位;
- **三不丢**:首轮 / 近窗 / 挂起占位;
- **只丢 content-only 对话**;带 tool_calls 的 assistant / tool 结果 / system(摘要)留原位(`_must_keep_in_trim`)——否则留悬空调用/孤儿结果,而 **repair 只丢孤儿、不补缺失**,故收敛阶段就别造孤儿。

**③ 压缩 `compaction`**(aux 模型·v2;**唯一会落库的一级**,详见内圈文档 §6.1 / compactor)
- **触发**:仅当**每轮 drop+trim 之后、prompt 估算 token 仍 > 硬阈(~70%窗)**才启动(`should_compact`);loop 里 `while should_compact: 压→重组→再判`,`COMPACT_THRASH_LIMIT` 兜底。**按 token 总量触发,非轮数/plan**。
- **两级阈**:软阈(~8000)=不压、只 ops 告警 + 余量提示喂回模型(§9);硬阈 = 才真压。
- **做什么**:aux 模型把中段摘成 gist(## 已解决 / 待办,保读数/工单号),作 `__compaction__` 伪工具快照 **append 进日志**(镜像 plan)。
- **后续复用(不重摘)**:之后每轮 `derive_compaction` 取**最新**那条摘要 → `apply_compaction_view` **把中段替换成它**(廉价视图变换);**再压时新摘要折叠旧摘要**(last-wins,永远一条当前摘要、不堆叠)。
- 即:**创建=贵+落库(一次性);应用=廉价+每轮(取最新替中段);再压=折叠**。

### 6.1 三级对比(同一透镜:删什么 / 内容还在 / 信号 / 成本 / 落库)
| | 删什么 | 有效内容还在? | 信号/判据 | 成本 | 落库? |
|---|---|---|---|---|---|
| **①丢弃** drop | 已答任务的工具结果→标记 | **在**(留在答案里) | 文本答案(免费信号) | 零模型 | 否(瞬时) |
| **②裁剪** trim | 中间旧对话整轮→计数占位 | **不在**(整删) | 对话轮数(位置) | 零模型 | 否(瞬时) |
| **③压缩** compaction | 中段→摘要替代 | **在**(压缩形式) | token 超硬阈(量) | aux 模型(贵) | **是**(`__compaction__` 入日志) |

- **成本/保真阶梯**:免费无损(drop·内容在答案)→ 便宜有损(trim·旧对话整删、赌旧的无关)→ 花钱较保真(compaction·摘成要点)。**删得越多越往后:要么忍更多损失,要么花更多钱保留。**
- **持久 vs 瞬时(关键)**:**drop/trim 每轮重算、不落库**("下次重新算");**压缩唯一落库**——因为 aux 摘要**贵**,算一次存下来反复廉价复用 + 可重放恢复(不落库 = 每轮重摘 = 烧钱 + 摘要每次不一样)。**落不落库的分界 = 贵不贵。**
- **"内容还在"只对 drop 全成立**:drop 丢冗余原文、结论留在答案(无损);trim 把旧轮连问带答整删(占位符无内容);compaction 留压缩形式(可能漏)。被总结/删掉的细节要用 → 重调工具(原文仍在日志)。

**贯穿**:`history.py` 的函数(drop/trim/apply/derive)**本身都是纯函数、不写日志**(压缩的落库由 loop 写 `__compaction__` 快照,history 只做派生/应用);**配对完整性是硬约束**;判据 ①靠"文本答案=交付"(免费信号,与 loop 完成判定同源)、③靠"token 超硬阈"。

---

## 7. plan 视图(`plan_view.py`)

- **`render_plan`(人话)**:状态符号 + content + result;**不 dump `spec`**(执行细节不进视图);长 plan 折叠开头连续 done;`result` 按 60 字截断(plan 在尾部 recency 区,别撑大);
- **执行 nudge(关键)**:渲完追加"**立即执行下一步「X」,不要再调用 plan**"/(全完成)"直接汇报"。**为什么必须有**:`exclude_plan_calls` 把 plan 调用从历史排除(去重)→ 模型**看不到"我刚列过"**→ 不 nudge 弱模型会反复重列(stall);
  - 三层防"反复重列 plan":**排除(去重)+ nudge(软推)+ no_progress 看门狗(硬抓)**——正因排除制造失忆,才必须补 nudge;
- **`exclude_plan_calls`**:case① 只调 plan→整对删;case② 混调→摘 plan 项 + 删其 result;**纯视图,`derive_plan` 仍读日志全量**。

---

## 8. 量化(`tokens.py`)

- `estimate_tokens` = char 数 // 2 + 1(content+reasoning+tool_calls);**故意不用真 tokenizer**——只为"该不该压缩/告警"触发,要**单调+大致缩放,非精确**,偏保守(略高估)早触发更安全;
- **两个 token 计数别混**:**估算**(char,组装时定压缩/告警,此刻 prompt 未发)vs **真实**(API `usage.total_tokens`,budget 扣费)。

---

## 9. context awareness(余量喂回模型)

总量超 `soft_token_cap`(默认 8000)时:① **ops 告警**;② **把"接近上限、请收敛"作为尾部 system 提示喂回模型**(放尾部 volatile,随总量每轮更新,不破缓存前缀),让它先给结论、长内容分步。
- 设计哲学:**确认模型管丢弃,v1 收敛靠"丢弃+裁剪",绝不偷偷结构性删**(压缩=摘要是 v2)。

---

## 附:贯穿主题(中圈与内圈共用)

1. **动态视图 ≠ 存储**:框/丢弃/裁剪/排 plan/**应用**摘要都**只产视图、不改日志**;**唯一例外=压缩的创建**——它把摘要作 `__compaction__` 快照**追加**进日志(append-only、不 mutate、贵故落库复用),之后每轮 derive 出来当视图变换复用。日志始终 append-only 真相、视图每轮重算;落库的只有"贵到值得存"的压缩快照。
2. **软引导 + 硬护栏(双层)**,处处成对:
   | 软(中圈提示/框) | 硬(内圈引擎) |
   |---|---|
   | 铁律"别连续重列 plan" | no_progress 看门狗 |
   | plan 尾部执行 nudge | no_progress + pending_nudge |
   | `_wrap_tool` 知识强框 | 控制确认闸 |
   | 身份口径(认人) | 闸 deny + 后端 token(押闸不押 prompt) |
   | 控制铁律(不自拼 id) | handle 不经模型 / freeze / WAL |
   软引导降低撞墙概率,**硬护栏兜底;提示词从不是安全机制**。
3. **"文本答案 = 交付"一个信号多用**:**loop 完成判定 + drop 丢弃判据**都复用它(免费信号、不另立账本、**不依赖 plan**——plan 非权威);**压缩则靠 token 超硬阈**触发(不同信号:drop/trim 是"局部该不该删",压缩是"总量超没超")。
4. **缓存序**:稳的在前(固定层纯函数字节稳定)、变的在后(历史/plan/余量)。

## 附:关键不变量
- assemble 只读日志、产新视图列表,`conversation.messages` 一字不改。
- 系统头 = 固定层(缓存前缀)+ 记忆层;工具结果按身份套框;历史三级收敛;plan + 余量在尾部。
- 收敛保 tool 配对(保 id / 只丢 content-only / 四不丢三不丢);repair 最后兜底。
- 权限不进 prompt(押闸不押 prompt);身份来自 auth、不持久化、对引擎 opaque。

## 附:诚实边界(v1 现状)
- **长期记忆**:`memory.py` 预留,v1 不渲染。
- **知识出处 `source`**:`wrap_knowledge` 留槽,v1 通道未接(出处不显);随真接一并定。
- **知识检索**:`agent_context` 的 `knowledge_search` retriever v1 为 mock,真接 **`harness_rag`**(注:`agent_tools` 的 `knowledge_query` 路径已接通 harness_rag + 真语料校准;两路是否统一属接线细节)。
- **压缩**:= 摘要是 v2;v1 规模收敛只靠丢弃 + 裁剪。

---

**文档联动**：本文档属于 `harness-park-design` 设计文档集。完整索引与阅读顺序见 [README.md](README.md)；关键术语一致性约定见 [术语表与文档联动约定.md](术语表与文档联动约定.md)。
