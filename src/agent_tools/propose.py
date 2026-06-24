"""`propose_control` 叶子工具 —— **grounding 闸**(三道闸①:可不可控 + 范围 + 可逆性)。

**is_control=False**(grounding 只查权威字典 `sycPointParamType` + 登记提案,不碰后端写)——故能进
**只读子 agent**。真不可逆执行在主会话 `execute_proposal`(走确认闸)。

铁律:**LLM 只产意图,规则查字典解析、不编 id/值**。模型从 `device_status` 候选抬来设备坐标
(point_type_id/device_id),给人话 param/value;`ground_control` 校验 isCtrl/范围、解析 paramValue、
分可逆性;**不可控/越界/不可逆当场拒**(理由回模型),只把合规的存成 grounded 提案。
"""
from __future__ import annotations

from agent_loop.tools import LoopTool, ToolContext, ToolResult

from .backend import BackendClient, BackendError
from .grounding import Grounded, Intent, Rejection, ground_control
from .proposal import ControlProposal, ProposalStore


def make_propose_control_tool(store: ProposalStore, backend: BackendClient,
                              reversibility_map: dict | None = None) -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        token = getattr(getattr(ctx, "principal", None), "token", None)
        pt_id = str(args.get("point_type_id", ""))
        dev_id = str(args.get("device_id", ""))
        pt_no = str(args.get("point_type_no", ""))
        pid = str(args.get("point_id", ""))
        sys_no = str(args.get("system_no", ""))
        target = str(args.get("target", "")) or str(args.get("device", ""))
        # ★免 id 抬:只给设备名(device)时,内部查 device_status 解析精确坐标——模型不必复制长 id
        # (这是控制最易出错的一步:qwen 抄不对 deviceId/pointTypeId → grounding 反复失败)。
        if not pt_id and target:
            try:
                hits = await backend.device_status(name=target, token=token)
            except BackendError as exc:
                # ★绝不把**系统/认证/网络**失败说成"设备名解析失败"——否则模型让用户反复换设备名(换名也没用)。
                # device_status 的 BackendError 一律是后端层故障(token 失效/连不通/RuoYi 业务码),非名字问题。
                return ToolResult(ok=False, content="", error=(
                    f"控制提案登记失败:后端设备查询出错(code={exc.code}:{exc})。"
                    f"这是**系统/认证/网络**问题(常见为 AI 服务的后端 token 失效),**不是设备名问题**——"
                    f"请直接告知用户:暂时无法连接设备后端、需检查/更新 token 与后端连通,"
                    f"**不要让用户改用更精确的设备名**(换名无法解决)。"))
            if not hits:
                # 后端正常但确实没匹配到 → 这才是真正的"名字问题",此时让模型请用户给准确名/编号才合理
                return ToolResult(ok=False, content="", error=(
                    f"未找到名为「{target}」的设备(后端连接正常,但无此设备)。"
                    f"请用户确认设备名或编号;可先查设备运行状态列出可用设备。"))
            if len(hits) > 1:
                # ★歧义硬闸:名字匹配到多台(如"空调机组"→106/101/107…)→ **绝不替用户选第一台**。
                #   控制必须唯一目标,否则会控错设备。仅当用户给的是某台精确全名才放行。
                exact = [h for h in hits if (h.name or "") == target]
                if len(exact) == 1:
                    hits = exact
                else:
                    cand = "、".join(f"{h.name}({h.status})" for h in hits[:12] if h.name)
                    return ToolResult(ok=False, content="", error=(
                        f"「{target}」匹配到 {len(hits)} 台设备,控制必须唯一目标、**绝不替用户选**。"
                        f"**请把下面候选完整列给用户,并明确告诉用户怎么回复**——回设备编号即可(如「空调机组101」)。"
                        f"候选清单:{cand}"))
            h0 = hits[0]
            pt_id = pt_id or h0.point_type_id
            dev_id = dev_id or h0.device_id
            pt_no = pt_no or h0.point_type_no
            pid = pid or h0.point_id
        intent = Intent(point_type_id=pt_id, point_type_no=pt_no, device_id=dev_id,
                        point_id=pid, system_no=sys_no,
                        param=str(args.get("param", "")), value=str(args.get("value", "")))
        result = await ground_control(intent, backend=backend,
                                      reversibility_map=reversibility_map, token=token)
        if isinstance(result, Rejection):
            return ToolResult(ok=False, content="", error=f"控制提案被拒:{result.reason}")

        g: Grounded = result
        # target 优先用上面解析好的设备名(device/target);都没有则退到点类型编码(Grounded 无 point_type_name)
        target = target or g.point_type_no or "目标设备"
        human = f"对「{target}」{g.param_type_name}={g.param_value}（{g.reversibility}）"
        handle = store.put(ControlProposal(
            target=target, action="deviceCtrl", params=g.payload(),
            human=human, reversibility=g.reversibility, token=token or ""))
        # ★handle 不进模型可见文本(M5:模型不碰治理对象)。execute_proposal 自动取最近一条提案,
        #   无需 handle round-trip——这里只给人话确认,不暴露/不要求复制 handle。
        return ToolResult(ok=True, content=(
            f"控制提案已登记（{human}）。"
            f"主控直接调用 execute_proposal 发起确认即可(**无需传 handle/提案号**,系统自动取最近一条),"
            f"不要自己下发控制。"))

    return LoopTool(
        name="propose_control",
        description=(
            "登记一个设备控制提案(只登记、不执行;系统查权威字典校验可控性/范围/可逆性,不合规当场拒)。"
            "★最简用法:只给 **device(设备名,如「空调机组106」)+ param(参数名,如「温度」「开关」)+ "
            "value(如「24」「开」)**——系统会自动解析设备坐标(deviceId/pointTypeId),**你不必抄长 id**。"
            "返回 handle,主控凭 handle 确认执行。(若你手头已有 device_status 的坐标,也可直接传 point_type_id 等。)"),
        parameters={
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "设备名(推荐),如 空调机组106;系统据此解析坐标"},
                "param": {"type": "string", "description": "要控的参数名,如 温度/温度控制/开关"},
                "value": {"type": "string", "description": "期望值,如 24/开"},
                "target": {"type": "string", "description": "目标设备人话名(等同 device)"},
                "point_type_id": {"type": "string", "description": "点位类型id(可选;给了 device 就不必)"},
                "point_type_no": {"type": "string"},
                "device_id": {"type": "string", "description": "设备id(可选)"},
                "point_id": {"type": "string"},
                "system_no": {"type": "string"},
            },
            "required": ["param", "value"],
        },
        handler=handler,
        is_control=False,           # grounding=只读 → 可进只读子 agent;真执行在 execute_proposal
    )
