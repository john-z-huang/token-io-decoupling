# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` 是一个 Agent 调度 Skill，用于把高价值语义决策与高体量状态消费、输出物化分离。

它提供两条独立 Flow：**Coding** 面向仓库和开发工作，**Multimodal** 面向 GUI/浏览器、视频、图片及其他视觉状态工作。请从 [`SKILL_zh_cn.md`](SKILL_zh_cn.md) 开始；它会按任务当前阶段路由到所需的 reference。

## 文档入口

- [`SKILL_zh_cn.md`](SKILL_zh_cn.md)：主要路由入口。
- [`BEST_PRACTICES_zh_cn.md`](BEST_PRACTICES_zh_cn.md)：可选的当前 Codex/OpenAI 使用指南。
- [`references/`](references/)：Flow、Coding、Runtime、Host 和 Profile 详细文档。
- [`MULTI_LINGUAL_zh_cn.md`](MULTI_LINGUAL_zh_cn.md)：双语文档规则。
