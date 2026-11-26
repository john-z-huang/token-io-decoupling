# 工作流架构

本页记录旧 MCP 服务存在时的职责分工。 [归档说明](../README.md)

## Skill、宿主与 MCP

- **Skill 定义流程**：`rules/` 中的 YAML 是维护源，构建器生成 `skill/` 阅读版。Agent 从 [Coding 选择器](../../../rules/workflows/coding.yaml)进入已授权的路线，再按当前动作读取适用的 [Hook 合同](../../../rules/hooks/README.yaml)。路线定义阶段顺序；Hook 定义触发、证据、通过或阻断条件，不是逐条自动触发的宿主事件。
- **Pi 提供执行环境**：Agent 使用实际发现且获准的宿主工具，核对会话、子代理能力、权限和结果。是否能调用工具与是否有权执行是两回事。具体限制见 [运行时能力边界](../../../rules/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support.yaml)。
- **MCP 提供通用工具**：唯一服务 `token-io-decoupling-tools` 通过 stdio 提供规则上下文、结构预检和其他开发工具，并提供 Skill 安装更新命令。它不选择路线、不推进检查点、不创建子代理，也不管理会话或任务计划生命周期。注册、包结构及启动边界见 [MCP 开发指南](mcp/DEVELOPMENT.md)。

## 规则数据与权限

MCP 的规则注册表和片段索引绑定 DSL 文档的 Markdown 导出路径和标题。源码查询和分发包摘录使用同一份导出。规则上下文的 Hash 只标识所读内容，不能证明语义正确、来源授权或任务通过验收。规则读取和结构预检不依赖数据库、API 凭据或联网。

通用 Git、托管平台和 API 工具分别遵守各自的授权与外发条件。可选的 [Worker 输出材料化](mcp/OUTPUT_MATERIALIZATION.md)还要求可信调用方、当前任务分配、独立授权与新鲜的 [合规预检](mcp/CANDIDATE_COMPLIANCE.md)；普通工具发现和默认 stdio 启动不能建立这些条件。

## 旧扩展归档

旧 Pi 工作流扩展已归档，仅供只读参考，不安装、不加载，也不参与当前构建和验证。它曾通过 Pi 宿主事件注入路线和合同、维护回执及恢复信息；当前实现并未逐条迁移旧适配，也不据此声称已完成运行时验收。历史说明见 Git 归档前版本；当前行为以 Skill 和实际宿主能力为准。
