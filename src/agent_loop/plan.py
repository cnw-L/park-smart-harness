from __future__ import annotations
from dataclasses import dataclass, field
from .tools import LoopTool, ToolContext, ToolResult
from .messages import Message


@dataclass
class PlanItem:
    id: str
    content: str                  # 这步的目标(模型可读的自然语言)
    status: str                   # todo|doing|done
    result: str | None = None     # 这步拿到什么(人话短句,记录完成情况;中圈渲染用)
    spec: dict | None = None      # 结构化规格(grounding 结果/参数等)。
    #   §2.2:status + spec,结构化、保真不压缩。
    #   §1.3:plan 保持精瘦——大产物走归一化结果/外部句柄,不嵌进快照(spec 里放引用,不放大 blob)。
    #   :167:并串关系不进 plan(靠循环动态),故 spec 不含 depends_on。
    #   瘦引擎:引擎不解释 spec,只保真存储 + 拼回上下文;由域(grounder)填充。


@dataclass
class PlanState:
    items: list[PlanItem] = field(default_factory=list)

    def replace(self, raw_items: list[dict]) -> None:
        # 畸形容错(qwen 抖):缺 id/content 跳过该 item;缺 status 默认 todo——别让一个畸形项崩整轮。
        items: list[PlanItem] = []
        for i in raw_items:
            if not isinstance(i, dict) or "id" not in i or "content" not in i:
                continue
            items.append(PlanItem(
                id=i["id"], content=i["content"],
                status=i.get("status", "todo"),
                result=i.get("result"),
                spec=i.get("spec"),
            ))
        self.items = items

    def render(self) -> str:
        # 注:这是**内圈桩**的渲染(§2.2 spec 保真,渲 spec dict)。生产/中圈用
        # `agent_context.plan_view.render_plan` 渲人话(content+status+result,不 dump spec)。
        # 两者分工:桩供 agent_loop 独立测试,真组装器在中圈。
        if not self.items:
            return ""
        lines = []
        for i in self.items:
            line = f"- [{i.status}] {i.content}"
            if i.spec:                      # 保真渲染结构化 spec(不压缩);无 spec 不产生噪声
                line += f"  spec={i.spec}"
            lines.append(line)
        return "当前计划(plan):\n" + "\n".join(lines)


def derive_plan(messages: list[Message]) -> PlanState:
    """从消息日志派生当前 plan（Claude TodoWrite 式：取最近一条 plan 工具调用的全量快照）。

    plan 工具是全量覆盖，故最新即当前；无调用 → 空 PlanState。
    仅读取 assistant 消息的 tool_call arguments（非 tool 结果消息）。
    arguments 缺 items 字段的 plan 调用视为畸形，跳过继续向前扫描。
    """
    for m in reversed(messages):
        if m.role == "assistant":
            # 同一轮内也取最后一条 plan 调用(与 loop 正向执行的 last-wins 一致)
            for tc in reversed(m.tool_calls):
                if tc.name == "plan" and isinstance(tc.arguments, dict) and "items" in tc.arguments:
                    ps = PlanState()
                    ps.replace(tc.arguments["items"])   # 复用覆盖式 replace
                    return ps
    return PlanState()


def make_plan_tool(state: PlanState) -> LoopTool:
    async def handler(args: dict, ctx: ToolContext) -> ToolResult:
        state.replace(args["items"])
        return ToolResult(ok=True, content="plan updated")

    return LoopTool(
        name="plan",
        description=(
            "提交一份全量计划快照(覆盖式)。每步含 id/content/status,"
            "并可带 spec:该步的结构化规格(如已 grounding 的设备/参数等)。"
            "大产物(完整候选集、长文本)走外部句柄,不要嵌进 spec。"
            "并行/串行不在此声明——并行=一轮发多个工具调用,串行=按需分步。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "content": {"type": "string", "description": "这步要达成什么"},
                            "status": {"type": "string", "enum": ["todo", "doing", "done"]},
                            "result": {
                                "type": "string",
                                "description": "可选:这步拿到什么(人话短句,如\"26℃,偏高\"/\"已下发待确认\")",
                            },
                            "spec": {
                                "type": "object",
                                "description": "可选:该步的结构化规格(grounding 结果/参数);大产物走外部句柄",
                            },
                        },
                        "required": ["id", "content", "status"],
                    },
                }
            },
            "required": ["items"],
        },
        handler=handler,
    )
