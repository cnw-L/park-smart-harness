# Fun-ASR-Nano 实时 WebSocket 协议契约（assistant_core 后端适配器 ↔ Nano 服务）

> **适用对象**：`assistant_core` 后端的 ASR 适配器（`media/asr.py` 的 `FunAsrNanoStreamingClient`）与官方 **Fun-ASR-Nano vLLM 实时服务**（`serve_realtime_ws.py`，端口 6011）之间的协议。
>
> **前端无关**：App 前端连的是 `assistant_core` 的 app 实时协议（`media_session.create` / 二进制 PCM 帧 / `media.commit`，收 `asr.partial`/`asr.final`），与本协议解耦——换 Nano **前端不需要改动**。本文档是后端适配器的实现规格。
>
> 本文档依据官方 `serve_realtime_ws.py` 源码（`/root/Fun-ASR-official/serve_realtime_ws.py`）整理，非二手转述。

## 1. 与旧协议的差异（必读）

| 项 | 旧（现网 Paraformer 2pass） | 新（Fun-ASR-Nano 实时） |
|----|--------------------------|------------------------|
| 传输 | **wss://**（TLS，自签证书） | **ws://**（明文，无 TLS） |
| 子协议 | `binary` | **无**（不要再请求 `binary` 子协议） |
| 首帧 | JSON 配置 `{mode,chunk_size,...}` | 文本 `START` |
| 配置方式 | 首帧 JSON 字段 | 文本指令 `LANGUAGE:中文` / `HOTWORDS:a,b` |
| 音频帧 | 二进制 PCM | 二进制 **PCM16 / 16kHz / 单声道** |
| 结束 | JSON `{"is_speaking":false}` | 文本 `STOP` |
| 返回 | `{mode:"2pass-online/offline", text, is_final}` | `{sentences[], partial, is_final, ...}`（见下） |

> 简言之：**scheme 改 ws、去掉 binary 子协议、用文本指令而非 JSON 首帧、返回结构是 sentences + partial**。

## 2. 连接

```
ws://<host>:<port>
```
- 无子协议、无 TLS（如需对外 TLS，建议在网关层加反代终止）。
- 端口：见部署侧最终确认（默认 10095；本项目可能复用现网 6011，以部署同学通知为准）。

## 3. 客户端 → 服务端

| 消息 | 类型 | 说明 |
|------|------|------|
| `START` | text | 开始一次会话（重置缓冲） |
| `LANGUAGE:中文` | text | 可选，设置语种提示（如 `中文`/`English`/`日本語`） |
| `HOTWORDS:词1,词2` | text | 可选，逗号分隔热词 |
| `<PCM16 bytes>` | binary | 16kHz 单声道 16-bit 小端 PCM，连续推送（边录边发） |
| `STOP` | text | 结束会话，触发最终解码 |

> 仅在收到 `START` 后推送音频才会被处理。

## 4. 服务端 → 客户端

### 4.1 事件（控制类）
```json
{"event":"started"}
{"event":"hotwords_set","hotwords":["..."]}
{"event":"language_set","language":"中文"}
{"event":"stopped"}
```

### 4.2 识别结果（核心）
服务端在推流过程中**周期性**（约每 `decode_interval`≈0.48s 且累积到一定音频时）下发**部分结果**，`STOP` 后下发**最终结果**：

部分结果（`is_final=false`）：
```json
{
  "sentences": [
    {"text": "已确认的整句", "start": 350, "end": 2395}
  ],
  "partial": "当前正在识别、尚未定稿的文本",
  "partial_start_ms": 2400,
  "duration_ms": 3120,
  "is_final": false
}
```

最终结果（`STOP` 后，`is_final=true`）：
```json
{
  "sentences": [ {"text": "整句1","start":0,"end":1800}, {"text":"整句2","start":1820,"end":3500} ],
  "partial": "",
  "partial_start_ms": 0,
  "duration_ms": 3500,
  "is_final": true
}
```

字段说明：
- `sentences[]`：**已锁定（confirmed）** 的整句列表，按 VAD 断句产生；每句含 `text`、`start`/`end`（毫秒）。开启说话人分离时句对象可能附带说话人 id 字段。
- `partial`：**当前在识别中**、尚未锁定的文本（会不断变化/被覆盖）。
- `partial_start_ms`：`partial` 对应音频起点（毫秒）。
- `duration_ms`：已接收音频总时长。
- `is_final`：是否为本次会话的最终结果。

### 4.2.1 final 的两种触发（后端适配器行为）
后端适配器 `FunAsrNanoStreamingClient` 会在**两种情况**产出 `is_final`（→ 前端的 `asr.final`，自动停止上传 + 触发回答）：
1. **VAD 自动断句**：服务器流式 VAD 在静音超过阈值时锁定整句（`sentences` 增长），适配器据此自动出 final——**无需前端发 commit**，等价于旧 2pass 的"静音自动停"。短句默认需 ~2s 起步的尾部静音（动态阈值，长句更快）；前端需持续推流（含静音）VAD 才能判停。
2. **显式 commit 兜底**：前端发 `media.commit`（→ STOP）立即收尾出 final，适用于按钮松开/前端自有静音检测。

两者先到先得；首个 final 后该 `media_session` 即结束（一次性），下一段录音需新建 `media_session`。

### 4.3 前端渲染建议
- **已确认文本** = 顺序拼接 `sentences[].text`（稳定、不再变化）。
- **实时文本** = 在已确认文本后追加 `partial`（每次收到覆盖上一次的 `partial`）。
- 收到 `is_final:true` 时，用 `sentences` 作为最终结果，清空 `partial`。

## 5. 最小交互时序
```
C → "START"
S → {"event":"started"}
C → <PCM16 bytes> ...（持续）
S → {sentences:[...], partial:"逛一下企", is_final:false}   ← 多次，partial 持续更新
S → {sentences:[{text:"逛一下企鹅岛园区"}], partial:"", is_final:false}  ← 整句锁定进 sentences
C → "STOP"
S → {sentences:[...], partial:"", is_final:true}
S → {"event":"stopped"}
```

## 6. 后端改动清单（已落地）
这些改动已在 `assistant_core` 完成，**前端无需任何改动**：
- [x] 新增 `media/asr.py` 的 `FunAsrNanoStreamingClient/Session`：`ws://`、文本 `START`/`STOP`、`LANGUAGE:`/`HOTWORDS:`、PCM16 直传、解析 `{sentences[],partial,is_final}` → `AsrResult`。
- [x] `config.py`：新增 `asr_provider`（`funasr_nano`/`funasr_2pass`）、`asr_language`；`asr_ws_url` 默认改 `ws://192.168.1.90:6011`。
- [x] `api/realtime.py` 的 `_asr_client_from_app`：按 `asr_provider` 选择适配器（旧 2pass 路径保留可回退）。
- [x] `.env(.example)`：`ASSISTANT_ASR_WS_URL=ws://192.168.1.90:6011`、`ASSISTANT_ASR_PROVIDER=funasr_nano`、`ASSISTANT_ASR_LANGUAGE=中文`；旧 2pass 变量注释保留。
- [x] 单测：`tests/test_funasr_nano_adapter.py`。

## 7. 参考
- 服务脚本：`/root/Fun-ASR-official/serve_realtime_ws.py`
- 官方实时 demo：`docs/realtime_demo.md`（Fun-ASR 仓库）
- vLLM 引擎指南：https://github.com/modelscope/FunASR/blob/main/docs/vllm_guide.md
