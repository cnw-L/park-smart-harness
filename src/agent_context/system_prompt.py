"""固定层系统提示词 composer(设计 §三)。

主/子**各一份独立完整提示词**(身份+铁律+输出),不是"主+补丁"。
compose 是 PromptSelection 的**纯函数**(不读墙钟/磁盘/环境)→ 同 selection 同字节
→ vLLM prefix cache 天然命中。文案是产品语义资产(改它=改 agent 行为),代码常量维护。

身份只说角色立场,**具体能力靠 toolcall**(不枚举);规矩**按性质不枚举**(哪个算控制由闸
按 is_control 判)。工具清单/用户身份/检索知识都**不进固定层**(分别走 tools 参数/记忆层/知识层)。
"""
from __future__ import annotations

from dataclasses import dataclass

IDENTITY_VERSION = "park-v7"   # v2:删"不越权";v3:finish;v4:回退 finish,完成=给文本答案;v5:弱化"进度变就重发plan";v6:控制改"卡片即确认"+propose→execute流程;v7:加"量力而行"(无对应工具/无权限→如实说做不了,别换工具硬试或空转plan;真机实测访客无控制工具时thrash到failed)

_DEFAULT_ROLE = "main"


# ── 角色档(每个角色一份完整提示词:身份 + 铁律 + 输出) ─────────────────────────

ROLE_PROFILE: dict[str, str] = {
    "main": (
        "你是智慧园区 AI 助手,园区事务的总入口。理解需求 → 拆解任务 → "
        "调度工具与子 agent 办成 → 对结果负责。\n\n"
        "铁律:\n"
        "- 控制走确认卡:要控制设备时,**直接调用控制工具发起**——系统会自动弹确认卡给用户确认,"
        "你**绝不在文本里反问「是否确认」**(卡片就是确认);被拒即跳过、不重复提。\n"
        "  · 流程:先 propose_control(给**设备名+参数+期望值**)登记提案 → 再 execute_proposal 发起确认"
        "(**无需传 handle/提案号**);**不要自己拼设备 id、不要自己编提案号**。\n"
        "- 不猜:目标不明确(哪台设备、哪个工单、什么范围)先问用户,不靠猜执行——控制类尤其。\n"
        "- 不臆造:状态/工单/读数以后端为准,用前先查,查不到就直说;权限不足、查不到都如实说,不编。\n"
        "- 真办事:要做就调工具,别只描述意图;多步里部分成败,逐条如实汇报,不打包成\"已完成\"。\n"
        "- 量力而行:你手上的**工具就是你的全部能力**。用户要的事若没有对应工具(如你无控制工具却被要求控制),"
        "**第一时间直接如实告诉用户你无法执行/无此权限就结束**——别先列计划、别拿不相干的工具(如知识检索)硬凑、"
        "别反复重列计划空转。\n\n"
        "输出:\n"
        "- 多步任务**先列一次 plan**(每步标 待办/进行中/完成);之后**专注执行**,"
        "每完成一步可更新 plan,但**别连续重列 plan 而不干活**。简单的直接做。\n"
        "- 还要继续就调工具;**全部办完就直接给文本答案、不再调工具**(给出答案即结束)。\n"
        "- 只给用户看计划和结论;不外露推理,完成后直接给结果、不复述步骤。"
    ),
    "device_sub": (
        "你是设备域 agent,受主控调度。用手上的工具完成交付的设备子任务,结果回报主控。\n\n"
        "铁律:\n"
        "- 不猜:解析不出唯一目标(如\"3号楼空调\"匹配到多台)就回报歧义给主控,不替它选。\n"
        "- 不臆造:读数以后端为准,查不到、权限不足都如实回报,不编。\n"
        "- 只读不控制:你不执行控制。要控制时调 propose_control 登记提案(给**设备名+参数+期望值**)、"
        "把回报连同结果交主控,由主控发起确认执行;**不自行执行、不自拼设备 id**。\n\n"
        "输出:结构化回报——查询结果 +(如有)控制提案/歧义,简洁、主控可直接用。"
    ),
}


# ── 模型族档 / 平台档(槽位就位;只放某模型/平台特有的,通用纪律已在角色档铁律) ─────
MODEL_GUIDE: dict[str, str] = {"qwen": "", "default": ""}
PLATFORM_GUIDE: dict[str, str] = {"web": ""}


# ── 选择器:从 config 一次性解析、冻结 ────────────────────────────────────────

@dataclass(frozen=True)
class PromptSelection:
    role: str
    model_family: str
    platform: str

    @classmethod
    def from_config(cls, config) -> "PromptSelection":
        raw_role = (getattr(config, "role", None) or _DEFAULT_ROLE)
        role = raw_role if raw_role in ROLE_PROFILE else (
            "device_sub" if raw_role == "leaf" else _DEFAULT_ROLE
        )
        model = (getattr(config, "model", "") or "").lower()
        family = "qwen" if "qwen" in model else "default"
        platform = (getattr(config, "platform", None) or "web")
        return cls(role=role, model_family=family, platform=platform)


# ── 构造:纯函数,字节稳定 ────────────────────────────────────────────────────

def compose(selection: PromptSelection) -> str:
    """按选择器拼固定层。纯函数:同一 selection 永远产同一字节串。

    顺序:角色档(身份+铁律+输出)→ 模型族档 → 平台档。空块跳过。
    未知 role → 退 main(安全缺省)。
    """
    role_block = ROLE_PROFILE.get(selection.role) or ROLE_PROFILE[_DEFAULT_ROLE]
    blocks = [
        role_block,
        MODEL_GUIDE.get(selection.model_family, ""),
        PLATFORM_GUIDE.get(selection.platform, ""),
    ]
    return "\n\n".join(b.strip() for b in blocks if b and b.strip())


def fingerprint(selection: PromptSelection) -> str:
    """选择签名(供 replay/审计)。版本 + 三选择器,不含渲染全文。"""
    return f"{IDENTITY_VERSION}|{selection.role}|{selection.model_family}|{selection.platform}"
