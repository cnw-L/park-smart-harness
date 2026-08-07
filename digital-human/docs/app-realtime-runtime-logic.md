# 智慧园区助手生产级运行逻辑

本文用“真实使用流程”说明智慧园区助手如何运行。详细字段、事件和 JSON 示例见 `docs/app-realtime-protocol.md`。

先记住一句话：

```text
前端只有一个主 WS 管所有实时事件。
每次用户输入都会创建一个 run。
run 里面可以查设备、查告警、调用 LLM、生成操作票。
真正控制设备必须等用户确认 ticket。
语音只是另一种输入方式，最终也会变成 run。
```

## 0. 连接身份与 Token 先说清楚

生产环境里，`conversation_id`、`run_id`、`operation_ticket_id` 都不是身份凭证。它们只是业务对象 ID。

真正的身份来自服务端认证后的连接上下文：

```text
HTTP 登录态 / access token
  只用于调用 /app/bootstrap、会话列表、上传等 HTTP 接口。

ws_ticket
  bootstrap 或专门接口签发的一次性短期 WS 建连票据。
  只用于建立 /app/realtime/ws，不用于业务授权。

connection_auth_context
  服务端在 WS 建连后生成的连接身份上下文。
  包含 user_id、tenant_id、roles、auth_version、capability_version。

media_token
  仅在双 WS / WebRTC transport 时签发。
  只允许访问指定 media_session，不允许调用业务接口。
  单 WS（transport="realtime_ws"）实现不签发 media_token。

operation_ticket_id
  操作票 ID，不是 token。
  用户确认 ticket 时仍然要依赖当前连接身份、当前权限和 ticket 状态校验。
```

浏览器原生 WebSocket 不能像普通 HTTP 一样稳定设置 `Authorization` 头，所以生产推荐两种方式：

```text
同站部署：
  HttpOnly + Secure + SameSite Cookie
  + 服务端 Origin allowlist
  + CSRF/WS ticket 防跨站建连。

跨域或无 Cookie 场景：
  前端先通过 HTTPS 获取一次性 ws_ticket。
  WS 建连时通过 Sec-WebSocket-Protocol 或首个 connection.hello 传递。
  ws_ticket 30-60 秒过期，只能消费一次。
```

不推荐：

```text
wss://example.com/app/realtime/ws?access_token=长期token
```

原因是 URL 容易进入代理日志、浏览器历史、监控和错误上报。即使用 query，也只能放一次性短期 `ws_ticket`，并且网关日志必须脱敏。

权限变化也要有实时协议：

```text
auth.expiring
  提醒前端刷新 HTTP 登录态或重新获取 ws_ticket。

auth.refresh_required
  当前连接还能短暂保留，但新的敏感命令会被拒绝。

auth.revoked
  登录态被撤销，服务端关闭连接或只允许只读收尾。

permission.changed
  用户权限发生变化，后续 run/tool/ticket 必须用新权限重新校验。

conversation.access_revoked
  某个会话不再可访问，前端必须从订阅和页面状态移除或置灰。
```

## 1. 用户打开页面

前端先调用：

```text
POST /app/bootstrap
```

后端告诉前端：

```text
你是谁
你属于哪个租户
你有什么权限
你能不能用语音
你能不能控制设备
主 WS 地址是什么
媒体 WS 地址是什么
WS 建连认证方式是什么
最大允许几个 run 同时运行
```

然后前端建立一条主连接：

```text
WS /app/realtime/ws
```

这条 WS 不是某个会话的连接，而是当前页面的实时通道。用户打开几个会话，都复用这一条主 WS。

生产规则：

```text
bootstrap 只做能力发现。
后端不能信任前端自称的 user_id、tenant_id、role。
WS 建连必须校验 Origin、登录态或一次性 ws_ticket。
后续每次 run.create、tool_call、operation_ticket.confirm 都要重新校验权限。
```

## 2. 用户打开两个会话

比如用户同时打开：

```text
会话 A：查 A 栋告警
会话 B：查 B 栋设备
```

前端不会开两条 WS，而是通过同一条主 WS 告诉后端：

```text
conversation.subscribe A
conversation.subscribe B
```

之后服务端推事件时，每条事件都会带：

```text
conversation_id
run_id
message_id
event_cursor
stream_id
seq
```

所以前端知道这条事件属于 A 还是 B，属于哪一次执行，属于哪条消息。

前端不能这样做：

```text
把 token 追加到当前选中的会话
用全局 isStreaming 判断是否生成中
用 messages 数组下标识别消息
```

前端必须这样做：

```text
按 conversation_id + run_id + message_id + stream_id + seq 合并增量
按 event_cursor 做断线恢复
```

## 3. 用户在会话 A 发一句话

用户输入：

```text
查询 A 栋今天的告警
```

前端通过主 WS 发：

```text
run.create
conversation_id = A
input = 查询 A 栋今天的告警
```

后端创建：

```text
run_id = run_A_001
message_id = 用户消息
message_id = 助手回复草稿
```

这里的 `run_id` 就是“这一次 AI 执行”。

后端接下来可能做这些事：

```text
1. 调 Python AI 判断用户意图。
2. 判断需要查告警。
3. 通过 Java 校验权限并调用告警接口。
4. 把告警结果给 LLM 总结。
5. 通过主 WS 流式返回文本。
```

前端收到：

```text
run.created
message.created
tool_call.started
tool_call.completed
message.delta: A 栋今天共有...
message.delta: 3 条告警...
message.completed
run.completed
```

生产规则：

```text
查询业务数据必须经过 Java 权限校验。
工具超时必须返回 tool_call.failed，不能让前端一直转圈。
LLM token 不需要每个都落 DB，最终 message 和 run 终态必须落 DB。
```

## 4. 用户同时在会话 B 发一句话

用户又在 B 会话输入：

```text
查询 B 栋空调状态
```

同一条主 WS 发：

```text
run.create
conversation_id = B
input = 查询 B 栋空调状态
```

后端创建：

```text
run_id = run_B_001
```

现在 A 和 B 可以同时运行：

```text
conv_A -> run_A_001 running
conv_B -> run_B_001 running
```

前端收到事件时靠这个区分：

```text
conversation_id = A, run_id = run_A_001
conversation_id = B, run_id = run_B_001
```

所以不会串消息。

并发限制：

```text
不同 conversation 允许并行 run。
同一 conversation 默认只允许一个 primary run。
一个 run 内可以并行多个 tool/task。
默认 max_active_runs_per_user = 3。
默认 max_active_runs_per_conversation = 1。
```

## 5. 如果用户重复点击发送

这在生产一定会发生。

所以前端每次发送都带：

```text
client_message_id
idempotency_key
```

含义：

```text
client_message_id：这条用户消息的前端 ID。
idempotency_key：这次发送动作的幂等键。
```

后端规则：

```text
同一个 conversation_id + client_message_id 不重复创建用户消息。
同一个 tenant_id + user_id + command_type + idempotency_key 不重复创建 run。
同一个 idempotency_key 如果 payload 不同，返回 IDEMPOTENCY_CONFLICT。
创建 run、取消 run、确认 ticket、上传资产等有副作用命令必须提供 idempotency_key。
```

这样用户点两次，也不会生成两条回答。

## 6. 如果用户想取消

取消不是关闭 WS，也不是切换会话。

前端发送：

```text
run.cancel
run_id = run_A_001
```

这表示：

```text
只取消 A 会话这一次回答。
B 会话不受影响。
WS 不关闭。
页面不刷新。
```

取消传播：

```text
Frontend -> Gateway run.cancel
Gateway -> run.cancelling
Gateway/Python -> cancel LLM stream
Gateway/Python -> cancel pending tool tasks where possible
TTS -> stop/cancel
最终 -> run.cancelled
```

重要边界：

```text
取消 AI 生成，不等于取消已经进入执行阶段的业务操作。
取消 operation_ticket 要用 operation_ticket.cancel。
```

## 7. 如果 AI 要查询设备或业务数据

用户说：

```text
查一下 A 栋 2 层空调状态
```

正确流程是：

```text
1. AI 判断需要查询设备。
2. Python 生成 query_device_status 工具意图。
3. Java 校验用户是否有权限查看该设备。
4. Java 调设备接口。
5. Java 返回结构化结果。
6. AI 总结成自然语言。
7. 主 WS 推送 tool_call 和 message 事件。
```

设备、告警、工单、能耗、巡检查询都属于 read tool：

```text
tool_call.started
tool_call.completed
tool_call.failed
```

read tool 可以自动执行，但必须有：

```text
trace_id
tenant_id
user_id
tool_name
java_api_name
resource scope
latency
error_code
```

## 8. 如果 AI 要控制设备

用户说：

```text
关闭 A 栋 2 层空调
```

后端不能让 LLM 直接执行。

错误流程：

```text
AI -> 直接调用设备控制接口
```

正确流程：

```text
1. AI 判断用户想关闭设备。
2. Java 校验用户有没有权限。
3. Java 找到具体设备。
4. Java 创建 operation_ticket，并冻结参数。
5. 前端显示确认卡片。
6. 用户点击确认。
7. Java 再次校验当前权限。
8. Java 获取设备资源锁。
9. Java 执行设备控制。
10. Java 记录审计。
11. 主 WS 推送执行结果。
```

这就是 `operation_ticket` 的意义。

操作票必须包含：

```text
operation_ticket_id
resource
action
params_frozen
risk
confirm_policy
permission_snapshot_id
resource_lock_key
audit_context
```

生产规则：

```text
operation_ticket_id 只是业务 ID，不是授权 token。
用户确认的是 params_frozen，不是自然语言“确认”。
确认时必须检查当前登录用户、租户、会话、ticket 状态和幂等键。
执行前必须重新校验当前权限。
同一个 resource_lock_key 同时只能有一个 executing ticket。
ticket.confirm 必须幂等。
```

## 9. 如果 AI 要控制工作台

AI 不能生成 JS，也不能直接操作 DOM。

它只能发结构化 UI 意图：

```text
ui.intent: open_device_panel
ui.intent: open_alarm_detail
ui.intent: apply_filter
ui.intent: show_energy_chart
```

前端按白名单执行，并回：

```text
ui.intent.result
```

禁止：

```text
execute_script
raw_dom_operation
open_untrusted_url
bypass_route_permission
```

工作台控制和设备控制不同：

```text
ui.intent 控制页面展示。
operation_ticket 控制真实业务动作。
```

## 10. 如果用户用语音

语音不是新的一套聊天逻辑。

用户开启语音时，先通过主 WS 创建：

```text
media_session
```

第一阶段默认使用单 WS 复用：音频 binary frame 与 AppEvent 共用 `/app/realtime/ws`，不另开媒体连接。`media_session.create` 返回 `transport="realtime_ws"` 且无 `media_ws_url`/`media_token`。

```text
文本输入 -> run
语音输入 -> ASR final -> 服务端 transcript promotion -> run
图片输入 -> asset_id -> run
```

所有输入最后都归一成 run。

媒体规则：

```text
主 WS 管控制、ASR 文本、LLM 流、工具、票据、TTS 状态。
音频 binary frame 与文本 AppEvent 复用同一条 /app/realtime/ws。
media binary 帧必须带 media_session_id、track、seq、timestamp_ms、codec、duration_ms。
当前单 WS（transport="realtime_ws"）实现不签发 media_token；音频走已鉴权主连接。
transport="ws"（双 WS）时启用 /app/media/ws 与 media_token；input_lease 用于独立 media transport 的并发输入权控制。
WebRTC / LiveKit transport 另行协商信令、room、participant、track ACL 和 token，主 AppEvent 模型不变。
音频帧不进入 AppEvent 日志。
```

打断规则：

```text
用户开口打断 -> 前端本地停播放 + 发 media.clear
-> 服务端停止 tts_audio/audio_out 下行
-> tts.cancelled
-> run.cancelling
-> message.cancelled
-> run.cancelled
-> 新 asr.final 再 promotion 为新 run
```

实现现状：v1 打断由前端 `media.clear` 驱动，**不发 `barge_in.detected`、不发 `avatar.*`**（均为预留）。服务端 VAD 自动打断需 `echo_guard=false` + 前端开 AEC；否则靠前端本地 VAD + `media.clear`。

## 11. 如果网络断了

WS 断了，不代表 run 停了。

前端重连后告诉后端：

```text
我上次在 conversation:conv_A 收到 event_cursor = cur_conv_A_000000100
我正在看 conversation A
我本地 stream_msg_assistant_001 的 last_seq = 42
```

后端返回：

```text
conversation.snapshot
active_runs
缺失的事件
或者最终结果
```

所以用户刷新页面后，仍然能看到刚才那次回答有没有完成。

恢复优先级：

```text
Redis Stream 有缺失事件 -> 补发。
Redis Stream 过期但 DB 有终态 -> 返回 snapshot。
run 仍在运行 -> 返回 run.progress 后继续推新事件。
无权限 -> conversation.access_revoked。
登录态过期 -> auth.refresh_required / auth.revoked。
```

最低生产要求：

```text
刷新页面不丢会话。
已完成回答能恢复。
运行中 run 有状态。
operation_ticket 不消失。
```

## 12. 最核心的生产逻辑图

```text
页面打开
  -> bootstrap
  -> 建立 1 条主 WS

用户打开多个会话
  -> conversation.subscribe A
  -> conversation.subscribe B

用户输入
  -> run.create

run 执行中
  -> tool_call 查询业务
  -> message.delta 流式回答
  -> operation_ticket 等待确认
  -> ui.intent 控制工作台

用户确认设备控制
  -> operation_ticket.confirm
  -> Java 执行
  -> audit
  -> operation_ticket.completed

语音输入
  -> media_session
  -> audio stream
  -> asr.final
  -> run.create

断线重连
  -> connection.hello + last_event_cursor
  -> snapshot / 补事件
```

## 13. 只需要先抓住的 5 个核心概念

```text
conversation_id
  哪个会话

run_id
  这一次 AI 执行

message_id
  哪一条消息

operation_ticket_id
  哪一个待确认操作

media_session_id
  哪一次语音/数字人媒体连接
```

其他字段是为了解决生产问题：

```text
event_id / event_cursor / stream_id / seq
  event_id 防重复，event_cursor 做恢复，stream_id + seq 做单流排序。

idempotency_key
  防止重复点击和网络重试。

trace_id
  排查问题。

permission_snapshot_id
  权限审计和异步上下文。

resource_lock_key
  防止多人同时控制同一设备。
```

最终可以简单理解为：

```text
一个页面一条主 WS；
多个会话靠 conversation_id 区分；
每次请求靠 run_id 区分；
每条消息靠 message_id 区分；
设备控制靠 ticket 确认；
语音靠 media_session 输入，最后也变成 run。
```

## 14. 第一阶段 P0 验收标准

第一阶段不是完整数字人平台，但必须达到生产级骨架：

```text
1. WS 建连有认证、Origin 校验和短期/一次性建连票据策略。
2. 两个用户同时发消息，不串事件。
3. 同一用户两个会话同时运行，不错位。
4. 重复点击发送，不重复创建消息/run。
5. 取消 A run，不影响 B run。
6. WS 断开重连，能恢复 snapshot。
7. 登录态过期、权限变更、用户被踢下线有明确事件。
8. 设备查询经过 Java 权限校验。
9. 设备控制只生成 ticket，不能直接执行。
10. ticket 确认后参数冻结、幂等、重新鉴权、可审计。
11. media_token（仅双 WS / WebRTC 等独立 media transport 签发）短期、最小权限，只能访问指定 media_session。
12. 工具超时返回 tool_call.failed 或 degraded。
13. 所有关键链路有 trace_id、错误码、日志脱敏。
```
