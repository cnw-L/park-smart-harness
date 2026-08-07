# 语音事件与 harness run_loop 的对接

> 来源：digital-human/笔记/语音交互协议细化-分包重传唇形同步VAD打断.md 与项目讨论整理  
> 日期：2026-07-07

---

## 一、核心问题

harness 的 run_loop 通常是按“轮次”工作的：

```text
用户输入 → 意图解析 → 工具选择 → 执行 → 观察 → 生成回复 → 输出
```

但语音是**连续流**，不是一次性 POST：

- 用户说一句完整的话，VAD 结束时才拿到最终文本。
- 数字人回复过程中，用户可能随时打断。
- 一次语音交互可能包含多轮对话（追问、澄清、确认）。

所以需要把**流式语音状态机**映射到**离散 Agent 循环事件**。

---

## 二、两条独立的时间线

| 时间线 | 介质 | 驱动方 |
|---|---|---|
| 音频媒体流 | WebSocket 上的 `media.audio` / `media.viseme` | 客户端 ↔ 服务端 |
| Agent 推理循环 | harness run_loop | 服务端 |

关键：**音频流不直接调用 Agent，Agent 循环由语音语义事件触发**。

---

## 三、语音事件到 Agent 循环的映射

定义一组高层事件，由语音网关层产生，注入 harness：

```json
{
  "event_type": "speech.event",
  "payload": {
    "session_id": "sess-001",
    "stream_id": "st-001",
    "event": "utterance_final",
    "text": "打开空调",
    "confidence": 0.92,
    "audio_start_ms": 1000,
    "audio_end_ms": 2500
  }
}
```

事件列表：

| 事件 | 含义 | Agent 循环动作 |
|---|---|---|
| `speech.start` | 用户开始说话 | 打断当前 TTS，准备接收新输入 |
| `speech.partial` | ASR 中间结果 | 可选：用于实时意图预览，不触发循环 |
| `speech.final` | 一句话结束 | 触发一次 run_loop（用户输入） |
| `speech.cancel` | 用户说话被打断/取消 | 丢弃该次输入 |
| `reply.start` | Agent 开始生成回复 | 通知客户端进入“思考/播报”状态 |
| `reply.chunk` | TTS 合成出新 chunk | 下发 audio + viseme |
| `reply.end` | 回复播报结束 | 客户端切回聆听，等待用户输入 |
| `interrupt` | 用户打断播报 | 中断当前 run_loop，丢弃后续输出 |

---

## 四、harness run_loop 的扩展

现有 run_loop 假设输入是完整的 query。对接语音后，run_loop 需要支持：

### 4.1 输入入口

```python
class VoiceLoopRunner:
    async def on_speech_final(self, event: SpeechFinalEvent):
        # 将语音最终文本封装为 harness 输入
        turn_input = TurnInput(
            session_id=event.session_id,
            user_query=event.text,
            audio_span=event.audio_span,
            modality="voice"
        )
        await self.run_loop(turn_input)
```

### 4.2 输出流式化

run_loop 的“生成回复”阶段不再等整句完成，而是**边生成边推送**：

```python
async def stream_reply(self, turn_output_stream):
    async for chunk in turn_output_stream:
        if chunk.type == "text":
            await tts_engine.feed(chunk.text)
        elif chunk.type == "audio":
            await ws.send_audio(chunk.audio, chunk.viseme)
        elif chunk.type == "control" and chunk.control == "end":
            await ws.send_reply_end()
```

这要求 harness 内部支持**生成器式输出**，而不是一次性返回 response dict。

### 4.3 中断语义

当收到 `interrupt` 事件时，run_loop 需要：

1. **取消当前 LLM 调用**（如果还在生成）。
2. **取消当前 TTS 合成**。
3. **丢弃未下发的回复 chunk**。
4. **清理工具调用状态**：如果当前正在等工具返回，应标记该工具调用为废弃。
5. **回滚或不回滚状态**：如果已经修改了 session state，需要决定是否撤销。

```python
async def on_interrupt(self, event: InterruptEvent):
    self.current_task.cancel()
    await self.tts_engine.clear()
    await self.ws.send_control_clear(
        target_stream_id=event.target_stream_id,
        scope="audio_output"
    )
    # 状态回滚策略取决于业务
    self.session_state.revert_uncommitted()
```

---

## 五、状态机：语音会话 vs Agent 循环

```text
                    ┌─────────────┐
         用户说话 ──►│   LISTENING  │
                    └──────┬──────┘
                           │ speech.final
                           ▼
                    ┌─────────────┐
                    │  THINKING   │◄──── run_loop 启动
                    └──────┬──────┘
                           │ 首包 TTS
                           ▼
                    ┌─────────────┐
                    │  SPEAKING   │◄──── 下发 audio/viseme
                    └──────┬──────┘
                           │ 用户打断 / reply.end
              ┌────────────┴────────────┐
              ▼                         ▼
        ┌─────────────┐           ┌─────────────┐
        │ INTERRUPTED │           │   WAITING   │
        └──────┬──────┘           └──────┬──────┘
               │ 新 speech.final          │ 用户说话
               └────────────────────────►│
                                         ▼
                                  ┌─────────────┐
                                  │   LISTENING │
                                  └─────────────┘
```

注意：

- `THINKING` 期间用户也可以打断，但此时客户端还没收到 TTS，所以只需取消 run_loop。
- `SPEAKING` 期间打断需要同时通知客户端清空播放缓冲区。
- `WAITING` 是“播报结束后的静默等待”，不应与 `LISTENING` 混淆：WAITING 时用户没说话，LISTENING 时用户正在说。

---

## 六、与 harness 三环架构的对齐

harness 的三环架构（内圈 / 上下文 / 治理）对接语音事件：

| 层级 | 语音相关职责 |
|---|---|
| 内圈（run_loop） | 处理 `speech.final` → 推理 → 流式输出 TTS |
| 上下文（context） | 维护 session state、多轮历史、语音特有元数据（VAD 状态、打断次数） |
| 治理（governance） | 安全校验、工具权限、打断策略（是否允许打断、打断阈值）、审计 |

打断策略示例：

```json
{
  "voice_policy": {
    "allow_barge_in": true,
    "barge_in_threshold_ms": 200,
    "safety_phrases": ["停止", "等一下", "别说了"],
    "force_interrupt_on_safety_match": true
  }
}
```

---

## 七、关键不变量

1. **一个 `speech.final` 对应一次 run_loop 调用**，不允许一个语音输入触发多次循环。
2. **run_loop 必须是可取消的**，从 LLM 调用到 TTS 输出都要能优雅中断。
3. **interrupt 必须同步客户端和服务端状态**，不能只清客户端或服务端。
4. **部分识别结果（partial）只用于 UI 反馈，不进 run_loop**。
5. **TTS 合成和播报可以异步于 LLM 生成**，但结束事件必须对齐。

---

## 八、待继续讨论

- 弱网/重连/降级策略
- 完整状态机与时序图的形式化定义
- 多轮对话中的语义去重与历史截断
