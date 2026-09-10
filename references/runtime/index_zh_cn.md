# Coding Runtime 注册表

本注册表列出已经具有明确 Host Adapter 与 Model Profile 的具体 Coding 部署。它属于部署元数据，不是 Runtime 无关的 Coding 角色架构。

只有 Coding Flow 通过 [`../coding/runtime_zh_cn.md`](../coding/runtime_zh_cn.md) 解析 active runtime 时才加载本文件。

## 已登记部署

| Host Adapter | Model Profile | 状态 |
|---|---|---|
| [`hosts/codex_zh_cn.md`](hosts/codex_zh_cn.md) | [`profiles/openai_zh_cn.md`](profiles/openai_zh_cn.md) | 当前已验证部署 |

Codex/OpenAI 条目继续保持本 Skill 已验证的 Coding 行为。

没有列在这里的 Host 或模型族，不能仅因为能够解析 Agent Skills 或执行 Coding 任务，就被视为已经受到本 Skill 支持。

## 接入新的 Code Agent 产品

新的部署通常应增加：

1. Host Adapter：描述该产品如何提供持久指令、独立 Session、模型/运行参数选择、上下文传输和隔离 capability；
2. Model Profile：声明角色 eligibility、具体模型绑定、执行参数策略、升级与 unavailable handling；
3. 验证：证明该部署遵守 Coding Runtime Contract，并且无需在 Core 文档中加入厂商分支。

不得修改已有部署项去近似适配另一个产品或 provider。新环境存在明确 capability 映射后，应新增独立 Adapter/Profile 组合；在真实 runtime smoke test 完成前，必须准确标注验证状态。

## Multimodal 边界

Multimodal Flow 当前不通过这套 Coding Runtime 注册表做通用化。它现有的部署绑定继续独立保存在 [`../multimodal-openai-profile_zh_cn.md`](../multimodal-openai-profile_zh_cn.md)。本注册表只适用于 Coding Flow，不对 Multimodal Flow 的可移植性作承诺。
