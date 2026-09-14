# OpenAvatarChat 项目全解(源码级,v0.6.0)

> 目标:把 OAC 从启动到每一站读透,作为园区数字人落地的参照实现。所有结论带 `文件:行号`。
> 配套:[研究主线.md](研究主线.md)(理论×代码核对)、[园区数字人落地方案.md](园区数字人落地方案.md)(施工图)。
> 读透日期 2026-06-17。

---

## 0. 一句话定位

OAC = **一个配置驱动的、handler 可插拔的实时多模态对话引擎**。它本身不"绑定"任何模型,而是用一套 **Handler / Stream / Signal 三件套** 把 VAD/ASR/LLM/TTS/Avatar/Client 串成数据流管线。换模型=改 YAML 的 `module` 字段;砍模块=删 YAML 块。

---

## 1. 启动链(demo.py → engine → handler 加载)

```
demo.py:main()
  → load_configs(args)              # 读 config/xxx.yaml → logger/service/engine 三份配置
  → ChatEngine().initialize(engine_config, app, ui)   # chat_engine.py:39
       → handler_manager.initialize()   # 按 config 动态加载 handler 类(见§2)
       → handler_manager.load_handlers()  # 逐个 .load() 加载模型;client/manager handler 注册 FastAPI 路由
  → uvicorn 跑 FastAPI(+Gradio /gradio)   # demo.py:96
```
- 默认 config:`chat_with_openai_compatible_bailian_cosyvoice.yaml`(demo.py:27)。
- 版本常量 `OPEN_AVATAR_CHAT_VERSION="0.6.0"`(chat_engine.py:22)。
- patch 了 `torch.load(weights_only=False)`(demo.py:33)——加载老模型权重的兼容 hack。

---

## 2. 配置即架构:动态加载机制(文档 §8.2 实证)

`handler_manager.py:38-58`:
```
config.handler_configs[name] = {module: "asr/sensevoice/asr_handler_sensevoice", ...其余=参数}
  → HandlerBaseConfigModel.model_validate(raw)   # Pydantic 解析,enabled? module?
  → import_class(module, HandlerBase, search_path)  # 在 src/handlers 下按路径找 HandlerBase 子类
  → handler_class() 实例化 → register_handler
```
- `handler_search_path: ["src/handlers"]`(config)。
- `load_priority` 决定加载顺序(`get_enabled_handler_registries` 按它排序)。
- **这就是"插线板"**:YAML 的 `module` = 插哪个牌子,其余字段 = 旋钮参数。换 ASR = 改 `module: asr/sensevoice/...` → `asr/bailian_asr/...`。

---

## 3. 三大核心抽象(整个引擎就这三件套)

### ① Handler(模块)— 统一契约 `common/handler_base.py`
每个模块实现:
| 方法 | 时机 | 作用 |
|------|------|------|
| `get_handler_info` | 注册 | 声明 name/config_model/load_priority |
| `load` | 启动一次 | 加载模型 |
| `create_context` | 每会话 | 建 per-session 状态(cache 等) |
| `get_handler_detail` | 每会话 | **声明:吃什么类型(inputs)/产什么类型(outputs)/听什么信号(signal_filters)** |
| `handle` | 每条数据 | pump 线程逐条调,处理 + 提交输出 |
| `on_signal` | 收到信号 | 响应 INTERRUPT/STREAM_CANCEL/SEMANTIC_WAIT 等 |
| `on_history_record`/`should_auto_record_history` | 自动 | 历史记录钩子 |

### ② Stream(数据流)— `core/stream_manager.py`
- 每个 handler 的输出 = 一条 ChatStream(有 builder_id/stream_id = `stream_key`)。
- 流构成**生产依赖图**:`LLM流→TTS流→AVATAR_AUDIO流→CLIENT_PLAYBACK流`(`source_streams`/`ancestor_streams` 指上游,`ref_by` 记下游)。
- 生命周期信号:STREAM_BEGIN/END/CANCEL。`recycle_ttl=10s` 留时间给下游建依赖。

### ③ Signal(控制)— `core/signal_manager.py`
- 一个独立线程,把信号按 `(type, source_type, stream_type)` 过滤分发给注册的 listener。
- 与数据流**物理分离**(不同队列、不同线程)= 文档 §5.2"控制走独立通道"的引擎级实现。

---

## 4. 运行时模型:pump 线程 + 数据类型路由

`core/chat_session.py`:
- **每个 handler = 一个独立线程**(`:342` `handler_pumper`):`input_queue.get` → `handle()` → `submit` 输出。
- **handler 靠数据类型连接**:handler 声明吃 `HUMAN_TEXT` → 注册成该类型的 `DataSink`;某 handler 产 `HUMAN_TEXT` → streamer → 路由到所有吃这个类型的 sink。**这是插线板的"孔对孔"。**
- ⚠️ **没有中央状态机**(无 IDLE/LISTENING/THINKING/SPEAKING)。"状态"涌现于"哪些 handler 队列此刻有数据"。
- **两层 cancel 拦截防污染**:生产侧 `stream_data` 挡已取消流;消费侧 pump `:83-88` 处理前查流状态,CANCELLED 就跳过。
- **异常隔离**:`handle()` 包 try/except(`:131`),单 handler 崩不拖垮线程。
- **自动历史**:STREAM_BEGIN/END 自动记 session_history,流式文本按 chunk 累积(`:90-169`)= 多轮记忆。

---

## 5. 完整 pipeline 逐站(以 chat_with_openai_compatible 为例)

数据流(数据类型在箭头上):
```
浏览器 ─MIC_AUDIO→ [Client] ─MIC_AUDIO→ [SileroVAD] ─HUMAN_AUDIO(is_last=speech_end)→ [SenseVoice]
  ─HUMAN_TEXT→ [LLM] ─AVATAR_TEXT(流式token)→ [CosyVoice TTS] ─AVATAR_AUDIO(流式块)→ [Client] ─→ 浏览器播放
信号侧:SmartTurnEOU/SemanticTurnDetector/InterruptHandler 旁路监听 + 发 INTERRUPT/SEMANTIC_WAIT/candidate STREAM_END
```

| 站 | handler | 吃 → 产 | 关键机制 |
|----|---------|---------|---------|
| 传输 | `client/ws_client` 或 `rtc_client` | 收发所有类型 | 单 WS,每通道独立队列+独立发送协程(信号不被音频堵);前端 noiseSuppression=off/AEC=on |
| 切句 | `vad/silerovad`(基础)/`duplex_vad`(双工) | MIC_AUDIO→HUMAN_AUDIO | 4状态机 PRE_START→START→POST_END→END;**POST_END 重连**先发出去错了再 cancel(防腰斩);START 时带 padding+look-back 防丢头字 |
| 识别 | `asr/sensevoice`(=fun-asr) | HUMAN_AUDIO→HUMAN_TEXT | **只整句 SenseVoice,无 partial**;speech_end(is_last_data)触发;剥 `<\|...\|>`;空结果拦截 |
| 轮次(声学) | `vad/smart_turn_eou` | 旁路 HUMAN_AUDIO | smart-turn onnx 取末 8s 判"说完没"→ candidate STREAM_END |
| 轮次/打断(语义) | `llm/semantic_turn_detector` | HUMAN_DUPLEX_TEXT/AUDIO | LLM 判完成/打断/意图;停止词表 fast path;附和词过滤;发 SEMANTIC_WAIT/INTERRUPT |
| 大脑 | `llm/openai_compatible` | HUMAN_TEXT→AVATAR_TEXT | OpenAI 流式;ChatHistory 多轮;**协作式 cancel**(见§6);空查询兜底 |
| 合成 | `tts/cosyvoice` | AVATAR_TEXT→AVATAR_AUDIO | **独立子进程**(torch.multiprocessing);内联正则切句;`filter_text` 白名单清洗;子进程→队列→per-session task 顺序提交 |
| 打断执行 | `logic/interrupt` | 只听 INTERRUPT 信号 | cancel_stream_chain / cancel_streams_by_type(CLIENT_PLAYBACK) |

---

## 6. 打断的端到端真相(最值得学的一块)

**触发→决策→执行→通知 四段,决策与执行解耦:**
```
触发: 前端点击/VAD → Client 发 INTERRUPT 信号(CLIENT)
      或 SemanticTurnDetector 判定 → emit INTERRUPT(HANDLER)
决策: 这两者只"决定要不要打断",不碰流
执行: InterruptHandler.on_signal → StreamManager.cancel_streams_by_type(CLIENT_PLAYBACK)
      → 沿依赖图向上 cancel 祖先(AVATAR_AUDIO/TTS/LLM)+ 向下 forward 到 ref_by
通知: 每个流发 STREAM_CANCEL → ws 的 _ws_signal_output_task 捕获 → InterruptNotification 给前端停播
      + _cancelled_stream_keys 拦截已排期未播的块
```

⚠️⚠️ **关键纠正(对你落地最重要)**:文档 §5.2 说"LLM/TTS 必须是可取消异步 task"。OAC 的真相是**两层**:
1. **引擎级**:不写 `task.cancel()`,而是 cancel 流 → 依赖图级联标记 CANCELLED。
2. **handler 级是协作式**:长跑 handler 自己要在循环里查"我被取消了吗"。
   - LLM(`:168-174`):流式循环每个 chunk 查 `stream_key in active_stream_keys`,不在就 `completion.close(); break`。on_signal 收 STREAM_CANCEL 时把 key 移除。被打断的轮**不写 history**(`:182`)。
   - TTS:**没有真正中断子进程合成**,靠下游 ws 丢弃 CANCELLED 流的音频。即"停止输出"而非"停止合成"。

> 启示:你做打断,LLM 那段必须能协作式中止(流式循环里查标志位 + 关连接);TTS 至少要能"丢弃输出",能停子进程更好。

---

## 7. 配置变体(config/ 的 13 个 yaml = OAC 能怎么搭)

命名规律 `chat_with_{LLM}_{TTS}_{Avatar}_{duplex?}`:
- `_duplex` = 用 DuplexVAD(always-on)+ SemanticTurnDetector,真双工打断;无 `_duplex` = 半双工(VAD 播放期自关)。
- `_musetalk`/`_lam`/`flashhead` = 不同形象;无形象后缀 = 纯语音(用 LiteAvatar 或 without_avatar)。
- `bailian` = 云端(百炼 ASR/TTS);否则本地模型。
- → **你要的"纯语音"= 选无形象 + 本地模型那一支**;要打断就参照 `_duplex` 变体的 handler 组合。

---

## 8. 对之前结论的两处纠正

1. ⚠️ **OAC 不是完全没有文本清洗**:cosyvoice handler `filter_text:199` 有白名单清洗(删 markdown 符号/emoji/特殊字符)。但**粗暴**:不做数字单位读化(`100%`→`100`,丢了"百分之"),不感知 markdown 语义。→ 你仍需更完善的清洗,但"❌完全没有"改为"⚠️有但粗暴"。
2. ⚠️ **cosyvoice 路径的句子聚合是内联正则**(`tts_handler:218` re.split 标点),不是 `token_buffer.py`。token_buffer.py 是更完善的独立工具(CJK/拉丁分治+字数兜底),但当前 cosyvoice handler 没用它,用了更简单的内联版。→ 你可直接用更好的 token_buffer.py。

---

## 9. 关键设计决策清单(及对纯语音落地的取舍)

| OAC 设计 | 评价 | 你纯语音落地 |
|----------|------|------------|
| dataflow 无中央 FSM | 扩展强但状态涌现难调试 | 起步用显式 FSM 更可控 |
| 单 WS 每通道队列双工 | ✅ 优雅,纯 WS 可双工 | 直接抄 |
| 决策/执行解耦(InterruptHandler) | ✅ 干净 | 抄思路 |
| 协作式 cancel(handler 查标志) | ✅ 务实 | LLM 段必须实现 |
| TTS 子进程 | 为 GPU 隔离 | 你的 6014 已是独立服务,等价 |
| SenseVoice 整句无 partial | 牺牲实时字幕换简单 | 你有 6011 流式 partial,更好 |
| 语义路线判误打断(无 pVAD) | 免声纹注册,能判附和 | ✅ 园区场景采纳 |
| 形象作可砍分叉链路 | ✅ | 直接砍 |

---

## 10. 没深读的部分(纯语音落地用不上,标注以备查)
- `avatar/{musetalk,lam,liteavatar,flashhead}` — 形象,已砍。
- `client/rtc_client` — WebRTC 路径,纯语音用 ws_client 即可。
- `data_models/runtime_data/data_bundle.py` — 数据容器内部(DataBundle 的 entry/序列化),理解其"装数据+元数据"角色即可。
- `service/service_utils/*` — 配置加载/SSL/日志,工程脚手架。
- `agent/`、`logics/` — agent 扩展(ENVIRONMENT_EVENT 那套),超出基础对话范围。
