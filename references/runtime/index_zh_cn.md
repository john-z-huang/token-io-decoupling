# Coding Runtime 注册表

本注册表列出已经登记 Host Adapter 与 Model Profile 映射的具体 Coding 部署。它属于部署元数据，不是 Runtime 无关的 Coding 角色架构。

只有 Coding Flow 通过 [`../coding/runtime_zh_cn.md`](../coding/runtime_zh_cn.md) 解析 active runtime 时才加载本文件。

## 已登记部署

| 部署文档 | 状态 |
|---|---|
| [`hosts/codex-openai_zh_cn.md`](hosts/codex-openai_zh_cn.md) | 已验证部署；保持本 Skill 既有 Coding 行为 |
| [`hosts/claude-code-anthropic_zh_cn.md`](hosts/claude-code-anthropic_zh_cn.md) | 已投入真实使用；Haiku-tier 辅助派发与正常双 Session Sonnet Primary Output 派发现已执行，其余限制列在该文档中 |

每份文档覆盖一个产品/provider 组合的两个部署关注点：**Host Adapter**（这个产品如何实例化工作）与 **Model Profile**（哪个 Runtime 应承担某项职责）。应选择 Host Adapter 与当前环境匹配的那份文档。

Codex/OpenAI 条目继续保持本 Skill 已验证的 Coding 行为。Claude Code/Anthropic 条目已投入本 Skill 自身的真实 Coding 使用，其宿主映射以 Claude Code 官方文档为依据；真实使用已经覆盖的路径与仍然记录的限制都写在该文档中，该文档或宿主未暴露的内容必须继续标记为未验证，而不是按已验证假设处理。

没有列在这里的 Host 或模型族，不能仅因为能够解析 Agent Skills 或执行 Coding 任务，就被视为已经受到本 Skill 支持。

## 接入新的 Code Agent 产品

新的部署通常应增加：

1. 一份部署文档，描述该产品如何提供持久指令、独立 Session、模型/运行参数选择、上下文传输和隔离 capability，并同时给出在该产品上适用的角色 eligibility、具体模型绑定、执行参数策略、升级与 unavailable handling；
2. 验证：证明该部署遵守 Coding Runtime Contract，并且无需在 Core 文档中加入厂商分支。

不得修改已有部署项去近似适配另一个产品或 provider。新环境存在明确 capability 映射后，应新增独立文档；在相关 runtime 行为真实执行过之前，必须准确标注验证状态。

## Multimodal 边界

Multimodal Flow 当前不通过这套 Coding Runtime 注册表做通用化。它现有的部署绑定继续独立保存在 [`../multimodal-openai-profile_zh_cn.md`](../multimodal-openai-profile_zh_cn.md)。本注册表中的 Claude Code/Anthropic 条目只适用于 Coding Flow，不对 Multimodal Flow 的可移植性作承诺。
