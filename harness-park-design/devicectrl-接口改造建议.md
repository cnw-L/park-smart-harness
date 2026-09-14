# deviceCtrl 接口问题与改造建议

> 面向后端同事的接口变更说明。背景:AI 助手要把"开空调/控设备"做成自然语言入口。
> 设备控制是**不可逆物理动作**,对接口的安全性要求高于普通 CRUD,故单列此文。  
> **文档联动**：本文档属于 `harness-park-design` 设计文档集。完整索引与阅读顺序见 [README.md](README.md)；关键术语一致性约定见 [术语表与文档联动约定.md](术语表与文档联动约定.md)；消费端治理参见 [后端接口情况与使用指南.md](后端接口情况与使用指南.md)、[工具管理子系统-设计.md](工具管理子系统-设计.md)、[harness落地设计-讨论总结.md](harness落地设计-讨论总结.md)。

## 一句话诉求

给 `POST /common/device/deviceCtrl` 增加(**可选、向后兼容**的)幂等键 `requestId` 与指令回执 `commandId`,并提供按 `commandId` 查指令状态的接口。**不传 `requestId` 的老调用方行为完全不变。**

---

## 一、当前接口现状

```
POST /common/device/deviceCtrl
入参  DeviceControlEvent: { deviceId, pointTypeNo, paramValue, paramStatus,
                            deviceIds[], pointIds[], extraParam, ... }  // 15 字段全可选
返回  RBoolean: { code, msg, data: true | false }                       // 一个裸布尔
```

两个事实:

1. **入参无幂等键 / 请求号** → 后端无法识别"这是重复的同一条指令"。
2. **返回只有布尔** → 无指令编号,动作发出即"匿名",事后无法查询其状态。

---

## 二、问题与后果

### 问题 1:无幂等,重复下发会重复执行

任何客户端(网页后台双击、网络重试、程序崩溃后重试)都可能发两次同一条指令。后端识别不出重复 → **物理动作执行两次**。

- 对**状态型**动作(开/关、设温到 26 度):重复无害(结果还是那个状态)。
- 对**非状态型**动作**有害**:
  - **相对调节**:"调高 2 度" → 实际 +4 度
  - **触发/脉冲型**:"道闸放行""电梯呼梯""设备重启/复位" → 触发两次
  - **扣费/下单型**:扣两次 / 生成两笔

### 问题 2:无回执,动作不可追踪

返回布尔不带 `commandId`,后果:

- **审计/问责**无法回答"是哪条指令、何时、由谁下发的"。
- **崩溃恢复**时无法查询"我刚那条指令到底执行没",只能靠猜。

### 两个具体故障场景

- **故障 A(状态过期 / TOCTOU)**:准备阶段读到空调=关,展示给用户;用户 90 秒后才点确认;期间运维已手动开 → 系统基于**过期事实**下发了一条不该发的指令。
- **故障 B(崩溃窗口)**:下发指令 → 物理动作已发生 → **记账前进程崩溃** → 恢复后不知发没发。重发则可能重复,不发则可能遗漏。

---

## 三、适用范围(决定优先级,可据此判断是否现在改)

本改造主要服务**非状态型动作**与**审计**:

| 场景 | 是否需要本改造 |
|---|---|
| AI 本期只控制 开/关 / 设定值(绝对写) | **可暂不改**。AI 侧用"下发后读回真实状态"即可兜底 |
| AI 本期含 相对调节 / 触发脉冲(道闸·电梯·重启) / 扣费下单 | **必须改**。这些"做两次≠做一次"且无法靠读回区分,后端幂等是唯一安全网 |
| 需要可审计、可复盘每条 AI 控制指令 | **建议改**(至少加 `commandId`) |

> 注:`deviceCtrl` 入参是 `paramValue`(目标值),属"把点位设成某值"的**绝对写**。若后端控制全是绝对写,则多数动作为状态型,优先级可降。真正需要幂等的是上表第二行那几类。

---

## 四、改造建议(加性、向后兼容、opt-in)

**设计原则**:`requestId` 是否传入 = 新旧行为开关。
不传 → 完全保持现有行为(老调用方零影响);传入 → 启用幂等 + 富回执。

### 1) 请求:新增可选字段,原字段一个不删

```jsonc
POST /common/device/deviceCtrl
{
  // ===== 新增(可选) =====
  "requestId": "客户端生成的UUID",       // 幂等键。不传 = 走老逻辑
  "expectedVersion": {                   // 选填,乐观锁(解故障A);见 P2
    "123:AC_ONOFF": "20260613T103000"    // 点位状态版本号或 updateTime
  },

  // ===== 原有字段不变 =====
  "deviceId": 123, "pointTypeNo": "AC_ONOFF", "paramValue": "1",
  "deviceIds": [], "pointIds": []
}
```

### 2) 返回:传了 requestId 时返回富对象(否则仍是老的 RBoolean)

```jsonc
{
  "code": 0, "msg": "",
  "data": {
    "commandId": "cmd-20260613-789",     // 指令编号,可追踪/审计
    "status": "dispatched",              // received|dispatched|applied|partial|failed|rejected
    "duplicated": false,                 // true = 命中幂等、未重复执行
    "results": [                         // 逐目标结果(解决"批量回一个布尔")
      { "deviceId": 123, "pointTypeNo": "AC_ONOFF", "status": "dispatched", "msg": "" }
    ]
  }
}
```

> **重要**:`status` 需区分 `dispatched`(网关已接受)与 `applied`(设备真到位)。SCADA 下发是异步的,别让接口用一个布尔假装"同步完成"。

### 3) 新增接口:按 commandId 查指令状态(解故障 B)

```jsonc
GET /common/device/commandStatus?commandId=cmd-20260613-789
→ { "code": 0, "data": {
     "commandId": "...", "status": "applied",
     "createTime": "...", "finishTime": "...",
     "results": [ { "deviceId": 123, "status": "applied",
                    "stateAfter": { "status": "开", "value": "26" }, "msg": "" } ]
   }}
```

### 4) 服务端行为

1. **幂等**:收到 `requestId` → 先占位(SETNX / 唯一索引)**再**执行;命中已存在 → 返回存储结果(`duplicated:true`),**不重复执行**;并发重复 → 返回"处理中"。TTL 建议 24h。
2. **commandId 生命周期**:`received → dispatched → applied/failed`,落库可查。
3. **(可选)乐观锁**:dispatch 前比对 `expectedVersion` 与当前态,变了 → `status:rejected, reason:STATE_CHANGED` + 回当前态。
4. **批量**:`results[]` 逐目标返回,部分失败时整体 `status:partial`。

---

## 五、优先级

| 级别 | 内容 | 说明 |
|---|---|---|
| **P0**(最小可行) | 入参 `requestId` + 返回 `commandId` + 服务端幂等去重 | 把"匿名不可逆 fire-and-forget"变成"可去重、可指认"。地基 |
| **P1** | `commandStatus` 查询接口;批量逐目标 `results[]` | 闭合崩溃对账与批量可见性 |
| **P2** | `expectedVersion` 乐观锁;请求 schema 收紧(必填约束、去掉 `extraParam` 无类型逃生口) | 进一步收紧 |

---

## 六、兼容性保证

- **不传 `requestId` 的调用方,入参与返回完全不变。**
- 所有新增请求字段均为可选;返回富对象仅在传 `requestId` 时启用。

---

## 七、AI 侧无论如何都会做的(契约边界,供后端参考)

即便后端不改,AI 侧也会:

- 控制后**读回真实状态**(`getDevicePage`)并**对照点位参数字典**(`sycPointParamType` 的 `paramStatuses`)确认到位,**不轻信返回布尔**。
- 自己生成 `requestId`(准备阶段铸造、重试复用),并在适配层维护一份去重台账。

但适配层的去重**只能挡 AI 自己的重发**;**挡不住网页后台等其它客户端的重复下发**——那只有后端幂等(P0)能做到。这是本文 P0 不可替代的根本原因。

---

**文档联动**：本文档属于 `harness-park-design` 设计文档集。完整索引与阅读顺序见 [README.md](README.md)；关键术语一致性约定见 [术语表与文档联动约定.md](术语表与文档联动约定.md)。
