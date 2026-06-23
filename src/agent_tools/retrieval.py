"""知识检索接缝(KnowledgeRetriever)+ 权限口径策略(KnowledgePermissionPolicy)。

防腐:`agent_tools` 只认协议,真 RAG(`assistant_core/rag`)在接线边适配注入(同 BackendClient)。

**注入层落点(RAG 设计 §4.5)**:身份在会话建立时从可信登录态解析,工具把它编译成 Milvus
`field_filters`(键名对齐 `rag/filters.py` 白名单),与语义检索一起执行 → 补 RAG 权限"注入层"洞。

口径(密级档位 / 空标签行为)集中在 `KnowledgePermissionPolicy` 一处,**改常量即可调**,
工具与适配器不动。默认保守(fail-closed),待真口径定了改本类。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Evidence:
    """检索结果(answer-ready)。`insufficient` 非空 = 检索不足的原因(老实回传,不臆造)。"""
    text: str = ""
    citations: list[str] = field(default_factory=list)
    insufficient: str = ""


class KnowledgeRetriever(Protocol):
    async def retrieve(self, query: str, *, field_filters: dict,
                       token: str | None = None) -> Evidence: ...


# ── 权限口径(★唯一该改的地方)──────────────────────────────────────────────────

@dataclass(frozen=True)
class KnowledgePermissionPolicy:
    """知识检索权限口径 —— **改这一处即可调**(密级档位 / 可见范围 / 空标签行为)。

    ★对齐真实语料(2026-06-22 实测 knowledge_chunks):confidential_level 用**英文**枚举
    (internal/public/…),非中文;department_scope/role_scope 当前整库统一为「园区运营」/「admin」
    (无组织级差异、无 `"*"` 公共标);permission_tags 是**来源标签**(应急预案汇报…)非访问控制码。
    故:① 密级档位**中英双写**(兼容);② **不发 permission_tags 过滤**(它不是 ACL 字段,发能力码必全 drop);
    ③ dept/role **默认不 fail-closed**(整库未做组织级差异化,fail-closed 会全 drop)——真组织标签体系
    入库后,把 scope_fail_closed 置 True 即恢复部门/角色隔离。密级隔离现已真生效(匿名看不到 internal)。
    """
    employee_levels: tuple[str, ...] = ("public", "internal", "公开", "内部")
    manager_levels: tuple[str, ...] = ("public", "internal", "confidential", "公开", "内部", "机密")
    anonymous_levels: tuple[str, ...] = ("public", "公开")        # 无身份 = 仅公开(看不到 internal)
    manager_role_markers: tuple[str, ...] = ("管理", "主管", "经理", "负责人", "admin")
    # dept/role 作用域:False=不发(整库未差异化时避免全 drop);True=fail-closed(隔离,需入库打标+"*")。
    scope_fail_closed: bool = False
    emit_permission_tags: bool = False     # permission_tags 当前是来源标签非 ACL → 默认不发(发了必误杀)

    def levels_for(self, principal) -> tuple[str, ...]:
        """密级许可:身份 → 允许看到的密级档位列表。"""
        if principal is None:
            return self.anonymous_levels
        role = getattr(principal, "role", "") or ""
        if any(m in role for m in self.manager_role_markers):
            return self.manager_levels
        return self.employee_levels

    def field_filters(self, principal) -> dict:
        """principal → Milvus `field_filters`(键名一字不差对齐 `rag/filters.py`,否则被静默丢弃=越权)。

        - `confidential_level`:标量 IN 允许档位(始终发,密级 fail-closed)。
        - `department_scope`/`role_scope`:JSON 白名单(compiler 自动补 `"*"` → 本部门/角色 + 公开);
          `scope_fail_closed=False` 时不发这两项(放行未打 scope 的块)。
        - `permission_tags`:用户权限码白名单。
        - `park_id`:园区隔离。
        """
        if principal is None:
            return {"confidential_level": list(self.anonymous_levels)}
        f: dict = {"confidential_level": list(self.levels_for(principal))}
        if self.emit_permission_tags:                  # 默认关:语料 permission_tags 是来源标签非 ACL
            perms = list(getattr(principal, "permissions", ()) or ())
            if perms:
                f["permission_tags"] = perms
        if self.scope_fail_closed:
            dept = getattr(principal, "dept", "") or ""
            role = getattr(principal, "role", "") or ""
            if dept:
                f["department_scope"] = [dept]
            if role:
                f["role_scope"] = [role]
        park = getattr(principal, "park_id", None)
        if park:
            f["park_id"] = park
        return f


# ── Fake(单测 / 无 milvus demo)─────────────────────────────────────────────────

class FakeKnowledgeRetriever:
    """罐装检索:不触 milvus。记录收到的 `field_filters`(供断言注入层),回固定证据。"""

    def __init__(self, evidence: Evidence | None = None) -> None:
        self._ev = evidence
        self.calls: list[dict] = []                 # 记录每次的 field_filters(测注入层)

    async def retrieve(self, query: str, *, field_filters: dict,
                       token: str | None = None) -> Evidence:
        self.calls.append(dict(field_filters))
        if self._ev is not None:
            return self._ev
        return Evidence(
            text=f"(设备维护手册§4.2)关于「{query}」:中央空调夏季设定不低于24℃、每月清洗滤网。",
            citations=["设备维护手册§4.2"])
