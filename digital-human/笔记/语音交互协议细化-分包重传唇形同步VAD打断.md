# 数字人语音交互协议细化：音频流分包、重传、唇形同步、VAD 与打断

> 来源：digital-human/笔记/媒体子系统契约设计方法论.md 与项目讨论整理  
> 日期：2026-07-07

---

## 一、音频流分包

### 1.1 为什么必须分包

- 一个完整句子音频可能几百 KB，WebSocket 单帧过大会导致：
  - 服务端等待时间长，延迟高
  - 中间路由/代理帧大小限制
  - 丢包时重传代价大
- 分小包可实现：
  - 流式 ASR/TTS（边说边识别、边合成边播放）
  - 低延迟首包输出
  - 服务端 Early decision

### 1.2 分包单位

| 单位 | 大小 | 适用 |
|---|---|---|
| 音频帧 | 20–40 ms（PCM 16bit 16kHz 单声道 ≈ 640–1280 bytes） | 最小粒度，最接近编解码器 |
| chunk | 100–200 ms | 常见 WS 传输单元，兼顾延迟与开销 |
| sentence | 一句完整话 | 非流式 TTS 输出 |

推荐：客户端上传用 20–40 ms 音频帧；服务端下发 TTS 用 100–200 ms chunk。

### 1.3 协议字段

```json
{
  "msg_type": "media.audio",
  "payload": {
    "stream_id": "st-uuid-001",
    "seq": 42,
    "timestamp": 1234567890,
    "codec": "pcm_s16le_16k",
    "sample_rate": 16000,
    "channels": 1,
    "data": "<base64>"
  }
}
```

服务端下发 TTS：

```json
{
  "msg_type": "media.audio",
  "payload": {
    "stream_id": "st-uuid-002",
    "seq": 7,
    "timestamp": 1234568000,
    "codec": "opus_24k",
    "sample_rate": 24000,
    "channels": 1,
    "text_offset": 15,
    "is_last": false,
    "data": "<base64>"
  }
}
```

### 1.4 分包纪律

- `stream_id`：一次完整对话流的标识，换句或重入时重置。
- `seq`：每句内从 0 开始，连续递增。gap 检测丢包。
- `timestamp`：基于音频采样时钟，不依赖网络。唇形同步用它。
- `is_last`：标记该句最后一个音频包，客户端可提前做结束处理。

---

## 二、重传

### 2.1 什么情况下重传

| 场景 | 处理 |
|---|---|
| 客户端上传音频丢包 | 服务端请求重传，或客户端检测到 gap 后主动补发 |
| 服务端下发 TTS 丢包 | 客户端请求重传，或服务端预缓存关键帧 |
| 网络抖动乱序 | 客户端按 seq 排序，缺包触发 NACK |

### 2.2 重传策略

音频流是实时流，过期重传无意义。策略要分方向：

#### 上行（客户端 → 服务端）

- ASR 可以容忍少量丢包，小 gap 用插值/concealment 补上。
- 关键包（如 vad 结束前的尾包）丢了，服务端发 NACK，客户端补发。
- 一般不用 TCP 式重传，因为延迟会爆炸。

#### 下行（服务端 → 客户端）

- TTS 流丢了，客户端发 NACK。
- 服务端保留最近 N 个已发 chunk（如 2 秒窗口），收到 NACK 后补发。
- 如果补发也过期，直接跳过，从最新包继续。

### 2.3 协议字段

NACK：

```json
{
  "msg_type": "media.nack",
  "payload": {
    "stream_id": "st-uuid-001",
    "missing_seqs": [12, 13, 14]
  }
}
```

重传包：

```json
{
  "msg_type": "media.audio",
  "payload": {
    "stream_id": "st-uuid-001",
    "seq": 12,
    "is_retransmit": true,
    "timestamp": 1234567890,
    "data": "<base64>"
  }
}
```

### 2.4 重传窗口

| 方向 | 窗口 |
|---|---|
| 上行 NACK | 服务端缓存 500 ms–1 s |
| 下行 NACK | 客户端请求最近 2 s 内丢失包 |
| 超过窗口 | 放弃，标记 audio_gap event |

---

## 三、唇形同步（Lip Sync / Viseme）

### 3.1 为什么需要唇形同步

- 数字人说话必须口型与音频对齐，否则恐怖谷效应明显。
- 唇形驱动通常基于音素（phoneme）→ 视位（viseme）映射，或服务端直接生成 viseme 时间线。

### 3.2 两种方案

| 方案 | 说明 | 优点 | 缺点 |
|---|---|---|---|
| 服务端生成 viseme | TTS 同时输出 audio + viseme timeline | 精度高，服务端算力强 | 多传一份数据 |
| 客户端本地音素识别 | 客户端从音频提取特征驱动口型 | 不依赖额外协议 | 精度低，设备要求高 |

推荐：服务端生成 viseme，协议里随音频包下发。

### 3.3 协议字段

独立 viseme 包：

```json
{
  "msg_type": "media.viseme",
  "payload": {
    "stream_id": "st-uuid-002",
    "seq": 7,
    "timestamp": 1234568000,
    "visemes": [
      {"viseme_id": 5, "start_ms": 0, "duration_ms": 80},
      {"viseme_id": 2, "start_ms": 80, "duration_ms": 120},
      {"viseme_id": 8, "start_ms": 200, "duration_ms": 90}
    ]
  }
}
```

或与 audio 包合并：

```json
{
  "msg_type": "media.audio",
  "payload": {
    "seq": 7,
    "data": "<base64>",
    "visemes": [
      {"viseme_id": 5, "start_ms": 0, "duration_ms": 80}
    ]
  }
}
```

### 3.4 同步机制

- 统一时间基：服务端生成时以 `timestamp` 为锚点。
- 客户端播放：音频按 timestamp 入播放缓冲区，viseme 按 timestamp 驱动渲染。
- 允许偏移：音频通常比 viseme 提前 20–40 ms 启动，因为听觉比视觉先感知。

### 3.5 时间戳策略示例

```
服务端 TTS 生成时间线：
  text: "你好"
  phonemes: [n, i, h, a, o]
  viseme timeline:
    n → viseme_5 @ t0
    i → viseme_2 @ t0+80
    h → viseme_8 @ t0+160
    a → viseme_1 @ t0+260
    o → viseme_6 @ t0+380

下发：
  audio chunk seq=7 timestamp=t0
  viseme chunk seq=7 timestamp=t0

客户端：
  收到 audio chunk @ t0 → 放入 jitter buffer
  收到 viseme @ t0 → 按本地播放时钟 t0 触发
  音频播放和口型渲染共享同一 clock
```

---

## 四、VAD（Voice Activity Detection）

### 4.1 VAD 作用

- 检测用户何时开始说话、何时结束说话。
- 决定什么时候把累积音频送入 ASR。
- 决定什么时候可以打断数字人。

### 4.2 VAD 落点选择

| 落点 | 优点 | 缺点 |
|---|---|---|
| 客户端 VAD | 低延迟，可本地做 barge-in | 客户端算力/算法差异大 |
| 服务端 VAD | 统一算法，精度高 | 增加上行延迟 |
| 端云协同 | 客户端粗检 + 服务端精检 | 复杂，需协议同步 |

推荐：端云协同。客户端做轻量 VAD 用于即时反馈和打断；服务端做精确 VAD 用于 ASR 切分。

### 4.3 协议字段

客户端 → 服务端：

```json
{
  "msg_type": "media.vad",
  "payload": {
    "stream_id": "st-uuid-001",
    "state": "start",
    "timestamp": 1234567890,
    "confidence": 0.95
  }
}
```

服务端确认：

```json
{
  "msg_type": "media.vad",
  "payload": {
    "stream_id": "st-uuid-001",
    "state": "end",
    "timestamp": 1234567890,
    "reason": "silence_800ms"
  }
}
```

### 4.4 VAD 状态机

```
silence ──[volume > threshold 持续 200ms]──► speech
speech  ──[volume < threshold 持续 800ms]──► silence_after_speech
silence_after_speech ──[收到 ASR final]──► end_of_utterance
```

- `start`：检测到语音开始，可以点亮麦克风提示。
- `end`：检测到语音结束，服务端可以开始完整 ASR/NLP。
- `speech`/`silence`：实时状态，用于可视化和打断判断。

---

## 五、打断（Barge-in / Interruption）

### 5.1 打断场景

| 场景 | 处理 |
|---|---|
| 数字人在说话，用户开始说话 | 立即停止 TTS 播放，清空播放队列 |
| 数字人在等待，用户抢话 | 直接开始新识别 |
| 用户连续说 | 合并为一次输入，或分段识别 |

### 5.2 打断协议

客户端 → 服务端：

```json
{
  "msg_type": "control.interrupt",
  "payload": {
    "target_stream_id": "st-uuid-002",
    "reason": "user_barge_in",
    "timestamp": 1234568000
  }
}
```

服务端 → 客户端：

```json
{
  "msg_type": "control.clear",
  "payload": {
    "target_stream_id": "st-uuid-002",
    "clear_scope": "audio_output",
    "reason": "interrupted"
  }
}
```

### 5.3 打断与 media.clear 的区别

| 消息 | 含义 | 使用时机 |
|---|---|---|
| `media.clear` | 清除本地媒体缓冲区 | 客户端主动清空，如用户切换场景 |
| `control.interrupt` | 请求打断当前对话流 | 用户说话时发 |
| `control.clear` | 服务端确认并指定清除范围 | 服务端收到 interrupt 后回复 |

### 5.4 打断状态机

```
数字人正在播放 TTS
        │
        ▼
用户开始说话（客户端 VAD start）
        │
        ▼
客户端发送 control.interrupt
        │
        ▼
服务端：
  1. 停止当前 TTS 合成
  2. 丢弃待播放队列
  3. 发送 control.clear 给客户端
  4. 通知 harness 中断当前 run_loop
        │
        ▼
客户端：
  1. 清空音频播放缓冲区
  2. 停止 viseme 动画
  3. 切到聆听状态
  4. 继续上传用户音频
```

---

## 六、时序图示例

```
客户端                    服务端
  │                        │
  │── media.vad start ────►│
  │                        │
  │── media.audio seq=0 ───►│
  │── media.audio seq=1 ───►│
  │── media.audio seq=2 ───►│
  │                        │── VAD end detected
  │                        │── ASR final: "打开空调"
  │                        │
  │◄──── thinking ─────────│
  │                        │── harness run_loop
  │                        │
  │◄── media.audio seq=0 ──│  TTS 开始合成
  │◄── media.viseme seq=0 ─│
  │◄── media.audio seq=1 ──│
  │                        │
  │── media.vad start ─────│  用户打断
  │── control.interrupt ──►│
  │                        │── 停止 TTS
  │◄── control.clear ──────│
  │                        │
  │── media.audio seq=3 ───►│
  │                        │── ASR: "调到24度"
```

---

## 七、关键设计不变量

1. **时间戳用音频采样时钟，不用网络/系统时钟**，保证唇形同步和乱序恢复。
2. **seq 只检测 gap，不重排序列号语义**，乱序由客户端 jitter buffer 处理。
3. **重传只补最近窗口，过期放弃**，实时流不能等。
4. **interrupt 必须让服务端和客户端同时达成一致**，不能只清一端。
5. **VAD 是 signal，不是 command**，只报告状态，不下发动作指令。
6. **audio 和 viseme 同 seq/timestamp 锚定**，但可独立通道发送。

---

## 八、待继续讨论

- 与 harness run_loop 的对接：语音如何触发/中断 Agent 循环
- 弱网/重连/降级策略
- 完整状态机与时序图的形式化定义
