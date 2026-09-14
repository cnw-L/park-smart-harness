# Step 2 · 兜底设计(超时 + fallback_policy)

> 用途:Step 2 落地前的设计与决策文档——**先定方案,不写代码**。
> 目标:让"工具调用超时/失败 → 有降级、≤3s 触发、不静默"成立,对齐腾讯 6.2(降级覆盖 100%、切换 ≤3s、降级主动告知)+ 行业 graceful degradation。
> 涉及真实代码:`agent_loop/dispatch.py`、`agent_loop/tools.py`、`agent_tools/catalog.py`、`agent_tools/composition.py`。**本文只设计,改不改、怎么改你定。**
> 日期 2026-06-23。

---

## 0. 三块组成

1. **超时**:工具调用加硬超时,超时即当失败 → is_error 回灌。
2. **fallback_policy**:每个工具声明降级路径(重试/跳过/降级 + 文案)。
3. **is_error 回灌**:已有(失败结果标 is_error,模型下一轮看到自然重规划)——无需改。

---

## 1. 超时设计

### 1.1 加在哪
`SequentialToolExecutor.execute_one`(dispatch.py)里,把 handler 调用包一层 `asyncio.wait_for`:
```
正常: result = await tool.handler(args, ctx)
改为: result = await asyncio.wait_for(tool.handler(args, ctx), timeout=超时值)
      超时 → 归一化为 disposition="failed" + 消息 "[timeout>Ns]"(与现有异常→failed 同路径)
```
**加法式**:不设超时值的工具走原路径,**16 条现有测试不受影响**。

### 1.2 超时值:不能一刀切(★决策点 1)

各类工具的合理耗时差很多,建议**分类设**(默认值待你拍):

| 工具类 | 性质 | 建议默认超时 | 说明 |
|---|---|---|---|
| 设备/运行/生活**查询** | 读后端一跳 | **3s** | 对齐腾讯"单次≤3s 触发降级" |
| 知识检索(RAG) | 向量库+重排多步 | **5s** | 步骤多;若严格守 3s 需在方案说明 |
| 执行工具(控制) | 下发+读回对账,真实设备往返 | **8–10s** | **超时不静默**:必须告知"未确认是否生效",走读回复核 |
| 子 agent(如设施) | 内部还跑一圈模型 | **15s** | 内部多轮,放宽 |

> 腾讯的"≤3s"是**触发降级的阈值**,主要针对查询类用户体验。控制/子 agent 客观需要更久——这点要在技术方案里写清"分级超时"理由,而不是硬套 3s。

### 1.3 超时值放哪
- `LoopTool` 加字段 `timeout_s: float | None = None`(引擎契约,执行器认它);
- `ToolSpec`(catalog)也加 `timeout_s`,在 `catalog.to_registry()` 桥接时传进 `LoopTool`;
- `composition.py` 给 7 个工具按 §1.2 分别设值。

---

## 2. fallback_policy 设计

### 2.1 字段(加在 `ToolSpec`)
```
@dataclass(frozen=True)
class FallbackPolicy:
    mode: str        # "retry_once" | "skip" | "degrade"
    degrade_to: str = ""   # 降级去向,如 "食堂大屏静态数据" / "原停车App跳转"
    user_msg: str = ""     # 给用户的话:降级了什么 + 还能用什么
```
`ToolSpec` 加 `fallback_policy: FallbackPolicy | None = None`。

### 2.2 三档怎么选(★决策点 2:谁决定走哪档)
- **retry_once**:瞬时抖动重试一次——**只允许只读/幂等工具**(控制类绝不自动重试,防双发);
- **skip**:非关键步,跳过——**模型看 is_error 自己决定**(引擎不强制);
- **degrade**:能力不可用,走 `degrade_to` + 报 `user_msg`。

建议:**retry_once 由引擎自动(仅只读)**;**skip 交模型**(is_error 回灌);**degrade 由引擎按 policy 触发并回文案**。

### 2.3 控制类红线
执行工具的 fallback **必须非静默**:失败/超时 → 明确告知"未确认是否生效",绝不假装完成。`user_msg` 必填。

---

## 3. 注册校验:软 or 硬(★决策点 3)

设计原话是"未填 fallback_policy 不许注册"。但**现有 composition 一个都没填,直接硬卡会让现有代码起不来**。建议**分两步**:
- **2a(先做)**:加字段 + 给 composition 7 个工具填上 + 注册时**仅软告警**(缺失打 log,不 raise);
- **2b(后做)**:对 `is_control` 工具**硬要求**有 `fallback_policy`(集合小、可控、能填全),其余保持软告警。

这样不破现有启动,又把红线(控制类必须有降级)逐步焊死。

---

## 4. 落完的收益 + 测试闭环

- 落完 2,**engine 套就能补上唯一缺的那条分支——"超时降级"**(`cases.yaml` ⑤⑥ 那两条降级用例从"占位"变"真测"):假模型让工具超时 → 断言降级生效、文案出现、控制类不静默。
- 即:Step 2 做完 → 回 `test_engine.py` 加 2 条超时/降级测试 → 引擎分支才算 100% 全覆盖。

---

## 5. 要你拍板的(就 3 点)

1. **超时值**:接受 §1.2 的分级默认(查询3s/RAG5s/控制8-10s/子agent15s)吗?还是另定。
2. **三档归属**:retry_once 仅只读自动、skip 交模型、degrade 引擎触发——这个分工 OK 吗?
3. **注册校验**:走"2a 软告警 → 2b 控制类硬卡"的两步,还是一步到位硬卡(需同时改 composition 填全)?

这 3 点定了,我就能出**精确补丁**(改哪个文件哪几行 + 配套测试),你 review 后合进 src。
