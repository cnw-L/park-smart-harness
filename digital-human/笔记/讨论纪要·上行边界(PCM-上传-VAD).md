# 讨论纪要 · 上行边界(§1 PCM / §2 上传 / §3 VAD)

> 这份是**我们俩一起推出来的结论**,不是单方研究报告。按理论主线 §1-3,逐段对 OpenAvatarChat 实际代码,带行号。
> 组织框架用讨论中点破的核心原则:**AI 服务边界 = 输入合同执行点**。
> 日期 2026-06-17。配套:[研究主线.md](研究主线.md)、[OpenAvatarChat项目全解.md](OpenAvatarChat项目全解.md)。

---

## 0. 贯穿全篇的核心原则(讨论中确立)

> **AI 服务在自己的边界上定义"什么是合法输入";前端不可信,爱传什么传什么;边界这道关只放符合定义的进去,不合规的直接不处理。脏活在最外一道关做完,核心只吃干净数据。**

完整的"输入合同"有**两层**,缺一不可:
- **格式合规**:16k / 单声道 / PCM(归一化)
- **内容合规**:是不是"该处理的那一段人声"(多层过滤,见 §3)

落地地基结论:**园区多终端、杂浏览器、公共环境 → 这道边界必须自己砌全,不能信前端、不能照抄 OpenAvatarChat(它砌得不全)。**

---

## §1 PCM

**决策:走 PCM(园区内网为主,不需要 Opus 压缩省带宽)。**

OpenAvatarChat 实际:
- 默认 16k / 16bit(int16)/ 单声道 PCM;Opus 为可选项。
- 收 PCM 就一行:`np.frombuffer(audio_bytes, dtype=np.int16)`(ws_input_delegate.py:665),**reinterpret 字节、零解码** = PCM 本质。

**关键发现:后端格式兜底不对称**
| 路径 | 后端归一化到 16k? |
|------|------|
| Opus | ✅ `OpusDecoder(sample_rate=16000)`(ws_input_delegate:585) |
| 裸 PCM | ❌ 不重采样,原样收 |

前端重采样的真身(讨论中补拉 WebUI submodule 看到):`mic-processor.js` AudioWorklet 手动降采样 —— `ratio = sampleRate / 16000`,逐窗求均值 + Float32→Int16。

**理论对照(§7.4):** 两道关卡,关卡一(前端)"自律不可靠"、关卡二(后端入口)"**兜底,必须有**"。
→ **OpenAvatarChat 裸 PCM 路径只有关卡一,缺理论强制的关卡二。** 同项目 Opus 路径反而合规。
→ **我们落地:后端入口必须自己加重采样兜底**(OpenAvatarChat 这块不能照抄)。

---

## §2 上传演进

OpenAvatarChat = 时代三(流式 WebSocket),但是**微批,不是裸字节水管**:
- 一次发音频 = JSON 头 `SendHumanAudio`(声明 transport=binary / segment_num / binary_size,ws_input_delegate:685)+ 若干二进制段;
- `BinaryStreamAssembler` 按注册顺序拼(ws_binary_protocol.py:163),靠 TCP 保证段序,不查包序号;
- 还有 base64 模式(音频塞 JSON)。

**关键结论:传输层是"哑"的 —— 只搬字节,不判边界。**
- `_handle_audio_data` 末尾只 `put_data(AUDIO, audio_array)`,无任何边界标记;
- "一句话"的起止由**下游 VAD** 探(接 §3)。
- → **传输 / 语义解耦**,这是该学的:传输归传输、切句归切句。

---

## §3 VAD = 多层过滤墙(讨论中深化)

**纠偏:VAD(4 状态机)≠ "只处理合规音频"的全部。** VAD 只是最外声学层(起止 + 挡噪声),**挡得了噪声、挡不了人声**(理论 §9.2 原话:数字人的、旁人的都是人声)。
"只处理合规音频"是**多层过滤墙**,每层不同手段:

| 层(不合规音频) | 手段(理论) | OpenAvatarChat 实现(行号) | 强度 |
|------|------|------|------|
| 环境噪音 | 普通 VAD | silero 概率 `speaking_threshold 0.5`(vad_handler_silero:311) + 音量门 `volume_threshold -40`,仅 END/POST_END 开(:466) | ✅ 实 |
| 主人音但很短(附和) | 时长 + 语义 | `start_delay 2048采样=128ms` 才进 START(:133)挡碎音 + SemanticTurnDetector 停止词表(:863)/打断 prompt 第4条"嗯/哦/uh→不打断"(:128) | ✅ 实 |
| 数字人音(回采) | AEC | 浏览器 AEC `echoCancellation:True`(ws_client_handler:206) + 逻辑门 `avatar_was_speaking`(duplex_vad_handler:201);**后端无 AEC** | ⚠️ 半 |
| 非主人音(旁人) | **pVAD 声纹** | **无**(vad/ 下只有 silerovad + smart_turn_eou,无声纹/说话人分离) | ❌ 空 |

**读法要点:**
- silero 模型本身简单(出个人声概率),但 OpenAvatarChat 外面包了重逻辑:4 状态机(PRE_START→START→POST_END→END)+ POST_END 重连防腰斩 + AGC。"模型简单"≠"切句逻辑简单"。
- 音量门只在"没说话"时开(防底噪误触),说话中不开(防句中音量波动被砍)。
- 声学挡"碎"(start_delay),语义挡"短而无意"(附和词)——两道分工。

---

## 理论 vs OpenAvatarChat 的两处实际偏离(讨论中核实)

1. **silero 角色**:理论 §14 = 前端 VAD / 打断触发,后端切句用 FSMN-VAD。
   OpenAvatarChat 实际 = **silero 全在后端**(切句 `vad_handler_silero` + 打断 `duplex_vad_handler`),**无 FSMN**;**前端无任何 VAD**(WebUI 里 grep 不到 silero/onnx,前端只采集+重采样+推流)。
2. **VAD 全后端化的优点**(讨论中想清楚)——本质是"边界防御":
   - 前端极简、跨端一致、易接入(无需浏览器加载模型);
   - VAD 逻辑单点维护、可上重模型;
   - **打断决策需要服务端上下文(数字人在说什么/历史/LLM)→ 本来就只能在后端**;
   - 切句和 ASR 看同一份原始音频。
   - 代价:打断慢一个网络往返(理论 §5.1 警告)→ 但换来误打断判得准(§9.4 宁慢勿误),取舍方向对。

---

## 对园区落地的待补项(这道墙 OpenAvatarChat 砌不全的)

OpenAvatarChat 这道边界是为**单人 / 近场 / 戴耳机或手机**设计的。搬到**园区(多人 / 外放 / 公共)**有三个洞要自己补:
1. **格式兜底**:后端入口加重采样归一化(§1,理论强制、OpenAvatarChat 裸 PCM 没做);
2. **回采**:外放场景浏览器 AEC 不够,后端要有 AEC 兜底(§3 第3层);
3. **旁人音**:加 pVAD 声纹 或 说话人分离,区分主说话人(§3 第4层,OpenAvatarChat 完全空白)。
