# 智慧园区助手生产级实时协议

本文定义智慧园区助手 `/app/*` 产品实时协议。它面向前端产品、AI Runtime、Java Business Authority 和媒体通道集成，不是 OpenAI-compatible `/v1/*` 模型适配协议。

前端第一阶段对接请先看 `docs/app-frontend-realtime-contract.md`。该文档是本文的前端投影视图，明确 P0 接入矩阵、模型选择、字段责任分层和旧接口迁移规则。

运行语义见 `docs/app-realtime-runtime-logic.md`。

读协议前先抓住这条主线：

```text
页面打开 -> bootstrap -> 建立 1 条 /app/realtime/ws
用户打开多个会话 -> conversation.subscribe
用户输入 -> run.create
run 执行中 -> tool_call / message.delta / operation_ticket / ui.intent
语音输入 -> media_session -> asr.final -> run.create
断线重连 -> connection.hello -> snapshot / 补事件
```

最核心的 5 个 ID：

```text
conversation_id       哪个会话
run_id                哪一次 AI 执行
message_id            哪一条消息
operation_ticket_id   哪个待确认操作
media_session_id      哪次语音/数字人媒体连接
```

生产辅助字段：

```text
event_cursor           断线恢复游标，服务端有序
event_id               事件去重
stream_id / seq        单个流内排序和增量合并
idempotency_key        防重复点击和网络重试
trace_id               排查问题
permission_snapshot_id 权限审计
resource_lock_key      防止多人同时控制同一设备
```

后文的字段和事件都围绕这条主线展开。

## 1. Endpoint

| Endpoint | 方法 | 用途 |
| --- | --- | --- |
| `/app/bootstrap` | `POST` | 启动能力发现 |
| `/app/auth/ws-ticket` | `POST` | 刷新一次性 WS 建连票据，可选；也可由 bootstrap 返回 |
| `/app/realtime/ws` | `WS` | 主实时协议 |
| `/app/conversations` | `POST` | 创建会话 |
| `/app/conversations` | `GET` | 会话列表 |
| `/app/conversations/{conversation_id}` | `GET` | 会话详情和 snapshot |
| `/app/conversations/{conversation_id}/runs` | `POST` | HTTP 创建 run，可选；主路径可用 WS `run.create` |
| `/app/runs/{run_id}/cancel` | `POST` | HTTP 取消 run，可选；主路径可用 WS `run.cancel` |
| `/app/runs/{run_id}/events?after_cursor=...` | `GET` | 断线恢复或调试补偿接口 |
| `/app/media-sessions` | `POST` | 创建语音/数字人媒体会话 |
| `/app/assets/upload` | `POST` | 图片、文件、音频文件上传 |
| `/app/operation-tickets/{ticket_id}/confirm` | `POST` | 操作票确认 REST 兜底 |
| `/app/operation-tickets/{ticket_id}/cancel` | `POST` | 操作票取消 REST 兜底 |

第一版必须实现 `/app/bootstrap`、`/app/realtime/ws`、会话 snapshot、run 创建/取消、工具查询、模拟操作票、基础恢复。媒体、真实设备执行和完整事件回放可以分阶段实现。

## 2. Bootstrap

`POST /app/bootstrap` 用于前端启动时获取协议版本、当前用户上下文、功能开关、endpoint 和限制。

响应示例：

```json
{
  "protocol_version": "park-app-realtime.v1",
  "server_time_ms": 1779340800000,
  "user": {
    "user_id": "u_123",
    "tenant_id": "t_001",
    "roles": ["park_operator"],
    "permission_snapshot_id": "perm_001",
    "permission_snapshot_version": 12
  },
  "capabilities": {
    "text_chat": true,
    "voice_chat": true,
    "device_query": true,
    "device_control": true,
    "workbench_control": true,
    "avatar": false,
    "resume": true
  },
  "endpoints": {
    "realtime_ws": "wss://example.com/app/realtime/ws",
    "asset_upload": "/app/assets/upload"
  },
  "auth": {
    "ws_auth_mode": "cookie_or_ticket",
    "ws_ticket": "opaque_one_time_ws_ticket",
    "ws_ticket_expires_at": "2026-05-21T10:01:00+08:00",
    "auth_refresh_before_ms": 1779340700000
  },
  "limits": {
    "max_active_runs_per_user": 3,
    "max_active_runs_per_conversation": 1,
    "max_ws_subscriptions": 20
  }
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `protocol_version` | 产品实时协议版本 |
| `server_time_ms` | 服务端当前毫秒时间戳 |
| `user.user_id` | 服务端认证后的用户 ID |
| `user.tenant_id` | 服务端认证后的租户/园区 ID |
| `user.roles` | 服务端解析后的角色 |
| `user.permission_snapshot_id` | 启动时权限快照，用于审计；关键动作仍需重新校验 |
| `capabilities` | 功能开关，前端据此展示入口 |
| `endpoints` | 前端应使用的产品 endpoint |
| `auth.ws_auth_mode` | WS 建连认证模式：同站 Cookie、一次性 ticket，或二者兼容 |
| `auth.ws_ticket` | 一次性短期 WS 建连票据；Cookie 模式可为空 |
| `auth.ws_ticket_expires_at` | 建连票据过期时间，推荐 30-60 秒 |
| `auth.auth_refresh_before_ms` | 建议前端刷新登录态或重新 bootstrap 的时间 |
| `limits` | 并发和订阅限制 |

安全要求：

- 生产环境不得信任请求 query/body 中自称的 `user_id`、`tenant_id`、`role`。
- `bootstrap` 不是授权缓存，后续 `run.create`、`tool_call`、`operation_ticket.confirm` 必须重新校验权限。

### 2.1 认证、Token 与连接身份

生产协议必须区分“身份凭证”“连接票据”“业务对象 ID”和“审计快照”。

| 名称 | 作用 | 允许使用位置 | 关键规则 |
| --- | --- | --- | --- |
| `user_access_token` / session cookie | 用户登录态 | HTTP `/app/*` | 不写入 WS URL；过期、撤销、刷新由认证系统负责 |
| `ws_ticket` | 一次性 WS 建连票据 | `/app/realtime/ws` 建连或 `connection.hello` | 30-60 秒过期、只消费一次、绑定用户/租户/页面实例 |
| `connection_auth_context` | 服务端连接身份上下文 | 服务端内存/Redis registry | 前端不可提交；所有命令从这里取 `user_id`、`tenant_id`、roles |
| `media_token` | 媒体通道短期 token（**仅双 WS/WebRTC transport 才需要；当前单 WS 实现不签发**） | 独立 media WS 或 WebRTC 信令 | 只绑定指定 `media_session_id`，不能调用业务接口；单 WS 下音频走已鉴权主连接，无此 token |
| `service_token` | Java、Python、媒体服务间身份 | 服务间 HTTP/gRPC/MQ | 只证明服务身份，不代表用户业务权限 |
| `user_delegation_context` | Java 给 Python 的用户能力委托 | Python AI Runtime | 只包含工具白名单、资源范围、trace；不能绕过 Java 执行业务 |
| `operation_ticket_id` | 操作票业务 ID | AppEvent/AppCommand/REST 兜底 | 不是 bearer token；确认时仍要当前用户认证和权限校验 |
| `permission_snapshot_id` | 审计快照 | 事件、票据、审计日志 | 不能当授权凭证；关键动作必须查当前权限 |

`ws_ticket` 推荐为不透明随机值，服务端在 Redis/DB 保存 claims；也可以是签名 JWT，但必须支持一次性消费。

`ws_ticket` 最少绑定：

```json
{
  "jti": "ws_jti_001",
  "aud": "app-realtime-ws",
  "sub": "u_123",
  "tenant_id": "t_001",
  "page_instance_id": "page_001",
  "origin_hash": "sha256_origin",
  "auth_version": 7,
  "capability_version": 12,
  "exp": 1779340860,
  "one_time": true
}
```

WS 握手要求：

```text
1. 只允许 wss。
2. 校验 Origin allowlist，防止 Cross-Site WebSocket Hijacking。
3. 同站部署优先使用 HttpOnly + Secure + SameSite Cookie + Origin 校验。
4. 跨域或无 Cookie 场景使用一次性 ws_ticket。
5. 浏览器原生 WS 不稳定支持自定义 Authorization 头，不要求前端强行设置。
6. 不允许把长期 access token 放入 WS URL。
7. 如必须通过 query 传 ticket，只能传一次性 ws_ticket，并对 access log 脱敏。
8. ws_ticket 的 jti 必须在 Redis 中原子 consume，重放返回 `WS_TICKET_REPLAYED`。
```

推荐关闭码：

| 关闭码 | 含义 |
| --- | --- |
| `4401` | 未认证或 ticket 过期 |
| `4403` | 已认证但无权限 |
| `4408` | 建连后未在限定时间内完成 hello |
| `4429` | 连接或命令限流 |
| `4500` | 服务端内部错误 |

连接后的身份规则：

```text
前端命令里的 user_id、tenant_id、roles 一律忽略。
服务端从 connection_auth_context 读取当前用户身份。
每个 run/tool/ticket 都要重新走 Java 权限校验。
权限变化后，服务端推 permission.changed，并拒绝旧权限下的新敏感命令。
```

Java 与 Python 分工：

```text
Python 可以承载 AI Runtime 或阶段性承载 /app/realtime/ws。
但 Python 不能持有可直接执行业务控制的用户 token。
Python 调业务工具时，必须带 Java 签发的 user_delegation_context、trace_id、tool_name、resource_scope。
Java 根据当前用户权限、租户、资源范围做最终校验和审计。
```

`user_delegation_context` 最小结构：

```json
{
  "jti": "delegation_001",
  "iat": 1779340800,
  "nbf": 1779340800,
  "aud": "python-ai-runtime",
  "issuer": "java-business-authority",
  "kid": "java-signing-key-2026-05",
  "tenant_id": "t_001",
  "user_id": "u_123",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "tool_call_id": "tool_001",
  "allowed_tools": ["query_alarm", "query_device_status"],
  "resource_scope": {
    "park_ids": ["park_001"],
    "building_ids": ["building_a"],
    "device_ids": ["dev_201"]
  },
  "auth_version": 7,
  "policy_version": "rbac-2026-05-21",
  "trace_id": "trace_001",
  "exp": 1779341100,
  "signature": "opaque_signature"
}
```

规则：

- delegation 必须短期有效，推荐 5 分钟以内。
- delegation 只能用于工具意图和查询上下文，不能确认或执行 operation ticket。
- Java 每次收到工具请求仍要按当前权限做最终校验；delegation 不是长期授权缓存。
- delegation 必须由 Java 签名或作为 Java 可校验的不透明句柄。
- delegation 必须绑定 `run_id + tool_call_id + allowed_tools + resource_scope + auth_version + policy_version`。
- Java 必须记录 delegation `jti`，支持撤销、审计和重放检测。

## 3. AppCommand

客户端发给服务端的 WS 命令统一使用 `AppCommand`。

```json
{
  "v": "park-app-realtime.v1",
  "type": "run.create",
  "request_id": "req_001",
  "idempotency_key": "idem_001",
  "page_instance_id": "page_001",
  "conversation_id": "conv_001",
  "ts_ms": 1779340800000,
  "payload": {}
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `v` | 是 | 协议版本 |
| `type` | 是 | 命令类型 |
| `request_id` | 是 | 请求追踪 ID |
| `idempotency_key` | 按命令 | 幂等键；所有有副作用命令必须提供，包括创建 run、取消 run、确认 ticket、上传资产 |
| `page_instance_id` | 是 | 浏览器标签页实例 |
| `conversation_id` | 按命令 | 当前业务会话 |
| `ts_ms` | 建议 | 客户端发送时间 |
| `payload` | 是 | 命令负载 |

`thread_id` 规则：

- 客户端命令不得提交 AI Runtime 的 `thread_id`。
- 服务端根据 `tenant_id + conversation_id` 映射或创建后端 `backend_thread_id`。
- `backend_thread_id` 只可在服务端内部、debug trace 或审计日志中出现，不能作为前端路由、授权或恢复依据。

幂等规则：

- 幂等作用域为 `tenant_id + user_id + command_type + idempotency_key`。
- 服务端必须保存 payload hash、首次结果、状态和过期时间。
- 同一作用域内重复提交且 payload hash 相同，返回同一结果或当前状态。
- 同一作用域内 payload hash 不同，返回 `IDEMPOTENCY_CONFLICT`。
- `run.create`、`run.cancel`、`operation_ticket.confirm`、`operation_ticket.cancel`、`media_session.create`、资产上传必须支持幂等。
- 推荐 TTL：普通命令 24 小时，操作票确认和资产上传不少于 7 天，审计记录长期保存。

## 4. AppEvent

服务端推给前端的事件统一使用 `AppEvent`。

```json
{
  "v": "park-app-realtime.v1",
  "type": "message.delta",
  "event_id": "evt_001",
  "event_cursor": "cur_conv_001_000000012",
  "cursor_scope": "conversation:conv_001",
  "seq": 12,
  "stream_id": "stream_msg_002",
  "conversation_id": "conv_001",
  "backend_thread_id": "thread_001",
  "run_id": "run_001",
  "message_id": "msg_002",
  "ts_ms": 1779340800123,
  "producer": {
    "service": "python-ai-runtime",
    "agent_role": "park_ops_assistant",
    "model_profile": "ops-default",
    "model_id": "private-or-openai",
    "provider": "private-or-openai"
  },
  "trace": {
    "trace_id": "trace_001",
    "span_id": "span_001"
  },
  "delivery": {
    "replayable": true,
    "priority": "normal",
    "ack_required": false
  },
  "payload": {}
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `v` | 是 | 协议版本 |
| `type` | 是 | 事件类型 |
| `event_id` | 是 | 全局唯一事件 ID，用于去重 |
| `event_cursor` | 按事件 | 服务端有序恢复游标；可回放事件必须提供 |
| `cursor_scope` | 按事件 | `event_cursor` 的排序范围；可回放会话事件必须为 `conversation:{conversation_id}` |
| `seq` | 是 | 当前 `stream_id` 内递增序号；没有 `stream_id` 时在 `run_id` 内递增 |
| `stream_id` | 按事件 | 区分文本、工具、媒体、控制等并行事件流，避免同一 run 内多路事件抢同一个序号 |
| `conversation_id` | 按事件 | 事件所属会话 |
| `backend_thread_id` | 可选 | 服务端内部 AI Runtime 线程，仅用于 debug/trace，前端不能依赖 |
| `run_id` | 按事件 | 事件所属执行 |
| `message_id` | 按事件 | 文本增量所属消息 |
| `ts_ms` | 是 | 服务端时间 |
| `producer` | 建议 | 事件来源 |
| `trace` | 建议 | 链路追踪 |
| `delivery` | 建议 | 恢复、优先级、ack 策略 |
| `payload` | 是 | 事件负载 |

高频 `message.delta` 可以使用紧凑格式，但必须保留 `event_id`、`event_cursor`、`seq`、`stream_id`、`conversation_id`、`run_id`、`message_id`。

排序规则：

```text
event_id
  全局去重，不要求可排序，不能单独作为恢复排序依据。

event_cursor
  服务端有序恢复游标，推荐按 conversation 或 tenant 分区单调递增。
  断线恢复和补事件优先使用 event_cursor。

cursor_scope
  说明 event_cursor 的排序范围。第一版生产只定义 `conversation:{conversation_id}` 为恢复主游标。
  `connection:{connection_id}` 只能用于连接诊断，不能作为会话恢复主依据。

stream_id + seq
  前端合并文本、工具进度、TTS 片段时的局部排序依据。
  它不是断线恢复游标。

run_id
  表示事件属于哪一次执行，不保证同一 run 内所有事件共享一个单调 seq。
```

示例规则：

- `AppEvent` 的生产实现必须携带完整 envelope。
- 后文若为了突出 payload 省略 `v/event_id/event_cursor/seq/stream_id/trace`，只表示字段示意，不表示这些字段可省略。
- `delivery.replayable=true` 的事件必须写入短期事件流并生成 `event_cursor`。

推荐 cursor 规则：

```text
conversation event:
  cursor_scope = conversation:{conversation_id}
  event_cursor = cur_conv_001_000000120

connection-only event:
  cursor_scope = connection:{connection_id}
  event_cursor = cur_conn_001_000000001
```

恢复时只以每个 subscription 的 `last_event_cursor + cursor_scope` 为准。第一版不要求客户端保存全局游标。

## 5. 命令类型

| 命令 | v1 状态 | 用途 |
| --- | --- | --- |
| `connection.hello` | 必实现 | WS 建连或重连握手 |
| `conversation.subscribe` | 必实现 | 订阅会话 |
| `conversation.unsubscribe` | 必实现 | 取消订阅会话 |
| `run.create` | 必实现 | 创建 AI 执行 |
| `run.cancel` | 必实现 | 取消指定 run |
| `operation_ticket.confirm` | 必实现 | 确认操作票 |
| `operation_ticket.cancel` | 必实现 | 取消操作票 |
| `media_session.create` | 必实现 | 创建媒体会话 |
| `media_session.close` | 必实现 | 关闭媒体会话 |
| `client.ack` | 必实现 | 客户端确认收到可 ack 事件 |
| `heartbeat` | 必实现 | 心跳 |
| `run.resume` | 预留 | 恢复或继续指定 run；v1 可用 `operation_ticket.confirm` 或新 `run.create input.kind=operation_continue` 表达 |
| `ui.intent.result` | 必实现 | 前端回报 UI intent 执行结果 |

预留命令不得作为第一版验收要求。未实现的预留命令必须返回 `VALIDATION_ERROR` 或 `UNSUPPORTED_COMMAND`，不能静默忽略。

## 6. 事件类型

### 6.1 连接和订阅

```text
connection.accepted
connection.rejected
conversation.subscribed
conversation.snapshot
conversation.access_revoked
```

### 6.2 Run

```text
run.created
run.started
run.progress
run.requires_action
run.cancelling
run.cancelled
run.completed
run.failed
```

### 6.3 Message

```text
message.created
message.delta
message.completed
message.failed
message.cancelled
```

### 6.4 Tool

```text
tool_call.started
tool_call.completed
tool_call.failed
```

### 6.5 Operation Ticket

```text
operation_ticket.requires_confirmation
operation_ticket.confirmed
operation_ticket.executing
operation_ticket.approval_requested
operation_ticket.approved
operation_ticket.rejected
operation_ticket.completed
operation_ticket.failed
operation_ticket.expired
operation_ticket.conflicted
```

### 6.6 Workbench UI

```text
ui.intent
ui.intent.acknowledged
ui.intent.failed
```

### 6.7 Media

```text
media_session.created
media_session.connected
media_session.closed
speech_started
speech_stopped
asr.partial
asr.final
tts.started
tts.segment
tts.completed
tts.cancelled
barge_in.detected
media.backpressure
avatar.state
```

### 6.8 Governance

```text
auth.expiring
auth.refresh_required
auth.revoked
permission.changed
error
rate_limited
permission_denied
provider_degraded
audit.recorded
```

### 6.9 TTS 与媒体命名约定

```text
AppEvent
  使用 tts.started / tts.segment / tts.completed / tts.cancelled 表示生命周期、字幕、segment metadata。

Media track
  使用 tts_audio 或 audio_out 承载真实音频 binary frame。

Legacy
  旧文档中的 tts.audio.delta / tts.audio.done 废弃，不作为生产协议事件名。
```

`tts.segment` 示例：

```json
{
  "v": "park-app-realtime.v1",
  "type": "tts.segment",
  "event_id": "evt_tts_seg_001",
  "event_cursor": "cur_conv_001_000000060",
  "cursor_scope": "conversation:conv_001",
  "seq": 1,
  "stream_id": "stream_tts_msg_assistant_001",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "message_id": "msg_assistant_001",
  "media_session_id": "media_001",
  "payload": {
    "tts_segment_id": "tts_seg_001",
    "track": "tts_audio",
    "text": "A栋今天共有3条告警。",
    "start_ms": 0,
    "end_ms": 1800
  }
}
```

### 6.10 v1 事件实现边界

第一版必须实现：

```text
connection.accepted
connection.rejected
conversation.subscribed
conversation.snapshot
conversation.access_revoked
run.created
run.started
run.progress
run.cancelling
run.cancelled
run.completed
run.failed
message.created
message.delta
message.completed
message.failed
message.cancelled
tool_call.started
tool_call.completed
tool_call.failed
operation_ticket.requires_confirmation
operation_ticket.confirmed
operation_ticket.executing
operation_ticket.completed
operation_ticket.failed
operation_ticket.expired
operation_ticket.conflicted
ui.intent
ui.intent.acknowledged
ui.intent.failed
media_session.created
media_session.closed
speech_started
speech_stopped
asr.partial
asr.final
tts.started
tts.completed
tts.cancelled
auth.expiring
auth.refresh_required
auth.revoked
permission.changed
error
rate_limited
permission_denied
provider_degraded
audit.recorded
```

第一版预留，可不实现：

```text
operation_ticket.approval_requested
operation_ticket.approved
operation_ticket.rejected
media_session.connected   # 仅在双 WS / WebRTC 模式下有意义，单 WS 不发送
tts.segment
barge_in.detected
avatar.state
```

预留事件如果未实现，服务端不能发送；文档中出现仅表示后续兼容方向。

## 7. connection.hello

建连或重连时发送：

```json
{
  "v": "park-app-realtime.v1",
  "type": "connection.hello",
  "request_id": "req_resume_001",
  "page_instance_id": "page_001",
  "payload": {
    "ws_ticket": "opaque_one_time_ws_ticket_if_not_cookie_mode",
    "subscriptions": [
      {
        "conversation_id": "conv_001",
        "run_id": "run_001",
        "last_event_cursor": "cur_conv_001_000000099",
        "cursor_scope": "conversation:conv_001",
        "streams": [
          {
            "stream_id": "stream_msg_assistant_001",
            "last_seq": 42
          },
          {
            "stream_id": "stream_tool_001",
            "last_seq": 3
          }
        ]
      }
    ]
  }
}
```

`ws_ticket` 只在非 Cookie 模式或服务端选择首包认证时出现。Cookie 或 `Sec-WebSocket-Protocol` 已完成认证时，`connection.hello` 不需要重复携带 ticket。

服务端行为：

```text
校验连接身份、Origin、page_instance_id 和 ws_ticket 绑定关系。
Redis Stream 有 event_cursor 后的缺失事件 -> 按 event_cursor 补发。
Redis Stream 过期但 DB 有终态 -> 返回 snapshot。
run 仍运行 -> 返回 run.progress 后继续推新事件。
无权限 -> conversation.access_revoked。
登录态过期或被撤销 -> auth.refresh_required / auth.revoked。
```

恢复规则：

- `last_event_cursor` 是恢复主依据。
- `cursor_scope` 必须和订阅的 conversation 匹配；不匹配时服务端返回 `VALIDATION_ERROR` 或降级为 snapshot。
- `streams[].last_seq` 只用于客户端合并状态自检和服务端调试，不用于决定补发范围。
- 如果客户端只保存了 `event_id`，服务端可以尝试映射到 `event_cursor`；新客户端必须保存 `event_cursor`。
- 补发事件必须保持原 `event_id`、`event_cursor`、`stream_id`、`seq` 不变。

接受事件示例：

```json
{
  "v": "park-app-realtime.v1",
  "type": "connection.accepted",
  "event_id": "evt_conn_001",
  "event_cursor": "cur_connection_000000001",
  "cursor_scope": "connection:conn_001",
  "seq": 1,
  "stream_id": "stream_connection",
  "ts_ms": 1779340800123,
  "payload": {
    "connection_id": "conn_001",
    "server_instance_id": "gw_az1_03",
    "auth_expires_at": "2026-05-21T10:30:00+08:00",
    "permission_snapshot_id": "perm_001",
    "resumable": true
  }
}
```

多实例投递要求：

```text
connection registry
  保存 connection_id -> server_instance_id、user_id、tenant_id、page_instance_id、subscriptions。

event stream
  可回放事件先写 Redis Stream 或等价短期事件日志，再推给当前连接实例。

fanout
  非连接所在实例产生事件时，通过 Redis Pub/Sub、MQ 或网关内部总线唤醒 owner instance。

reconnect
  重连可以落到任意实例；新实例按 last_event_cursor、subscriptions、DB snapshot 恢复。
```

## 8. conversation.subscribe

```json
{
  "v": "park-app-realtime.v1",
  "type": "conversation.subscribe",
  "request_id": "req_sub_001",
  "page_instance_id": "page_001",
  "conversation_id": "conv_001",
  "payload": {
    "include_active_runs": true,
    "last_event_cursor": "cur_conv_001_000000099"
  }
}
```

服务端应返回：

```text
conversation.subscribed
conversation.snapshot
```

如果无权限，返回 `conversation.access_revoked` 或 `permission_denied`。

## 8.1 client.ack

`client.ack` 只确认投递，不代表 UI 动作成功、工具成功或业务操作成功。

```json
{
  "v": "park-app-realtime.v1",
  "type": "client.ack",
  "request_id": "req_ack_001",
  "page_instance_id": "page_001",
  "conversation_id": "conv_001",
  "payload": {
    "acked_event_ids": ["evt_201", "evt_202"],
    "acked_until_cursor": "cur_conv_001_000000202",
    "cursor_scope": "conversation:conv_001",
    "status": "received",
    "error_code": null
  }
}
```

规则：

- `client.ack` 只能推进服务端投递水位或清理内存队列。
- `client.ack` 不替代 `ui.intent.result`、`operation_ticket.confirm` 或任何业务确认。
- `acked_until_cursor` 必须和 `cursor_scope` 匹配。
- `delivery.ack_required=true` 的事件如果超时未 ack，服务端可以重发、降级为 snapshot 或关闭连接。

`conversation.snapshot` 示例：

```json
{
  "v": "park-app-realtime.v1",
  "type": "conversation.snapshot",
  "event_id": "evt_snapshot_001",
  "event_cursor": "cur_conv_001_000000120",
  "seq": 1,
  "stream_id": "stream_snapshot_conv_001",
  "conversation_id": "conv_001",
  "ts_ms": 1779340800123,
  "payload": {
    "conversation": {
      "conversation_id": "conv_001",
      "title": "A栋告警查询",
      "status": "active",
      "created_at": "2026-05-21T09:50:00+08:00",
      "updated_at": "2026-05-21T10:00:03+08:00"
    },
    "last_event_cursor": "cur_conv_001_000000120",
    "messages": [
      {
        "message_id": "msg_user_001",
        "client_message_id": "client_msg_101",
        "role": "user",
        "status": "completed",
        "content_parts": [
          {
            "type": "text",
            "text": "查询A栋今天的告警"
          }
        ],
        "created_at": "2026-05-21T10:00:00+08:00"
      },
      {
        "message_id": "msg_assistant_001",
        "role": "assistant",
        "status": "completed",
        "content_parts": [
          {
            "type": "text",
            "text": "A栋今天共有3条告警。"
          }
        ],
        "finish_reason": "stop",
        "created_at": "2026-05-21T10:00:00+08:00",
        "completed_at": "2026-05-21T10:00:03+08:00"
      }
    ],
    "active_runs": [
      {
        "run_id": "run_002",
        "status": "running",
        "primary": true,
        "user_message_id": "msg_user_002",
        "assistant_message_id": "msg_assistant_002",
        "client_message_id": "client_msg_102",
        "current_streams": [
          {
            "stream_id": "stream_msg_assistant_002",
            "kind": "message",
            "last_seq": 4
          }
        ]
      }
    ],
    "operation_tickets": [
      {
        "operation_ticket_id": "ticket_001",
        "status": "requires_confirmation",
        "run_id": "run_002",
        "resource": {
          "resource_type": "device",
          "resource_id": "dev_201"
        },
        "action": {
          "name": "turn_off",
          "params_frozen": {
            "target_state": "off"
          }
        },
        "expires_at": "2026-05-21T10:05:00+08:00"
      }
    ],
    "media_sessions": [
      {
        "media_session_id": "media_001",
        "status": "created",
        "mode": "voice",
        "transport": "realtime_ws",
        "expires_at": "2026-05-21T10:10:00+08:00"
      }
    ],
    "subscriptions": {
      "streams": [
        {
          "stream_id": "stream_msg_assistant_001",
          "last_seq": 16
        }
      ]
    }
  }
}
```

Snapshot 规则：

- `conversation.snapshot` 是重连、刷新页面和事件流过期后的兜底事实。
- `messages` 必须返回最终消息实体，不返回零散 delta。
- `active_runs` 返回仍在运行、取消中或等待操作的 run。
- `operation_tickets` 返回未终态 ticket，避免确认卡片在刷新后消失。
- `media_sessions` 返回仍有效的媒体会话和输入 lease，避免刷新后麦克风状态漂移。
- `last_event_cursor` 是下一次恢复的主游标。

## 9. run.create

```json
{
  "v": "park-app-realtime.v1",
  "type": "run.create",
  "request_id": "req_101",
  "idempotency_key": "idem_msg_101",
  "page_instance_id": "page_001",
  "conversation_id": "conv_001",
  "payload": {
    "client_message_id": "client_msg_101",
    "input": {
      "kind": "text",
      "text": "查询A栋今天的告警"
    },
    "agent": {
      "agent_role": "park_ops_assistant",
      "model_profile": "ops-default"
    }
  }
}
```

规则：

- 同一 `conversation_id + client_message_id` 只能创建一条用户消息。
- 同一 `tenant_id + user_id + command_type + idempotency_key` 重试返回同一 run。
- 同一 conversation 默认只允许一个 primary run。
- `input.kind` 可为 `text`、`transcript`、`multimodal`、`operation_continue`。
- `input.kind=transcript` 只用于 `media_session.options.auto_run_on_final=false` 的手动模式；必须传服务端签发的 `transcript_id`，不能只传任意 ASR 文本。
- `agent.agent_role`、`model_profile` 是请求偏好，最终选择必须由服务端 capability、租户配置和权限决定。

语音 transcript 创建 run 的规则：

- 默认 `media_session.options.auto_run_on_final=true`，服务端在产生 `asr.final` 后自动幂等创建 run，前端不得再为同一 `transcript_id` 发送 `run.create`。
- 自动创建 run 的幂等作用域为 `tenant_id + conversation_id + media_session_id + transcript_id`。
- 自动创建的用户消息 `client_message_id` 由服务端派生，推荐 `transcript:{transcript_id}`。
- 重复的 `asr.final`、media commit 重试、断线补发只能返回同一 `run_id/user_message_id/assistant_message_id`。
- 手动模式下，前端发送 `run.create input.kind=transcript`，服务端仍按 `transcript_id` 幂等去重。

典型返回事件：

```text
run.created
message.created
run.started
run.progress
message.delta
message.completed
run.completed
```

## 10. run.cancel

```json
{
  "v": "park-app-realtime.v1",
  "type": "run.cancel",
  "request_id": "req_cancel_001",
  "idempotency_key": "idem_cancel_run_001",
  "conversation_id": "conv_001",
  "payload": {
    "run_id": "run_001",
    "reason": "user_requested"
  }
}
```

规则：

- 取消指定 run，不关闭 WS。
- 取消 AI 生成不等于取消已执行中的业务操作。
- 若 run 已终态，返回当前终态或 `RUN_ALREADY_TERMINAL`。

## 10.1 Run 实体与状态机

Run 最小结构：

```json
{
  "run_id": "run_001",
  "conversation_id": "conv_001",
  "status": "running",
  "primary": true,
  "input_kind": "text",
  "client_message_id": "client_msg_101",
  "user_message_id": "msg_user_001",
  "assistant_message_id": "msg_assistant_001",
  "idempotency_key": "idem_msg_101",
  "created_at": "2026-05-21T10:00:00+08:00",
  "started_at": "2026-05-21T10:00:00+08:00",
  "terminal_at": null,
  "current_streams": [
    {
      "stream_id": "stream_msg_assistant_001",
      "kind": "message",
      "last_seq": 8
    }
  ]
}
```

状态枚举：

```text
queued
running
requires_action
cancelling
cancelled
completed
failed
```

规则：

- 同一 conversation 默认只能有一个 `primary=true` 且未终态的 run。
- `run.created` 必须返回 `run_id`、`client_message_id`、`user_message_id`、`assistant_message_id`、`idempotency_key`。
- `run.completed`、`run.failed`、`run.cancelled` 三者只能出现一个终态事件。
- `run.requires_action` 用于等待 `operation_ticket.confirm`、补充信息或审批；必须在 payload 中给出 action 类型和关联 ID。
- 重复 `run.create` 命中幂等时，服务端返回同一 run 当前状态，不创建新的 user message 或 assistant message。

## 11. message

### 11.1 Message 实体

`message_id` 是稳定消息实体 ID。前端不能用数组下标、`response_id` 或一次流式请求的临时 ID 代替。

Message 最小结构：

```json
{
  "message_id": "msg_assistant_001",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "role": "assistant",
  "status": "completed",
  "content_parts": [
    {
      "type": "text",
      "text": "A栋今天共有3条告警。"
    }
  ],
  "model": {
    "agent_role": "park_ops_assistant",
    "model_profile": "ops-default",
    "model_id": "private-or-openai",
    "provider": "private-or-openai"
  },
  "usage": {
    "input_tokens": 1260,
    "output_tokens": 86,
    "total_tokens": 1346,
    "latency_ms": 2400
  },
  "refs": {
    "tool_call_ids": ["tool_001"],
    "citation_ids": ["cite_001"],
    "asset_ids": []
  },
  "finish_reason": "stop",
  "created_at": "2026-05-21T10:00:00+08:00",
  "completed_at": "2026-05-21T10:00:03+08:00"
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `role` | `user`、`assistant`、`tool`、`system`；普通聊天列表通常展示 `user` 和 `assistant` |
| `status` | `created`、`streaming`、`completed`、`failed`、`cancelled` |
| `content_parts` | 多模态内容数组，不把图片、音频、文件直接塞进文本 |
| `model` | 生成该助手消息的 agent 和模型信息；用户消息可为空 |
| `usage` | 模型 token、时延、成本等用量信息；最终消息或 run 终态必须给出 |
| `refs.tool_call_ids` | 本消息引用过的工具调用 |
| `refs.citation_ids` | RAG 或业务数据证据引用 |
| `finish_reason` | `stop`、`cancelled`、`error`、`tool_call`、`content_filter`、`length` |

`content_parts` 类型：

```text
text
  普通文本。

asset
  图片、文件、音频等对象存储资产引用。

transcript
  ASR final 生成的 transcript_id 引用。

tool_result
  工具结构化结果摘要，通常不直接展示完整原始结果。

operation_ticket
  操作票确认卡片引用。

refusal
  安全拒答或权限拒绝说明。
```

### 11.2 message.created

```json
{
  "v": "park-app-realtime.v1",
  "type": "message.created",
  "event_id": "evt_msg_created_001",
  "event_cursor": "cur_conv_001_000000020",
  "seq": 1,
  "stream_id": "stream_msg_assistant_001",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "message_id": "msg_assistant_001",
  "payload": {
    "message": {
      "message_id": "msg_assistant_001",
      "conversation_id": "conv_001",
      "run_id": "run_001",
      "role": "assistant",
      "status": "streaming",
      "content_parts": [
        {
          "type": "text",
          "text": ""
        }
      ],
      "model": {
        "agent_role": "park_ops_assistant",
        "model_profile": "ops-default"
      },
      "created_at": "2026-05-21T10:00:00+08:00"
    }
  }
}
```

### 11.3 message.delta

```json
{
  "v": "park-app-realtime.v1",
  "type": "message.delta",
  "event_id": "evt_201",
  "event_cursor": "cur_conv_001_000000028",
  "seq": 8,
  "stream_id": "stream_msg_assistant_001",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "message_id": "msg_assistant_001",
  "payload": {
    "content_part_index": 0,
    "delta": "A栋今天共有3条告警"
  }
}
```

规则：

- 前端按 `conversation_id + run_id + message_id + stream_id + seq` 合并。
- 服务端应 30-80ms 合并 token，避免每 token 一次渲染。
- `message.completed` 或重连后的 `conversation.snapshot` 是最终校准来源；前端本地拼接文本只是临时渲染态。

### 11.4 message.completed

```json
{
  "v": "park-app-realtime.v1",
  "type": "message.completed",
  "event_id": "evt_msg_completed_001",
  "event_cursor": "cur_conv_001_000000040",
  "seq": 16,
  "stream_id": "stream_msg_assistant_001",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "message_id": "msg_assistant_001",
  "payload": {
    "message": {
      "message_id": "msg_assistant_001",
      "conversation_id": "conv_001",
      "run_id": "run_001",
      "role": "assistant",
      "status": "completed",
      "content_parts": [
        {
          "type": "text",
          "text": "A栋今天共有3条告警，其中2条未处理、1条已确认。"
        }
      ],
      "model": {
        "agent_role": "park_ops_assistant",
        "model_profile": "ops-default",
        "model_id": "private-or-openai",
        "provider": "private-or-openai"
      },
      "usage": {
        "input_tokens": 1260,
        "output_tokens": 86,
        "total_tokens": 1346,
        "latency_ms": 2400
      },
      "refs": {
        "tool_call_ids": ["tool_001"],
        "citation_ids": [],
        "asset_ids": []
      },
      "finish_reason": "stop",
      "completed_at": "2026-05-21T10:00:03+08:00"
    }
  }
}
```

### 11.5 message.failed

```json
{
  "v": "park-app-realtime.v1",
  "type": "message.failed",
  "event_id": "evt_msg_failed_001",
  "event_cursor": "cur_conv_001_000000041",
  "seq": 17,
  "stream_id": "stream_msg_assistant_001",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "message_id": "msg_assistant_001",
  "payload": {
    "status": "failed",
    "finish_reason": "error",
    "error_code": "PROVIDER_TIMEOUT",
    "message": "模型响应超时",
    "retryable": true
  }
}
```

### 11.6 message.cancelled

```json
{
  "v": "park-app-realtime.v1",
  "type": "message.cancelled",
  "event_id": "evt_msg_cancelled_001",
  "event_cursor": "cur_conv_001_000000042",
  "cursor_scope": "conversation:conv_001",
  "seq": 18,
  "stream_id": "stream_msg_assistant_001",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "message_id": "msg_assistant_001",
  "payload": {
    "status": "cancelled",
    "finish_reason": "cancelled",
    "reason": "user_barge_in"
  }
}
```

消息规则：

- `user` 消息由服务端创建和落库，前端只能提供 `client_message_id` 做幂等关联。
- `assistant` 流式消息必须先有 `message.created`，再有零到多个 `message.delta`，最后只能有一个 `message.completed`、`message.failed` 或 `message.cancelled`。
- `message.completed.payload.message` 是最终事实，覆盖前端本地拼接文本。
- `tool` 和 `operation_ticket` 相关内容可以作为 `refs` 或 `content_parts`，但真实工具结果和票据状态仍以 `tool_call.*`、`operation_ticket.*` 事件为准。

## 12. tool_call

查询类工具使用 `tool_call` 事件。

```json
{
  "type": "tool_call.started",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "tool_call_id": "tool_001",
  "payload": {
    "tool_name": "query_device_status",
    "java_api_name": "DeviceStatusQuery",
    "risk_level": "read_only",
    "status": "running",
    "timeout_ms": 5000,
    "permission_check_id": "perm_check_001",
    "input_frozen": {
      "device_id": "dev_201"
    },
    "resource": {
      "resource_type": "device",
      "resource_ids": ["dev_201"]
    },
    "data_classification": "internal"
  }
}
```

完成：

```json
{
  "type": "tool_call.completed",
  "tool_call_id": "tool_001",
  "payload": {
    "summary": "A栋2层空调主机当前运行中",
    "redacted": true,
    "structured_result": {
      "device_id": "dev_201",
      "status": "running",
      "temperature": 24.5
    }
  }
}
```

失败：

```json
{
  "type": "tool_call.failed",
  "tool_call_id": "tool_001",
  "payload": {
    "error_code": "JAVA_API_TIMEOUT",
    "message": "设备状态接口超时",
    "retryable": true
  }
}
```

规则：

- 业务查询必须经 Java 权限校验。
- 查询结果应返回结构化数据和用户可读摘要。
- 工具失败后 run 可以降级回答，也可以 `run.failed`。
- Python 只提交工具意图和参数草稿；Java 负责租户、权限、资源范围、接口调用和审计。
- 工具返回给 LLM 的内容必须是服务端整理后的可信字段集合，不能把下游原始错误堆栈、HTML、脚本或未脱敏隐私直接拼入 prompt。
- 每个 tool 必须有服务端注册的 input schema、allowed resource types、tenant scope intersection 和输出脱敏策略。
- 工具结果必须限制最大记录数和最大字节数，超限返回摘要或 `TOOL_RESULT_TOO_LARGE`。

## 13. operation_ticket

高风险操作使用 operation ticket。

```json
{
  "type": "operation_ticket.requires_confirmation",
  "event_id": "evt_ticket_001",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "operation_ticket_id": "ticket_001",
  "payload": {
    "operation_type": "device_control",
    "resource": {
      "resource_type": "device",
      "resource_id": "dev_201",
      "display_name": "A栋2层空调主机",
      "location": "A栋2层"
    },
    "action": {
      "name": "turn_off",
      "params_frozen": {
        "target_state": "off"
      }
    },
    "risk": {
      "level": "high",
      "reason": "会影响A栋2层公共区域空调"
    },
    "confirm_policy": {
      "mode": "initiator_only",
      "required_roles": ["park_operator"],
      "require_mfa": false,
      "expires_at": "2026-05-21T10:05:00+08:00"
    },
    "authorization": {
      "permission_snapshot_id": "perm_001",
      "policy_version": "rbac-2026-05-21"
    },
    "resource_lock": {
      "resource_lock_key": "t_001:device:dev_201:control",
      "lock_id": "lock_pending_001",
      "fencing_token": 1288,
      "owner_ticket_id": "ticket_001",
      "expires_at": "2026-05-21T10:05:30+08:00"
    },
    "audit_context": {
      "audit_id": "audit_pending_001",
      "initiator_user_id": "u_123",
      "tenant_id": "t_001",
      "source": "ai_assistant",
      "reason_text": "用户请求关闭A栋2层空调",
      "trace_id": "trace_001"
    }
  }
}
```

确认：

```json
{
  "type": "operation_ticket.confirm",
  "request_id": "req_confirm_001",
  "idempotency_key": "idem_confirm_ticket_001",
  "conversation_id": "conv_001",
  "payload": {
    "operation_ticket_id": "ticket_001",
    "mfa": {
      "challenge_id": "mfa_challenge_001",
      "proof": "opaque_mfa_proof"
    }
  }
}
```

规则：

- `operation_ticket_id` 只是业务对象 ID，不是 bearer token。
- 用户确认的是 `params_frozen`，不是自然语言。
- 确认命令必须依赖当前 `connection_auth_context`，并校验 tenant、user、conversation、ticket status、expires_at、confirm_policy。
- 执行前必须重新校验当前权限。
- 同一 `resource_lock_key` 同时只能一个 executing ticket。
- 资源锁必须由 Java/OperationRuntime 原子获取，包含 `lock_id`、`fencing_token`、`owner_ticket_id`、`expires_at`。
- 真实设备执行必须携带 fencing token；终态释放，超时自动释放，冲突返回 `RESOURCE_LOCKED`。
- `ticket.confirm` 必须按 `tenant_id + user_id + operation_ticket_id + idempotency_key` 幂等。
- 如果 ticket 创建后资源状态、权限策略或风险等级发生变化，返回 `operation_ticket.conflicted`，不能静默按旧自然语言执行。
- `confirm_policy.require_mfa=true` 时，确认命令必须带服务端挑战生成的 MFA proof；`operation_ticket_id` 和自然语言“确认”都不足以执行。
- 高风险 L3+ 操作必须显式点击确认，不接受语音或聊天文本作为充分确认；L4 必须进入审批或默认拒绝。
- `audit_context` 必须在 ticket 创建时冻结，并在确认、执行、失败、取消时追加审计记录。
- 第一版可只实现 simulated execution，但协议必须保持与真实执行一致。

风险策略：

| 风险等级 | 处理规则 |
| --- | --- |
| `L1/read_only` | 查询类，允许自动执行，但必须审计 |
| `L2/low` | 可结构化确认或按业务规则自动提交 |
| `L3/high` | 必须显式点击确认，可要求 MFA |
| `L4/critical` | 必须审批或默认拒绝；无审批实现时不能执行 |

审批规则：

- L4 必须发送 `operation_ticket.approval_requested`，或直接 `operation_ticket.failed` 且 `error_code=OPERATION_APPROVAL_REQUIRED`。
- 审批人不能等于发起人。
- 审批命令必须当前鉴权、幂等、可审计。
- 审批超时发送 `operation_ticket.expired`。

MFA proof 规则：

- MFA challenge 必须绑定 `tenant_id + user_id + operation_ticket_id + payload_hash + action + resource + challenge_id`。
- proof 必须短 TTL、一次性消费，不能跨 ticket 或跨用户复用。
- 确认时必须同时校验当前登录态、ticket 状态、当前权限和 MFA challenge 状态。

审计事件最小结构：

```json
{
  "audit_event_id": "audit_evt_001",
  "audit_type": "operation_ticket_confirmed",
  "tenant_id": "t_001",
  "actor_user_id": "u_123",
  "service": "java-business-authority",
  "operation_ticket_id": "ticket_001",
  "run_id": "run_001",
  "policy_version": "rbac-2026-05-21",
  "permission_snapshot_id": "perm_001",
  "payload_hash": "sha256_payload",
  "mfa": {
    "required": true,
    "challenge_id": "mfa_challenge_001",
    "verified": true
  },
  "resource_lock": {
    "lock_id": "lock_001",
    "fencing_token": 1288
  },
  "trace_id": "trace_001",
  "created_at": "2026-05-21T10:00:03+08:00"
}
```

审计日志必须 append-only，覆盖 `ticket_created`、`confirmed`、`approval_requested`、`approved`、`rejected`、`executing`、`completed`、`failed`、`cancelled`、`conflicted`。

## 14. ui.intent

```json
{
  "type": "ui.intent",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "payload": {
    "intent": "open_device_panel",
    "target": "device_panel",
    "params": {
      "device_id": "dev_201"
    },
    "requires_client_ack": true
  }
}
```

允许白名单：

```text
open_device_panel
open_alarm_detail
open_work_order
apply_filter
highlight_map_device
show_energy_chart
focus_camera_view
```

禁止：

```text
execute_script
raw_dom_operation
open_untrusted_url
bypass_route_permission
```

前端执行后返回命令 `ui.intent.result`：

```json
{
  "v": "park-app-realtime.v1",
  "type": "ui.intent.result",
  "request_id": "req_ui_ack_001",
  "idempotency_key": "idem_ui_ack_evt_ui_001",
  "page_instance_id": "page_001",
  "conversation_id": "conv_001",
  "payload": {
    "intent_event_id": "evt_ui_001",
    "run_id": "run_001",
    "status": "applied",
    "error_code": null
  }
}
```

规则：

- `ui.intent` 只能驱动前端白名单动作，不能携带脚本、表达式或任意 URL。
- 前端执行前仍要检查本地路由权限和当前页面能力，不满足时返回 `ui.intent.result status=failed`。
- 服务端收到 result 后可推 `ui.intent.acknowledged` 或 `ui.intent.failed` 事件。
- `ui.intent.result` 只表示页面动作已处理，不代表设备控制或业务操作成功。

## 15. media_session

> **传输选型说明**：协议支持多种媒体传输模式，由 `media_session.create` 的 `transport` 字段协商决定。
> 第一版推荐 **单 WS 复用**（`transport="realtime_ws"`）：音频二进制帧直接走主 `/app/realtime/ws`，
> 不另开 `/app/media/ws`、不签发 `media_token`。该模式已在 Python 后端真机验证。
>
> 但如果 Java 网关基于 **STOMP 等文本协议栈** 实现主 WS，或团队希望媒体层与主 WS 生命周期解耦，
> 可选用 **双 WS**（`transport="ws"`）：主 WS 管 AppEvent/AppCommand，独立 `/app/media/ws` 管音频 binary，
> 此时启用 `media_ws_url` + `media_token`。WebRTC / LiveKit 作为后续扩展。
>
> 下文中 `transport="realtime_ws"` 表示单 WS 复用；`transport="ws"` 表示双 WS；两者都属 v1 合法实现，
> 前端根据 `media_session.created` 返回的 `transport` 与 `media_ws_url` 决定如何发送音频。

创建命令：

```json
{
  "v": "park-app-realtime.v1",
  "type": "media_session.create",
  "request_id": "req_media_001",
  "idempotency_key": "idem_media_001",
  "conversation_id": "conv_001",
  "payload": {
    "mode": "voice",
    "transport": "realtime_ws",
    "features": [
      { "feature": "auto_run_on_final", "enabled": true, "required": true },
      { "feature": "echo_guard", "enabled": true, "required": false },
      { "feature": "client_aec", "enabled": true, "required": false }
    ],
    "turn_detection": {
      "mode": "server_vad",
      "endpoint_silence_ms": 800,
      "interrupt": "any_speech"
    },
    "audio": {
      "audio_in": {
        "enabled": true,
        "codec": "pcm16",
        "sample_rate": 16000,
        "channels": 1,
        "frame_duration_ms": 20
      },
      "audio_out": {
        "enabled": true,
        "codec": "pcm16",
        "sample_rate": 24000,
        "channels": 1
      }
    }
  }
}
```

字段：

- `transport`：媒体传输模式。v1 合法值 `realtime_ws`（单 WS 复用）或 `ws`（双 WS，独立 media WS）；未来扩展 `webrtc`、`livekit` 等。
- `auto_run_on_final`：`asr.final` 后由服务端按 `transcript_id` 幂等自动建 run（默认 true）。
- `echo_guard`：助手出声期间后端丢弃该会话 ASR 结果防自打断（默认 true）；前端确认开了 AEC 后设 false 解锁服务端 VAD 语音打断。
- `features`：客户端请求的能力列表，每项为 `{feature, enabled, required?}` 对象。服务端在 `media_session.created` 中回显实际启用的能力；未启用且 `required=true` 时创建失败，未启用且 `required=false` 时进入 `disabled_features`。
- `turn_detection`:断句/轮次/打断配置(🔧 spec)。**定位 = 前端意图 / 后端 `AudioInputConfig` 适配层契约,不是直通引擎的字段**——⚠️ 我们生产直连的是 **FunASR runtime 开源版**(6011/6012),它的客户端协议**只收** `mode/wav_format/is_speaking/audio_fs/chunk_size/chunk_interval/encoder_chunk_look_back/decoder_chunk_look_back/hotwords/itn`,**不含 silence/semantic 开关**(实读 `funasr_wss_server.py` 确认)。所以下面字段由后端映射,不能假设直通 runtime。
  - `mode`=`server_vad`(**实现态默认**:断句由 **FunASR runtime 服务端 fsmn-vad 模型**做,客户端调不动)/`manual`(**实现态**:PTT,前端 `media.commit` → FunASR `is_speaking:false`——**这俩是 runtime 真字段**)。
  - `endpoint_silence_ms`:**意图值(默认 800),非引擎直通**。FunASR runtime 客户端协议不收;静默端点在服务端 VAD,**不能每会话热调到任意值**;后端映射到服务端 VAD 配置或前置一层 VAD 才能调。
  - `interrupt`=`any_speech`(**实现态默认,纯应用层**:客户端本地 VAD 持续语音→停 TTS 播放 + 200-300ms 最小时长门 + `media.clear` + 硬 `run.cancel`;不碰 LLM/GPU,与 FunASR 无关。WS 传输下客户端管播放本就如此)/`semantic`(🔧 **预留**:未来轻量模型判"真打断 vs 附和" + `resume_false_interruption`)。
  > **不上 OpenAvatarChat 那种 LLM 判官打断**(Qwen3-8B 判意图,3s 超时):不在 <150-300ms 预算 + GPU1 已满 + 逆行业趋势(行业在把打断从 LLM 手里拿走)。
  > **本项目轮次纠错靠屏幕**:有屏 → ASR partial 上屏 + 一键取消/重说,比模型/LLM 判官便宜可靠(消费级纯语音才需把轮次判死=无别的纠错通道)。
  > ⚠️ **参数名不抄阿里云 SaaS,也不抄 OpenAI**:`max_sentence_silence`/`semantic_punctuation_enabled` 是**阿里云 Model Studio SaaS** 的(我们没跑),FunASR runtime 不收;`threshold/prefix_padding` 是 OpenAI 能量 VAD 的。本契约用**中性适配层名** `endpoint_silence_ms`/`interrupt`,后端按实际底座映射。流式延迟真旋钮 = FunASR runtime `chunk_size`(默认 `[5,10,5]`)/`encoder_chunk_look_back`/`decoder_chunk_look_back`,在 `audio.audio_in`。**室内 mode=server_vad,室外 mode=manual(PTT,无需任何轮次检测/barge-in)。**
- `audio.audio_out`：下行 TTS 为**裸 PCM16 @ 24kHz**（CosyVoice2 原生采样率，SDK 直接排期播放，无编解码延迟）。

创建事件（实现实际返回的 payload）：

```json
{
  "type": "media_session.created",
  "conversation_id": "conv_001",
  "media_session_id": "media_001",
  "payload": {
    "media_session_id": "media_001",
    "mode": "voice",
    "transport": "realtime_ws",
    "features": [
      { "feature": "auto_run_on_final", "enabled": true },
      { "feature": "echo_guard", "enabled": true },
      { "feature": "client_aec", "enabled": true }
    ],
    "disabled_features": [],
    "audio": { "audio_in": { "...": "回显请求的音频配置" }, "audio_out": { "...": "..." } }
  }
}
```

`disabled_features` 示例（非空时说明某项能力未被启用）：

```json
{
  "feature": "client_aec",
  "enabled": false,
  "reason_code": "CLIENT_AEC_NOT_CONFIRMED",
  "reason": "前端未上报已开启 AEC，服务端保留 echo_guard"
}
```

媒体会话状态：

```text
created
closing
closed
failed
```

生命周期规则：

- `media_session.created` 后，前端按返回的 `transport` 发送音频：
  - `transport="realtime_ws"`：直接在**同一条主 WS** 上发音频二进制帧，无需另建连接、无 `media.hello` 握手。
  - `transport="ws"`：按 `media_ws_url` 建立独立 media WS，走 `media.hello`/`media.accepted` 握手，用 `media_token` 鉴权。
- 单 WS 模式下无 `media_token`、无 `media_ws_url`、无 `input_lease`：音频复用主连接的鉴权与生命周期。
- `media_session.close` 是**关闭媒体会话的命令**，需要幂等；关闭原因包括 `user_closed`、`run_cancelled`、`barge_in`、`network_lost`。
- `media.clear` 是**会话存续期间的信号/命令**，只清空未提交的 ASR 输入缓冲并取消当前输出，不关闭媒体会话；禁止用 `media_session.close` 代替打断。
- 主 WS 断线时，单 WS 模式媒体即中断；双 WS 模式下媒体 WS 应同步关闭或进入恢复流程。
- `media_session.connected` 在单 WS 下不发送；在双 WS 下表示独立 media WS 握手成功，可发送。
- 双 WS / WebRTC 方向的 `media_token` 续租、input lease 抢占等规则，仅在启用独立 media transport 时适用。

ASR partial：

```json
{
  "type": "asr.partial",
  "conversation_id": "conv_001",
  "media_session_id": "media_001",
  "payload": {
    "transcript_id": "transcript_001",
    "text": "帮我查一下A栋",
    "confidence": 0.82,
    "start_ms": 0,
    "end_ms": 1200
  }
}
```

ASR final：

```json
{
  "type": "asr.final",
  "conversation_id": "conv_001",
  "media_session_id": "media_001",
  "payload": {
    "transcript_id": "transcript_001",
    "text": "帮我查一下A栋今天的告警",
    "start_ms": 1200,
    "end_ms": 4300
  }
}
```

ASR final promotion：

```text
auto_run_on_final=true
  服务端以 transcript_id 幂等创建 run，并推送 run.created/message.created。

auto_run_on_final=false
  前端展示 asr.final，由用户或前端策略再发送 run.create input.kind=transcript。

幂等键
  tenant_id + conversation_id + media_session_id + transcript_id。
```

规则：

- ASR final 触发普通 `run.create`。
- 音频帧不进入 AppEvent 日志（只过 `[voice]` 诊断日志）。
- 未来 WebRTC 只改变 `transport` 与 token，不改变主事件模型。
- `auto_run_on_final=true` 时，`asr.final` 由服务端自动 promotion 为 run；前端只展示事件，不重复提交。
- 单 WS 下音频复用主连接鉴权，上行音频仍须校验格式、采样率、单帧大小、总时长和租户限额。
- `asr.final` 的 `transcript_id` 由服务端签发；后续 `run.create input.kind=transcript` 应引用该 ID。
- 前端展示 ASR 文本可以用 `text`，但服务端执行 run 时应以 `transcript_id` 对应的服务端记录为准。

VAD 状态事件：

```json
{
  "type": "speech_started",
  "conversation_id": "conv_001",
  "media_session_id": "media_001",
  "payload": {
    "transcript_id": "transcript_001",
    "timestamp_ms": 120
  }
}
```

```json
{
  "type": "speech_stopped",
  "conversation_id": "conv_001",
  "media_session_id": "media_001",
  "payload": {
    "transcript_id": "transcript_001",
    "timestamp_ms": 4320,
    "reason": "endpoint_silence"
  }
}
```

规则：

- `speech_started` / `speech_stopped` 由服务端 VAD 产生，表示一段可识别的语音区间。
- 每个区间必须分配一个服务端 `transcript_id`，后续 `asr.partial`、`asr.final`、`run.create input.kind=transcript` 都引用该 ID。
- `transcript_id` 在一次 `media_session` 内唯一；同一 `media_session` 出现新的 `speech_started` 即开启新 transcript。
- v1 服务端 VAD 断句后自动触发 `asr.final`，前端无需发送 `media.commit`；`media.commit` 仅作为 PTT/手动模式兜底。

> 以下 `media_token` 绑定与安全规则**仅在双 WS / WebRTC transport 时适用**；
> 单 WS（`transport="realtime_ws"`）实现不签发 `media_token`（音频走已鉴权主连接），可跳过本小节。

`media_token`（仅双 WS/WebRTC 适用）最少绑定：

```json
{
  "jti": "media_jti_001",
  "aud": "app-media-ws",
  "tenant_id": "t_001",
  "user_id": "u_123",
  "conversation_id": "conv_001",
  "media_session_id": "media_001",
  "page_instance_id": "page_001",
  "allowed_publish": ["audio_in"],
  "allowed_subscribe": ["audio_out", "tts_audio"],
  "input_lease_id": "lease_001",
  "auth_version": 7,
  "capability_version": 12,
  "origin_hash": "sha256_origin",
  "exp": 1779341100
}
```

媒体安全规则（仅双 WS/WebRTC 预留）：

- `media_token` 只能用于指定 `media_session_id`，不能订阅其他会话或媒体流。
- `media_token` 必须绑定 `auth_version`、`capability_version`、`page_instance_id` 和 Origin；登录态撤销或权限变化时必须可撤销。
- media WS token 的 `jti` 应在连接时一次性消费；重连需要服务端重新签发或显式允许 connection resume。
- 并发输入 lease 仅在独立 media transport 下需要；单 WS 下输入权由唯一主连接天然持有。

### 15.1 主 WS 媒体帧协议（单 WS 复用模式）

音频二进制帧直接在主 `/app/realtime/ws` 上收发——同一条连接既走文本 AppEvent，也走音频 binary frame。**单 WS 模式无独立 `/app/media/ws`、无 `media.hello`/`media.accepted` 握手**：

```text
1. 前端通过主 WS 发送 media_session.create（transport="realtime_ws"）。
2. 服务端返回 media_session.created（transport="realtime_ws"，无 media_ws_url/media_token）。
3. 前端即在同一条主 WS 上开始发上行 binary media frame（track=audio_in）。
4. 服务端在同一条主 WS 上回 asr.partial/asr.final 文本事件，并下发 TTS binary frame（track=tts_audio）。
```

> 单 WS 模式下 `media.hello` / `media.accepted` 不使用（连接身份已由主 WS 的 `connection.hello` 建立）。
> 若 `transport="ws"`（双 WS），则必须走独立 media WS 的 `media.hello`/`media.accepted` 握手，详见 §15.2。

Binary frame 格式（主 WS 上的非文本帧）：

```text
4 bytes unsigned big-endian header_length
header_length bytes UTF-8 JSON header
remaining bytes media payload
```

> ⚠️ **开销权衡(对照阿里 ISI 的"裸二进制音频")**:阿里 ISI 直接发裸音频二进制帧、不带 per-frame header(会话上下文由前面的 text 指令建立)。本协议每 20ms 帧带完整 JSON header,把**会话恒定字段(media_session_id/codec/sample_rate/channels)每帧重复**——换来"自描述 + 多 track 就绪",代价是相对 960B PCM 的 header 开销。**优化项(规模上来再做)**:稳态帧只留 `track/seq`(+ 必要 flags),会话级字段在 `media_session.create` 定、帧不再重复;现阶段保留完整 header 不阻塞。

Binary frame header（v1 完整形；稳态可瘦身）：

```json
{
  "v": "park-media.v1",
  "media_session_id": "media_001",
  "track": "audio_in",
  "frame_id": "mf_000001",
  "seq": 1,
  "timestamp_ms": 0,
  "duration_ms": 20,
  "codec": "pcm16",
  "sample_rate": 16000,
  "channels": 1,
  "flags": {
    "key_frame": false,
    "silence": false
  }
}
```

规则：

- `v` 固定为 `park-media.v1`，与主 AppEvent 的 `park-app-realtime.v1` 独立演进。
- `seq` 在 `media_session_id + track` 内单调递增。
- `timestamp_ms` 是该媒体会话内的相对媒体时钟（以 `media_session.created` 为 0），不是服务端 wall clock。
- `duration_ms` 推荐 20-100ms，第一版语音推荐 20ms。
- 上行 `audio_in` 用于 ASR；下行 `audio_out` 或 `tts_audio` 用于 TTS/数字人语音。
- `flags` 在 v1 仅保留 `key_frame` 和 `silence` 两个位；**所有控制语义（commit/end/clear）只通过 text 命令发送**，不允许放在 binary flags 里。
- 媒体 frame 不进入 AppEvent 日志；只记录 frame 计数、字节数、时长、错误码和 trace。
- 丢帧、乱序、codec 不匹配、超出 `max_frame_bytes` 时，服务端在同一条主 WS 上返回 `error` 或 `provider_degraded`；启用独立 media transport（如双 WS）时建议通过 `media.error` 返回。

Frame validation：

| 校验项 | 要求 | 失败处理 |
| --- | --- | --- |
| `header_length` | 最大 16KB，必须是合法 UTF-8 JSON | 返回 `VALIDATION_ERROR`，严重时关闭 WS |
| `max_frame_bytes` | 包含 header 和 payload 总长度 | 超限返回 `PAYLOAD_TOO_LARGE` |
| `seq` 重复 | 幂等丢弃重复 frame，不重复送 ASR/TTS | 记录 `duplicate_frame` |
| `seq` 跳号 | 短暂等待可重排窗口，超时后标记丢帧 | 返回 `MEDIA_FRAME_GAP` |
| `timestamp_ms` 倒退 | 拒绝该 frame | 返回 `MEDIA_CLOCK_SKEW` |
| codec/采样率不匹配 | 拒绝该 track frame | 返回 `UNSUPPORTED_MEDIA_TYPE` |
| 空 payload | 仅允许在 text 命令中表达控制语义；binary frame 空 payload 视为非法 | 返回 `VALIDATION_ERROR` |
| 非法 `flags` 位 | v1 只接受 `key_frame`/`silence`，出现其他位返回 `VALIDATION_ERROR` | 返回 `VALIDATION_ERROR` |

媒体控制消息（全部通过主 WS 的 text AppCommand/AppEvent 收发，binary frame 不带控制语义）：

```text
media.commit
  提交当前输入缓冲，要求 ASR 尽快输出 final。
  v1 默认由服务端 VAD 自动触发，前端仅在 PTT/手动模式下显式发送。

media.clear
  清空未提交输入缓冲，用于 barge-in 或用户取消说话。
  这是"会话存续期间的信号"，不关闭 media_session。
  打断 = 停 CosyVoice 下行流 + 取消 run（级联编排；FunASR/CosyVoice 组件不管打断，这是应用层的事）。
  **多轮上下文截断(v1 = 服务端粗截断)**:服务端把被打断的助手消息截到"**已合成/已发 message.delta 的部分**"
   再落库（服务端自知，无需客户端字段，无文本-音频对齐依赖；会 overcount 一个播放缓冲深度，可接受）。
  **可选精确截断(OpenAI 式，默认不做)**:media.clear 带 `audio_end_ms`(用户实际听到的毫秒)→ 服务端截到真听到处；
   ⚠️ 但级联里需"音频ms→文本位置"对齐(即 `tts.segment`{text,start/end_ms}，当前预留未发)，启用对齐后再做。

media_session.close
  主动关闭整个媒体会话；服务端确认后发送 `media_session.closed`。
  不能用 `media.clear` 或 `media.commit` 代替关闭。

media_session.closed
  服务端确认 media_session 已关闭，payload 携带 `reason`。

media.backpressure
  服务端提示前端降低发送速率或暂停上行。
```

Barge-in 处理链（单 WS 复用模式）：

```text
1. 前端本地 VAD 检测用户开口（有 AEC 时）-> 立即本地停播放（§5.4 铁律1，不等服务端）。
2. 前端在主 WS 发 media.clear。
3. 服务端停止下行 tts_audio 队列，取消该会话活跃 run：run.cancelling(reason=barge_in)。
4. 主 WS 推送 tts.cancelled -> message.cancelled -> run.cancelled。
5. 新的 ASR final 按 auto_run_on_final 规则创建新 run。
```

> 实现现状：打断由前端 `media.clear` 驱动，**不发 `barge_in.detected`、不发 `avatar.*`**（均为预留）。
> 服务端 VAD 自动打断需 `echo_guard=false` + 前端开 AEC；否则靠前端本地 VAD + `media.clear`。
> 双 WS 模式下步骤 2 的 `media.clear` 仍在主 WS 发送，音频 binary 只过 media WS。

规则：

- barge-in 不能取消已经进入 `operation_ticket.executing` 的真实业务操作。
- barge-in 后生成的新 run 必须有新的 `run_id`，但可以引用被打断的 `previous_run_id`。
- 下行媒体帧取消后，不再发送旧 `tts_segment_id` 的 audio frame。

WebRTC / LiveKit transport：

```json
{
  "transport": "livekit",
  "signaling": {
    "url": "wss://livekit.example.com",
    "room_id": "room_media_001",
    "participant_id": "u_123_page_001",
    "token": "opaque_livekit_token",
    "allowed_publish_tracks": ["audio_in"],
    "allowed_subscribe_tracks": ["tts_audio", "avatar_audio", "avatar_video"],
    "expires_at": "2026-05-21T10:10:00+08:00"
  }
}
```

规则：

- 主 AppEvent 模型不变，`media_session.transport` 决定媒体承载。
- `transport=webrtc/livekit` 必须有 transport-specific signaling payload。
- token 必须绑定 `media_session_id`、`room_id`、`participant_id`、publish/subscribe tracks、TTL。
- track identity 必须能映射回 `media_session_id + track`，以便 TTS、barge-in 和数字人同步。

### 15.2 双 WS 媒体帧协议（独立 media WS 模式）

当 `transport="ws"` 时，音频 binary 走独立 `/app/media/ws`，主 WS 继续跑 AppEvent/AppCommand。

建连流程：

```text
1. 前端通过主 WS 发送 media_session.create（transport="ws"）。
2. 服务端返回 media_session.created，携带 media_ws_url 与 media_token。
3. 前端建立 /app/media/ws，发送 media.hello（携带 media_token、media_session_id）。
4. 服务端返回 media.accepted；此后前端在 media WS 上发送 audio_in binary frame。
5. ASR/TTS 控制命令（media.clear / media.commit 等）仍通过主 WS 收发。
```

`media.hello` 示例：

```json
{
  "v": "park-media.v1",
  "type": "media.hello",
  "media_session_id": "media_001",
  "payload": {
    "media_token": "opaque_media_token",
    "page_instance_id": "page_001",
    "supported_tracks": ["audio_in"],
    "supported_codecs": ["pcm16"]
  }
}
```

`media.accepted` 示例：

```json
{
  "v": "park-media.v1",
  "type": "media.accepted",
  "media_session_id": "media_001",
  "payload": {
    "transport": "ws",
    "tracks": ["audio_in", "tts_audio"],
    "expires_at": "2026-05-21T10:10:00+08:00"
  }
}
```

规则：

- media WS 只承载音频 binary frame，不承载文本 AppEvent。
- `media_token` 必须一次性消费、绑定 `media_session_id` 与 `page_instance_id`。
- media WS 断线不影响主 WS；重连时需要重新 `media.hello`，或按服务端策略恢复。
- 双 WS 模式下的 binary frame header、校验规则与单 WS 一致（§15.1）。

### 15.3 选型建议

| 模式 | 适用场景 | 对 Java 网关的要求 |
| --- | --- | --- |
| `realtime_ws` 单 WS 复用 | 延迟敏感、网关原生支持 binary WebSocket | 同一 Endpoint 同时处理 text/binary（`TextWebSocketHandler` + `BinaryWebSocketHandler` 或 javax `Endpoint`） |
| `ws` 双 WS | 网关基于 STOMP 文本协议、或希望媒体层独立扩缩容 | 主 WS 走 STOMP/text；media WS 走原生 binary WebSocket |
| `livekit` / WebRTC | 后续数字人、多人协同、跨网段 | 需要 LiveKit/信令服务集成 |

v1 前端必须同时兼容 `realtime_ws` 与 `ws` 两种返回值：根据 `media_session.created` 中的 `transport` 与 `media_ws_url` 决定如何发送音频，不能硬编码单 WS。

数字人事件：

```text
avatar.state
  idle | listening | thinking | speaking | interrupted | error

avatar.viseme.delta
  口型帧，绑定 media_session_id/run_id/message_id/tts_segment_id/timestamp_ms。

avatar.gesture.delta
  姿态/动作帧，绑定同一媒体时钟。

avatar.interrupted
  barge-in 或取消导致数字人停止当前输出。
```

数字人第一版可以只实现 `avatar.state`；viseme/gesture 作为后续扩展，但命名和时钟必须按上述模型保留。

`media.backpressure` 示例：

```json
{
  "v": "park-media.v1",
  "type": "media.backpressure",
  "media_session_id": "media_001",
  "payload": {
    "track": "audio_in",
    "reason": "server_buffer_high",
    "pause_ms": 200,
    "max_buffer_ms": 1000
  }
}
```

## 16. 资产输入

图片、文件、离线音频不走主 WS。

```text
HTTP upload -> asset_id -> run.create with asset_id
```

上传安全规则：

```text
1. 上传接口必须使用 HTTP 登录态，不接受前端自称 tenant_id/user_id。
2. 服务端限制文件大小、数量、总配额、MIME allowlist 和扩展名。
3. MIME 不能只信任 Content-Type，必须做内容嗅探和魔数校验。
4. 文件落对象存储前后记录 sha256、size、mime、tenant_id、owner_user_id、acl、expires_at。
5. 图片、文档、压缩包等异步做恶意内容扫描；未通过扫描的 asset 不能进入 run。
6. asset_id 只能引用当前租户和当前用户有权限访问的文件。
7. 对象存储访问使用短期 signed URL，日志中不得记录完整签名 URL。
```

多模态 run 示例：

```json
{
  "type": "run.create",
  "conversation_id": "conv_001",
  "payload": {
    "client_message_id": "client_msg_201",
    "input": {
      "kind": "multimodal",
      "text": "看一下这张设备截图有没有异常",
      "assets": [
        {
          "asset_id": "asset_img_001",
          "kind": "image"
        }
      ]
    }
  }
}
```

## 17. 错误码

第一版至少支持：

```text
IDEMPOTENCY_CONFLICT
UNSUPPORTED_COMMAND
AUTH_EXPIRED
AUTH_REVOKED
ORIGIN_NOT_ALLOWED
WS_TICKET_EXPIRED
WS_TICKET_REPLAYED
RATE_LIMITED
PERMISSION_DENIED
CONVERSATION_RUN_CONFLICT
RUN_NOT_FOUND
RUN_ALREADY_TERMINAL
TOOL_TIMEOUT
TOOL_RESULT_TOO_LARGE
JAVA_API_FAILED
JAVA_API_TIMEOUT
PROVIDER_TIMEOUT
PROVIDER_DEGRADED
MEDIA_TOKEN_EXPIRED
MEDIA_TOKEN_FORBIDDEN
MEDIA_FRAME_GAP
MEDIA_CLOCK_SKEW
OPERATION_TICKET_EXPIRED
OPERATION_TICKET_CONFLICTED
OPERATION_APPROVAL_REQUIRED
RESOURCE_LOCKED
PAYLOAD_TOO_LARGE
UNSUPPORTED_MEDIA_TYPE
ASSET_SCAN_FAILED
BACKPRESSURE
VALIDATION_ERROR
INTERNAL_ERROR
```

错误事件示例：

```json
{
  "type": "error",
  "event_id": "evt_error_001",
  "conversation_id": "conv_001",
  "run_id": "run_001",
  "payload": {
    "error_code": "RATE_LIMITED",
    "message": "当前用户并发 run 数已达上限",
    "retryable": true,
    "retry_after_ms": 5000
  }
}
```

限流与背压维度：

```text
connection
  每用户、每租户、每 IP、每 page_instance 的 WS 连接数。

command
  每用户每分钟命令数、run.create 频率、ticket.confirm 频率。

run
  max_active_runs_per_user、max_active_runs_per_conversation、租户级并发。

tool
  每工具 QPS、Java API timeout、单 run 最大 tool_call 数。

media
  单帧大小、上行码率、并发 media_session、ASR 总时长、TTS 下行队列。

delivery
  客户端 ack 滞后、发送队列长度、重放窗口大小。
```

当发送队列过长时，服务端应优先保留 `run.*`、`message.completed`、`operation_ticket.*`、`error` 等状态事件，对高频 `message.delta`、`asr.partial`、`tts.segment` 做合并、降采样或返回 `BACKPRESSURE`。

日志与脱敏要求：

```text
必须记录：
  trace_id、span_id、tenant_id、user_id、conversation_id、run_id、tool_call_id、operation_ticket_id、error_code、latency_ms。

必须脱敏：
  access token、ws_ticket、media_token、signed URL、Cookie、手机号、身份证、门禁卡号、精确定位、原始音频内容。

禁止记录：
  完整 Authorization 头、完整 Cookie、完整对象存储签名 URL、未脱敏的设备控制参数密钥。

LLM 日志：
  prompt、tool result、ASR 文本、用户上传文件摘录要按租户策略采样、脱敏和保留期限处理。
```

## 18. 第一版实现边界

必须实现：

```text
/app/bootstrap
/app/realtime/ws
ws_ticket 或 Cookie + Origin 的 WS 认证
connection_auth_context
conversation.subscribe
conversation.snapshot
run.create
run.cancel
message.delta/completed
tool_call read
operation_ticket simulated flow
ui.intent 白名单
idempotency
DB 终态
Redis checkpoint
基础重连恢复
auth.expiring / auth.revoked / permission.changed
trace_id 和错误码
日志脱敏
```

可以后置：

```text
完整 Redis Stream 回放
真实设备执行
复杂审批策略
完整 WebRTC
数字人
多用户共享会话确认策略
AG-UI adapter
MQ 全量事件化
```

## 19. 参考依据

- [Dify Chat API](https://docs.dify.ai/api-reference/chats/send-chat-message)
- [LibreChat Resumable Streams](https://www.librechat.ai/docs/features/resumable_streams)
- [AG-UI Events](https://docs.ag-ui.com/sdk/java/core/events)
- [Open WebUI Scaling & HA](https://docs.openwebui.com/troubleshooting/multi-replica/)
- [OWASP LLM06: Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)
- [OWASP WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)
- [OWASP JSON Web Token for Java Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [OpenAI Realtime WebRTC](https://developers.openai.com/api/docs/guides/realtime-webrtc)
- [LiveKit Agents](https://docs.livekit.io/agents/)
- [Pipecat WebSocket Transport](https://docs.pipecat.ai/api-reference/client/js/transports/websocket)
- [FunASR 实时语音识别](https://github.com/alibaba-damo-academy/FunASR)
- [CosyVoice 语音合成](https://github.com/FunAudioLLM/CosyVoice)

## 20. 前端-Java 网关-Python AI Runtime 三方集成约束

第一版实时链路是**前端 ↔ Java Product Realtime Gateway ↔ Python AI Runtime** 的三方架构。媒体层和 AI 层不直接对话，所有产品控制语义由 Java 网关持有。

```text
Frontend (Web Audio / WebSocket)
  ↕ 单条 /app/realtime/ws (文本 AppEvent + binary media frame)
Java Product Realtime Gateway
  ↕ 内部控制：gRPC / WebSocket / HTTP chunked（按团队现状选型）
Python AI Runtime (LangGraph + FunASR/CosyVoice)
```

关键约束：

- **控制面与媒体面分离**：前端只认识 Java 网关的 `/app/realtime/ws`；ASR/TTS 模型运行细节（FunASR Nano、CosyVoice2）对前端不可见。
- **Java 网关持有连接、鉴权、幂等、event cursor、operation ticket 权威**。Python AI Runtime 不能持有可直接执行业务控制的用户 token。
- **音频不直接打给 Python**：上行 `audio_in` binary frame 由 Java 网关接收并转发给 ASR 适配器/服务；下行 TTS audio 由 Python 生成后回传 Java 网关，再由网关以 binary frame 下发。Python 侧不暴露 raw WebSocket 给前端。
- **打断是应用层编排**：`media.clear` → Java 网关停止 TTS 队列 + 取消当前 run；barge-in 不经过 LLM 判官（<150-300ms 预算、GPU 满载、行业趋势把打断从 LLM 手里拿走）。
- **ASR final promotion 在 Java 网关侧完成**：服务端按 `transcript_id` 幂等创建 `run.create`，再交给 Python AI Runtime；Python 不应自己决定何时创建 run。
- **工具调用必须经 Java 权限校验**：Python 生成工具意图，Java 校验权限并执行业务查询/控制票创建；Python 不直接调用设备、告警、工单接口。
- **内部传输选型**：Java ↔ Python 可选 gRPC（推荐，强 schema + 流控）、WebSocket（已有基础设施）或 HTTP chunked（简单但流式恢复弱）。选型需在内部架构文档中明确，但不得暴露给前端协议。
- **数字人/Avatar**：v1 可只实现 `avatar.state`；viseme/gesture 由 Python 生成后回传 Java 网关，与 TTS 共享同一相对媒体时钟 `timestamp_ms`。
- **容错与降级**：ASR/TTS 超时或失败时，Java 网关返回 `provider_degraded` 或 `error`，前端无需知道是 FunASR 还是 CosyVoice 异常。

> 本协议是**产品协议**；Java ↔ Python 内部协议另文定义（如 `fun-asr-nano-realtime-ws-contract.md` 描述的是后端适配器与 FunASR Nano 服务之间的协议，前端不感知）。