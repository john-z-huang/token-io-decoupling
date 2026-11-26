# MCP Server 开发指令

本页保留旧服务的开发约定。 [归档说明](../README.md)

原目录面向 Pi Coding Agent，文档规范见[仓库维护说明](../../../docs/DOCUMENTATION_STANDARDS.md)。

仅发布 `token-io-decoupling-tools` 一个可执行入口，通过 uv tool 安装；默认 stdio，附带 Skill 安装和更新命令。不要恢复 workflow MCP 服务或双入口安装器。宿主 Extension 独立保留。

保留通用工具原有的授权、可信绑定、路径与外发检查。不得将 Pi 会话标识或自报元数据冒充为已验证调用方绑定，也不得为了适配宿主而降低材料化等操作的保护要求。Skill 仅安装至 `~/.pi/agent/skills/` 下受管理目录，不覆盖未知目录、本地改动或符号链接。

开发与测试见 [开发指南](../docs/mcp/DEVELOPMENT.md)。普通测试不启动真实模型或真实 API。
