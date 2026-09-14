# 单 WebSocket 多路复用 · 具体设计要点

> 本文把"单 WS 多路复用"从选型结论落到具体实现层面,覆盖帧协议、并发模型、上下行链路、打断、状态机、错误处理。配套:[数字人语音交互协议方案归纳.md](数字人语音交互协议方案归纳.md)、[园区数字人·语音管线设计.md](园区数字人·语音管线设计.md)、[语音交互子系统-设计.md](../../../../../../C:/Users/admin/Desktop/harness-park-design/语音交互子系统-设计.md)。

---

## 0. 核心原则

1. **一条连接,两种帧**:同一条 WebSocket 上,`text` 帧走 JSON 控制/事件,`binary` 帧走音频。这是单 WS multiplex 的地基。
2. **并发不靠连接,靠队列**:为每个下行 modality(文本/音频/信号)设置独立的 asyncio Queue + 独立发送协程,避免音频发送阻塞控制消息。
3. **媒体面只翻译,不编排**:音频 ↔ 协议事件;run/工具/上下文全委托大脑。
4. **连接生命周期 ≠ 状态生命周期**:连接会话级长保;每句 `speech_end` 清 ASR/TTS 缓存,打断时清播放队列。

---

## 1. 帧协议

### 1.1 基本帧类型

| 帧类型 | 内容 | 方向 | 示例 |
|---|---|---|---|
| `text` JSON | 控制/事件/配置 | 双向 | `media_session.create`、`media.clear`、`asr.partial`、`tts.started` |
| `binary` | 音频 payload | 双向 | 上行 PCM 16k / 下行 PCM 24k |

### 1.2 text 帧规范

- 每个 JSON 消息带 `header.name`(消息类型) + `header.request_id`(用于响应/错误追溯)。
- 业务载荷放 `payload`,控制消息可空。
- 典型上行消息:
  - `media_session.create`:声明音频格式、采样率、通道、订阅内容。
  - `SendHumanAudio`:声明 binary 传输方式(binary/base64)、总大小、段数。
  - `media.clear` / `Interrupt`:打断信号。
  - `TriggerHeartbeat`:心跳触发。
- 典型下行消息:
  - `media_session.created`:确认会话建立。
  - `asr.partial` / `asr.final`:识别结果。
  - `tts.started` / `tts.completed` / `tts.cancelled`:合成状态。
  - `InterruptNotification`:服务端确认打断,通知前端停止播放。
  - `Error`:格式/超时/鉴权错误。

### 1.3 binary 帧规范

**方案 A:小帧直发(推荐,最简)**

- 每 20 ms 一帧直接 `send_bytes`。
- 帧格式在 `media_session.create` 中一次性约定:PCM 16 bit / 16 kHz / 单声道 / 小端。
- 无额外帧头,纯裸 PCM。

**方案 B:JSON 头 + 分段 binary(OAC 模式)**

- 先发送 JSON 头 `SendHumanAudio`,声明 `binary_size`、`segment_num`。
- 随后连续发送 `segment_num` 个 binary 段;服务端按注册顺序拼接(依赖 TCP 保序)。
- 适合一次上传较大音频块,但实现复杂度高于方案 A。

**落地建议**:

- **上行语音流用方案 A**:20 ms 小帧直发,无需帧头,无需组装,延迟最小,打断最灵敏。
- 下行 TTS 音频用方案 A:20 ms 小帧直发。
- 仅在上传整段音频(如文件上传)时用方案 B。

---

## 2. 并发模型:为什么单 WS 不会被音频堵住

单 WS 最大的质疑是"控制消息被大段音频堵住"。解决方式不是再加一条连接,而是**把发送侧拆成多个独立协程 + 独立队列**,并在应用层保证控制消息不排队尾。

```
┌─────────────────────────────────────────────────────────┐
│                      WebSocket 连接                      │
│  (单条 TCP, text + binary 复用)                          │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │ 统一发送锁(防并发 send 冲突)
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌─────────┐        ┌─────────┐        ┌─────────┐
   │ 文本输出 │        │ 音频输出 │        │ 信号输出 │
   │  队列   │        │  队列   │        │  队列   │
   └─────────┘        └─────────┘        └─────────┘
        ▲                   ▲                   ▲
        │                   │                   │
   ASR 文本流          TTS 音频流          打断/取消信号
```

### 2.1 关键实现点

- **每 modality 一个 `asyncio.Queue`**:文本、音频、信号分别排队,互不影响。
- **每个队列配一个独立发送协程**:从队列取到数据立即发送。
- **统一发送锁 `asyncio.Lock`**:WebSocket 的 `send_text`/`send_bytes` 不能并发调用,加锁保证顺序,但锁持有时间极短(仅一次 send)。
- **优先级策略**:控制信号帧可以跳过音频队列直接进发送锁;更简单的做法是"控制消息一到就发,不经过音频队列"。

### 2.2 实际效果

- 音频队列里即使堆积了 500 ms 的 TTS 数据,`media.clear` 信号仍然能立即被发送协程处理,不会等音频发完。
- 打断延迟 ≈ 1 个 RTT(控制消息到服务端) + 服务端 cancel 处理时间,而不是"把音频队列排空"的时间。

---

## 3. 连接生命周期

### 3.1 会话级连接

- WebSocket 在会话开始时建立,会话结束时关闭;**不是每句说完就关**。
- 一条连接承载多轮对话,复用 ASR 上游连接(OAC 模式:一条上游连接跨多句)。

### 3.2 握手流程

```
客户端                       服务端
  │                            │
  ├─ text: media_session.create ─┤
  │  {audio_in:{pcm/16k/1ch/20ms},
  │   audio_out:{pcm/24k/1ch/20ms},
  │   subscriptions:[...]}      │
  │                            │
  ├─ text: media_session.created ┤
  │                            │
  ◄──── 开始双向 binary 帧 ────►│
```

- `media_session.create` 必须携带音频格式契约,服务端校验;不支持则回 `Error`。
- `media_session.created` 之前,客户端不应发送音频 binary。

### 3.3 断连处理

- **服务端断连**:客户端立即停录、停播、提示"连接已断开,请重试"。
- **客户端断连**:服务端 `connection.close` → 取消所有进行中的任务 → 清理 `MediaSessionStore` → 释放 ASR/TTS 连接。
- **心跳**:30 s 无消息认为超时;心跳消息走 text 帧,轻量不堵。

---

## 4. 上行链路:音频 → asr.final

### 4.1 前端采集

- **AudioWorklet + ScriptProcessor  fallback**:AudioWorklet 是标准,ScriptProcessor 作旧浏览器兜底。
- **getUserMedia 配置**:
  ```js
  {
    echoCancellation: true,      // 外放场景必需
    noiseSuppression: false,     // 护辅音,ASR 模型自己扛噪
    autoGainControl: false       // 避免 ASR 输入动态范围被压
  }
  ```
- **重采样到 16 kHz**:在 AudioWorklet 内手动降采样,输出 Int16 PCM。
- **20 ms 帧**:每帧 640 字节(16k × 16bit × 0.02s),小帧直发。

### 4.2 后端入口:归一化(关卡二)

前端理论上已发 16k PCM,但**后端不可信前端**:

- 校验:采样率、通道数、位深、单帧大小。
- 兜底重采样:若前端格式不符,用 `scipy.signal.resample_poly` 抗混叠重采样到 16k。
- 归一化输出 Int16 PCM 给 ASR。

### 4.3 VAD 切句

- 服务端 fsmn-vad 切句(FunASR runtime 自带)。
- 出 `speech_start` / `speech_end`。
- `speech_end` 触发 `asr.final` + 幂等 `run.create`。

### 4.4 上游 ASR 连接复用

- 一条 ASR 上游连接承载多句,只在 `media_session.close` 时断开。
- 避免每句重新建连的开销。

---

## 5. 下行链路:message → 音频

### 5.1 后端流程

```
message.delta(文本流)
  → 句子聚合(标点/字数兜底/首标点提前送)
  → 文本清洗(去 markdown/emoji/符号/数字规范化)
  → CosyVoice stream=True 流式合成
  → Pcm24kFramer(切 20ms 帧)
  → send_bytes + tts.started/completed/cancelled
```

### 5.2 前端排期播放

```js
let nextPlayTime = audioContext.currentTime;
let playingSources = [];

function playChunk(pcm24kInt16) {
    const buffer = audioContext.createBuffer(1, sampleCount, 24000);
    buffer.copyToChannel(pcm24kInt16, 0);
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.destination);

    const startTime = Math.max(nextPlayTime, audioContext.currentTime);
    source.start(startTime);
    nextPlayTime = startTime + buffer.duration;
    playingSources.push(source);
}
```

- **`nextPlayTime` 游标**:保证音频连续不重叠。
- **`playingSources` 列表**:记录当前播放源,打断时逐个 `stop()`。
- **预留 jitter buffer**:可缓存 1-2 帧再开始播放,对抗网络抖动。

---

## 6. 打断(barge-in)的具体实现

打断是单 WS 设计的核心验证点,必须做到"快 + 干净"。

### 6.1 打断链路

```
用户开口
  ↓
前端本地 VAD 检测到持续语音(200-300ms 门限滤咳嗽)
  ↓
① 立即本地 stop 所有 playingSources + 清空排期队列   (快,不等后端)
② 发送 text: media.clear                              (通知后端)
③ 可选:发送 media.clear 后继续发新音频帧
  ↓
服务端收到 media.clear
  → run.cancelling → run_store.cancel → 硬 task.cancel
  → tts.cancelled / message.cancelled / run.cancelled
  → 下行音频停止生成
```

### 6.2 为什么单 WS 足够快

- 控制消息(`media.clear`)走 text 帧,不经过音频发送队列;即使音频 binary 队列有积压,控制消息也能插队。
- 客户端本地先停播,把"感知延迟"降到 0;后端 cancel 只影响后续音频是否继续生成。
- 20 ms 小帧意味着即使音频队列里有未发数据,总量也很小。

### 6.3 服务端硬 cancel

- `run_store.cancel` 不是协作信号,而是 `session.task.cancel()`。
- 全链必须异步:`graph.astream` → `supervise` → `await tool.run` → `httpx.AsyncClient` / `Milvus await`。
- 无 `requests/time.sleep/run_in_executor` 同步盲点,`CancelledError` 在当前 await 点抛出,真停工具/RAG/LLM。

### 6.4 清理清单(状态转换 SPEAKING→LISTENING)

- 客户端:stop 播放源、清空 `audioQueue`、重置 `nextPlayTime`、重置 `isPlaying`。
- 服务端:cancel 当前 run、cancel TTS 生成、清空下行音频缓冲、发送 `tts.cancelled` / `run.cancelled`。
- ASR:新音频进入新句子,`asr.final` 幂等创建新 `run`。

---

## 7. 状态机

### 7.1 四态 FSM

| 状态 | VAD | ASR | LLM/TTS | 播放 | 说明 |
|---|---|---|---|---|---|
| IDLE | 待命 | 关 | 关 | 关 | 可合并到 LISTENING |
| LISTENING | 工作 | 工作 | 关 | 关 | 用户说话 |
| THINKING | 待命 | 关 | 工作 | 待命 | LLM 生成中 |
| SPEAKING | 工作★ | 待命/轻量 | 工作 | 工作 | 数字人说话,可打断 |

★ SPEAKING 时 VAD 必须开着,否则无法检测打断;带来的回声问题由 AEC/半双工/pVAD 解决。

### 7.2 状态转换清理

| 转换 | 动作 |
|---|---|
| LISTENING→THINKING(speech_end) | 出 `asr.final` + 清 ASR cache/buffer + 启动 LLM |
| SPEAKING→LISTENING(打断) | cancel LLM/TTS + 清播放队列 + 重置播放游标 + 清后端缓冲 |
| 任何→IDLE(会话结束) | 清所有 cache/buffer/队列 + 释放任务 + 关闭 WS |

### 7.3 连接生命周期 ≠ 状态生命周期

- 连接是**会话级**:整个对话期间保持。
- 缓存/队列是**句子级**:每句 `speech_end` 或每次打断都要清,否则上句污染下句。

---

## 8. 错误处理与降级

### 8.1 常见错误码

| 错误码 | 场景 | 处理 |
|---|---|---|
| `AUDIO_FORMAT_ERROR` | 前端发错采样率/格式 | 服务端回错误,若支持则兜底重采样 |
| `BINARY_DATA_ERROR` | binary 段数/大小不符 | 丢弃本次 binary,等下一个 JSON 头 |
| `HEARTBEAT_TIMEOUT` | 30s 无消息 | 服务端主动关连接 |
| `INVALID_SESSION` | 未初始化就发音频 | 回错误并拒绝 |

### 8.2 弱网/重连

- **上行 ASR 句中重连**:断连即停录 + 提示"网络波动,请重说";根治需上游补帧能力(依赖 FunASR runtime 能力)。
- **下行 TTS 中断**:客户端断连后重连,不追播历史音频,只接收新数据。
- **WebSocket 重连**:会话级连接断后,建议重新走完整握手,不尝试无缝续接(状态复杂度高,收益小)。

### 8.3 室外嘈杂场景降级

- 连续采集 + 本地 VAD 扛不住时,切换到 **PTT(按住说话)**。
- PTT 不是降级,而是"确定性边界"的正解。
- PTT 档无 barge-in,因为用户主动控制句尾。

---

## 9. 前端实现 checklist

- [ ] AudioWorklet 采集 + 16k Int16 PCM 输出
- [ ] getUserMedia 配置:AEC=on,NS=off,AGC=off
- [ ] 20 ms 小帧直发 WS binary
- [ ] 本地 VAD(200-300ms 持续语音门限)
- [ ] `nextPlayTime` 游标排期播放
- [ ] 打断时 stop 所有 playingSources + 清空 audioQueue + 重置游标
- [ ] 发送 `media.clear` 后继续发新音频帧
- [ ] 心跳发送/超时处理
- [ ] 断连停录停播 + 提示重试
- [ ] 室内连续档 / 室外 PTT 档切换(重取流)

---

## 10. 后端实现 checklist

- [ ] 单 WS endpoint 接收 text + binary
- [ ] 独立接收协程 + 多个发送协程(文本/音频/信号)
- [ ] 统一发送锁
- [ ] 音频入口归一化到 16k(关卡二)
- [ ] FunASR 2pass 连接复用
- [ ] 句子聚合 + 文本清洗
- [ ] CosyVoice 流式合成 + 24k PCM 切 20ms 帧
- [ ] `media.clear` → `run.cancel` → 硬 task.cancel
- [ ] 打断时清下行缓冲、发 `tts.cancelled`
- [ ] 状态机 + 状态转换清理
- [ ] 心跳监控
- [ ] 会话结束清理所有资源

---

## 11. 与 OpenAvatarChat 的对照

| 设计点 | OpenAvatarChat(ws_client) | 本项目(v1 单 WS) |
|---|---|---|
| 帧类型 | text + binary | text + binary |
| binary 上传 | JSON 头 + 分段 binary | **20ms 小帧直发**(更简) |
| 发送模型 | 多独立发送协程 + 独立队列 | 同左 |
| 打断 | `Interrupt` JSON + `STREAM_CANCEL` 信号 | `media.clear` + `run.cancel` |
| 音频格式 | PCM/OPUS 可选 | PCM 基线,OPUS 预留 |
| 排期播放 | WebUI submodule | 前端 `nextPlayTime` 游标 |
| 状态机 | dataflow(复杂) | 显式 FSM(更可控) |

---

## 12. 一页纸总结

> **单 WS 多路复用 = 一条连接 + 两种帧 + 多队列并发 + 小帧 + 客户端先行清缓冲。**
> 帧:text JSON 走控制/事件,binary 走 20ms 音频。
> 并发:每 modality 独立 Queue + 独立发送协程,统一发送锁防冲突,控制消息不排队尾。
> 打断:前端本地 VAD 立即停播 + 清队列 + `media.clear`;后端硬 `task.cancel` 停 LLM/TTS。
> 状态机:IDLE/LISTENING/THINKING/SPEAKING,每次状态转换必须清干净上一状态残留。
> 生命周期:连接会话级,缓存句子级;断连即停录停播,不追历史音频。
