# Multimodal OpenAI Deployment Profile

本文件用于在根 `SKILL_zh_cn.md` 移除具体部署细节后，继续保留 Multimodal Flow 当前的 OpenAI 模型绑定。它有意保持为小型部署专属文档，不尝试建立通用 Multimodal Runtime 抽象。

Multimodal 架构、工作模式、Observation Firewall、视觉 checkpoint 与 handoff 行为继续以 [`multimodal-flow_zh_cn.md`](multimodal-flow_zh_cn.md) 为规范来源。

## 当前绑定

- **Decision Agent**：当前高级父模型。
- **Primary Observation Agent**：`gpt-5.6-luna`；承担大量图片、视频帧、Computer Use Observation 或其他实质性高体量分析时使用 `reasoning_effort=xhigh`。
- **Optional Primary Output Agent**：`gpt-5.6-luna`；实质性长输出与其他高体量物化使用 `reasoning_effort=xhigh`。
- Primary Observation 与 Optional Primary Output 是不同职责和不同 Session Affinity；即使两者都绑定到 Luna，也不默认合并各自的高体量上下文。

Coding Flow 的 Single-Session Coding Mode 只改变 Coding 的角色映射，不削弱 Multimodal Observation ownership，也不意味着 Observation 与 Output 应共享同一 Session。

## 部署约束

- 不得把本 Profile 要求使用 Luna 的 Multimodal 角色静默替换为其他模型。
- 若需要独立 Luna 角色但无法确认 `gpt-5.6-luna` 身份、无法显式选择该模型，或宿主不能满足当前 dispatch 所要求的 reasoning-effort 档位，则停止对应实质性 Multimodal 工作并简短报告 capability block。
- 纯只读、严格有界的诊断或 Observation，在能够确认 Luna 身份但宿主无法设置 reasoning effort 时可以继续；不得因此把复杂高体量 Observation/物化回退给高级父模型，也不得把 Profile 要求 `xhigh` 的工作静默交给更轻量档位。

本 Profile 只保留当前部署行为，不声明对其他 Code Agent 产品或模型族具有可移植性。未来 Multimodal 的跨产品工作应以真实测试为基础，而不是从 Coding Runtime 架构推断。
