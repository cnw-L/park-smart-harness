# SP-10 Theory Trace（回溯到第一~四篇）

来源：第五篇-SP10-SecuritySupplyChainControl-正式操作规程.md §Theory Trace

---

# 12. Theory Trace

```text
Part I:
GI-03 / GI-05

Part II:
Ch4 §18（Security / Privacy 十类 concern，早于代码完成识别）、
§25（Safety vs Security，领域标准叠加）
Ch9 §20（Secret 禁令与 Rotation）、§24（SSDF / Third-party / SP-09 分工）、
§40-41（Enforcement Point / Input Validation 边界）、§42（SSDF 集成 SDLC）、
§67.6（[MUST][BASELINE] 可信边界执行）
Ch11 §11（Provenance / SLSA v1.2）、§49（Integrity 底线）、§50（Secure
Release 五件）、§51（SBOM 适用）、§56（Deployment 权限）、§57（SoD /
Authority 可追踪）、§86.1-86.2（Build 可追踪 / 可确定 [MUST][BASELINE]）

Part III:
Source / Build / Runtime Mapping（Ch5 Source·Build、Ch3 Runtime 面对应关系：
Enforcement Point 在 Source / Runtime 的落点，Release 权限面在 Build /
Runtime 的映射）

Part IV:
Ch5（Enforcement 在实现期落地）
Ch6（安全验证义务进入 Candidate Evidence）
Ch7（Integrity / Provenance / 权限控制在 Release 期生效）
Ch8（Emergency 安全响应压缩路径）

Journey:
JG-05 新增或升级 Dependency / Toolchain / Config 主线（SP-09 → SP-10）
```

---
