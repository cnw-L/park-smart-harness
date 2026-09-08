# 数字人研究库

> 实时语音 / 数字人系统的持续研究工作区。
> 配套核心读物:[`文档/数字人系统_深度学习文档.md`](文档/数字人系统_深度学习文档.md)(完整心智地图 + 易错点速查)。
> **★ 项目级权威综合**已上移至仓库根目录:语音外壳设计已并入 [`项目设计文档.md`](../项目设计文档.md) §11(单 WS 多路复用/打断/状态机/弱网/语音↔大脑对接)、落地路线并入 [`项目落地文档.md`](../项目落地文档.md) Phase 5。本工作区承载语音研究细节与推演。

---

## 目录结构

```
数字人研究/
├── README.md              ← 本文件:总索引
├── 腾讯V6项目收敛/         ← ★与腾讯需求对齐的项目收敛包(架构地图+测试+兜底)
├── 文档/                   ← 研究读物、规范、心智地图
│   └── 数字人系统_深度学习文档.md
├── 笔记/                   ← 自己的研究笔记 / 源码阅读结论 / 对照实验
└── 开源项目/               ← clone 的开源底座(浅克隆 --depth 1)
    ├── OpenAvatarChat/    ★ 主底座
    ├── LiveTalking/         形象推流专项
    ├── FunSpeech/           语音微服务参考
    ├── FireRedChat/         双工/打断参考
    └── DH_live/             轻量/移动端
```

---

## 开源项目速查表

| 项目 | 仓库 | 定位 | 重点研究什么 | 对照文档章节 |
|------|------|------|-------------|------------|
| **OpenAvatarChat** ★ | github.com/HumanAIGC-Engineering/OpenAvatarChat | 主底座,技术栈=本文档选型(SenseVoice+CosyVoice+silero+MuseTalk),模块化+双工打断已实现 | 整体架构、handler 插拔机制、**双工到底依赖 WebRTC 还是纯逻辑**(待源码验证) | §8 模块化、§15 开源底座 |
| **LiveTalking** | github.com/lipku/LiveTalking | 形象推流专项,MuseTalk 工程化+WebRTC 推流最成熟 | inferfps/finalfps≥25 怎么保证、batch_size 调度 | §12 形象工程、§13 并发 |
| **FunSpeech** | github.com/zaigie/FunSpeech | 语音微服务参考,FunASR+CosyVoice 整合,解决依赖地狱 | gateway 的句子状态机、服务拆分 | §3/§4 上下行、§8 模块化 |
| **FireRedChat** | github.com/FireRedTeam/FireRedChat | 双工/打断参考,pVAD 设计先进,开源了 pVAD/turn-detector 模型 | pVAD 因果卷积流式推理、误打断三层防御 | §5 打断、§9 误打断判定 |
| **DH_live** | github.com/kleinlee/DH_live | 轻量/移动端,2.5D | `server_realtime.py` 有完整 vad-asr-llm-tts 全流程 | §4 下行、§12.5 Avatar 版图 |

---

## 腾讯 V6 项目收敛包(2026-06-22)

> 以腾讯《需求说明书 V6.0》全量架构为骨架,把本研究(语音/数字人外壳)与 `harness-park-design`(大脑)归位,重点补齐**测试**与**兜底/降级**两个空白。入口:[`腾讯V6项目收敛/README.md`](腾讯V6项目收敛/README.md)。

- [00 项目总纲·全量架构与能力地图](腾讯V6项目收敛/00_项目总纲_全量架构与能力地图.md) — 五层骨架 + 资产归位 + 能力对照 + 目录结构。
- [01 测试方案·验收指标对齐](腾讯V6项目收敛/01_测试方案_验收指标对齐.md) — 附录 A 逐条 → 可执行测试。
- [02 兜底与降级方案](腾讯V6项目收敛/02_兜底与降级方案.md) — 四级降级体系。

## 笔记索引

> 阅读顺序:**设计文档**(结论)→ 研究主线/全解(依据)→ 讨论纪要/理论(过程)。

- ⭐ **[园区数字人·语音管线设计.md](笔记/园区数字人·语音管线设计.md)** — **最终设计**(2026-06-18):语音管线=媒体侧薄胶水接既有协议;选型反转(不用Pipecat/LiveKit,FunASR/CosyVoice原生);块①上行/②下行/③打断逐块设计+字段映射+可选层。**落地看它。**
- **[数字人语音交互协议方案归纳.md](笔记/数字人语音交互协议方案归纳.md)** — **协议选型结论**(2026-07-01):单WS/双WS/WS+WebRTC 对比 + 形象分水岭 + 阶段推进建议。**协议决策看它。**
- **[单WebSocket多路复用设计要点.md](笔记/单WebSocket多路复用设计要点.md)** — **单 WS 落地设计**(2026-07-01):帧协议、并发模型、上下行链路、打断、状态机、错误处理。**实现单 WS 看它。**
- **[媒体子系统契约设计方法论.md](笔记/媒体子系统契约设计方法论.md)** — **契约设计方法论**(2026-07-01):基于行业生产级实践+本项目协议提炼出的分层解耦、信号语义、幂等、错误契约、可观测、版本演进方法论。**契约设计决策看它。**
- [园区数字人落地方案.md](笔记/园区数字人落地方案.md) — ⚠️已被上文取代(假设Pipecat=编排底座的旧方案,留作历史)。
- [讨论纪要·上行边界(PCM-上传-VAD).md](笔记/讨论纪要·上行边界(PCM-上传-VAD).md) — **两人讨论结论**(§1-3 上行输入侧):核心原则"AI 边界=输入合同执行点";PCM/上传/VAD 多层过滤墙逐条带行号;园区落地三个待补洞。
- [OpenAvatarChat项目全解.md](笔记/OpenAvatarChat项目全解.md) — **OAC 源码级全解**(v0.6.0):启动链/动态加载/三大抽象(Handler·Stream·Signal)/pump线程模型/完整pipeline逐站/打断真相/配置变体/设计决策取舍。想懂 OAC 看它。
- [研究主线.md](笔记/研究主线.md) — **文档理论 × 开源代码逐条核对**(✅印证/⚠️分歧/❌缺口),含 5主线实现矩阵 + 待读清单。研究入口。
- [语音事件与harness-run_loop对接.md](笔记/语音事件与harness-run_loop对接.md) — **语音流↔大脑对接**(2026-07-07):语音连续流(非轮次)与 harness `run_loop` 轮次模型的对接设计。
- [语音交互协议细化-分包重传唇形同步VAD打断.md](笔记/语音交互协议细化-分包重传唇形同步VAD打断.md) — **协议细化**(2026-07-07):音频流分包、重传、唇形同步、VAD 与打断。
- [语音交互弱网重连降级与状态机形式化定义.md](笔记/语音交互弱网重连降级与状态机形式化定义.md) — **弱网与状态机**(2026-07-07):弱网重连、降级策略与状态机形式化定义。

## 研究主线(文档骨架)

```
① 上行(听懂)  音频流 → VAD切句 → 2pass(流式partial+整句final) → 文本   §3
② 下行(开口)  文本 → LLM流式 → 句子聚合 → 流式TTS → 排期播放          §4
③ 打断(双工)  前端清播放 + 后端cancel任务 + 信号走独立通道            §5
④ 状态机(焊死) 每状态各模块工作态 + 转换时清残留                      §6
⑤ 形象(可选)  TTS音频分叉 → 口型同步 → 音视频对齐推流                §12
传输层:WebSocket / WebRTC(§7)    生产深水区:误打断/VAD/异常/并发(§9-13)
```

## 与本项目(smart_park_assistant)的对照

- **上行已落地**:dual 模式 Paraformer(6011 流式 partial)+ SenseVoice(6012 整句 final)= 文档 §3.4 的 2pass。
- **下行 TTS 已落地**:CosyVoice2-0.5B @ 90 GPU1(6014)= 文档选型表的"首包 150ms 流式 TTS"。
- **尚缺/待研究**:下行后半段(句子聚合 + 文本清洗 + 排期播放)、双工打断、状态机异常处理、形象工程。

---

## 与 harness-park-design 的联动

数字人语音外壳只负责**实时语音/形象的输入输出与打断**,大脑(意图理解、任务编排、设备控制、护栏、记忆、会话持久化)全部在 `harness-park-design` 设计文档集中定义。阅读顺序:

1. [`harness-park-design/README.md`](../harness-park-design/README.md) — 大脑侧文档总索引。
2. [`harness-park-design/总纲-理论到落地到细节.md`](../harness-park-design/总纲-理论到落地到细节.md) — 从理论到落地的单一主线。
3. [`harness-park-design/术语表与文档联动约定.md`](../harness-park-design/术语表与文档联动约定.md) — 跨 `digital-human` 与 `harness-park-design` 的术语一致性约定。

语音外壳与大脑之间的接口约定(单 WS 多路复用、信号/命令分层、幂等、打断语义)见 [`笔记/媒体子系统契约设计方法论.md`](笔记/媒体子系统契约设计方法论.md)。

---

## 待验证的关键空白(落地前必须亲自确认)

1. **OpenAvatarChat 的双工依赖 WebRTC 还是纯逻辑?** → 决定纯 WebSocket 能否复刻它的双工。读 OpenAvatarChat 源码确认。
2. 误打断数据(Ten 78% / FireRedChat 10%)来自论文自评,需谨慎;但"有目标说话人识别才能压低误打断"的定性结论可靠。
3. CosyVoice2 150ms / MuseTalk 30fps 是理想硬件标称,实际因硬件/负载而异。

---

## Submodule 状态(重要)

| 仓库 | submodule | 是否已拉 | 说明 |
|------|-----------|---------|------|
| OpenAvatarChat | 上游模型仓(CosyVoice / MuseTalk / silero-vad / LAM / smart-turn / 前端 WebUI) | **未拉** | 自身架构代码全在主仓 `src/handlers/`,研究架构无需 submodule;要实际跑起来才需补拉 |
| FireRedChat | `agents` / `agents-playground` | **已拉** | 否则主仓是空壳。发现:**FireRedChat 基于 LiveKit**(`livekit-agents`+`fireredchat-plugins`),pVAD 在 `agents/fireredchat-plugins` |

补拉 OpenAvatarChat submodule(需要跑时):
```
cd 开源项目/OpenAvatarChat && git submodule update --init --depth 1 <path>
```

### 已验证的事实(source-grounded)
- **OpenAvatarChat 的 client 传输层可插拔**:`src/handlers/client/` 同时有 `rtc_client`、`ws_client`、`ws_lam_client` → 印证文档 §8.3"通信模块可插拔",且 WS 实现确实存在(回应"纯 WebSocket 能否复刻双工"的空白,待进一步读 ws_client 确认双工细节)。
- handler 全景(主仓内):asr/sensevoice · tts/cosyvoice+edgetts · vad/silerovad+smart_turn_eou · llm/openai_compatible+qwen_omni+dify+semantic_turn_detector · avatar/musetalk+liteavatar+lam+flashhead · manager/interrupt。

## 维护约定

- 开源项目是浅克隆(`--depth 1`)。需要完整历史:`git fetch --unshallow`。
- 源码阅读的结论写进 `笔记/`,一个主题一个文件,文件名见名知意。
- 本 README 是入口索引,新增资料 / 新克隆项目都在这里登记一行。
