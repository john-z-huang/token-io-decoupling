# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` 是一个 Agent 调度 Skill，用于把高价值语义决策与高体量状态消费、输出物化分离。

它维护面向仓库和开发工作的 **Coding** 工作流。Multimodal 内容仅作为独立 reference 保留，不作为可执行工作流维护。请从 [`SKILL_zh_cn.md`](SKILL_zh_cn.md) 开始；它会按任务当前阶段路由到所需的 reference。

## 文档入口

- [`SKILL_zh_cn.md`](SKILL_zh_cn.md)：主要路由入口。
- [`references/`](references/)：由工作流组合使用的独立 Coding 模块和共享协议模块。
- [`MULTI_LINGUAL_zh_cn.md`](MULTI_LINGUAL_zh_cn.md)：双语文档规则。
