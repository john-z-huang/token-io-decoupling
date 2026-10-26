# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` 是一个 Agent 调度 Skill，用于把高价值语义决策与高体量状态消费、输出物化分离。

它维护面向仓库和开发工作的 **Coding** 工作流。Multimodal 内容仅作为独立 reference 保留，不作为可执行工作流维护。请从 [Skill 入口](SKILL_zh_cn.md) 开始；它会按任务当前阶段路由到所需的 reference。

## 文档入口

- [Skill 入口](SKILL_zh_cn.md)：主要路由入口。
- [Coding reference](references/)：由工作流组合使用的独立 Coding 模块和共享协议模块。
- [多语言规则](MULTI_LINGUAL_zh_cn.md)：双语文档规则。
- [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md)：可选 MCP 状态、规则上下文、语义建议及经核验的宿主边界；Native 仍为默认路径。
- [MCP 开发指南](mcp/DEVELOPMENT_zh_cn.md)：本地 Python 检查与包构建。

可选 Decisions 集成默认关闭。每次真实请求（包括测试请求）必须读取本地 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`，缺少任一项就不得请求。显式启用与测试方法见开发指南。当前生产入口没有经核验的 Codex 或 ChatGPT Desktop 宿主绑定，因此只暴露公共诊断与规则上下文。
