# 候选变更合规预检

[English](candidate-compliance.md) | [简体中文](candidate-compliance_zh_cn.md)

本文档定义对拟议仓库变更进行可选只读结构预检的规范。它不拥有写入授权、完整验证或最终验收。

## 通用规范

### 对照可信的当前状态检查候选内容

当已授权工作流需要提前获得结构反馈时，可将一组候选变更作为内存覆盖层，与可信检出内容一起检查。候选文件可相互满足直接的语言镜像和本地链接检查。基线记录观察到的文件状态；它不是锁、写入授权，也不保证状态保持不变。

策略范围必须明确。只有 `skill_maintenance` 请求适用 Skill 维护规则；`generic_project` 请求不得默默把本仓库的 Skill 规则应用到其他项目。配置了可信服务时，该服务还会限制可请求的范围。未配置读取器时，仍可执行候选内容的静态检查；依赖可信磁盘状态或基线证据的检查应为 unknown，而不是通过。候选请求不得选择自身可信根目录或策略来源。

分别将结果解释为 pass、fail、unknown 或 not applicable。将 unknown、失败、因限制未返回的检查以及过期基线视为未解决。修正原因或补齐证据后，应针对当前候选内容重新运行。成功预检只覆盖该覆盖层与读取器观察实际返回的检查。

预检不会扫描未变更文档中的反向入站链接、证明双语语义等价、执行仓库代码、运行所有项目检查、授权应用文件，也不替代当前状态 Verification 和 Acceptance。变更应用后仍须完成适用的权威检查。

## Codex CLI / ChatGPT Desktop 特别优化指令

当当前会话实际暴露并授权该能力时，使用 `payload.request` 调用 `validate_decoupling_compliance`，明确提供 `policy_scope`、候选路径、操作、内容和基线。可信根目录、启用范围和只读基线/目标读取器来自服务器启动时配置的操作方代码；请求内容和当前目录都不能选择它们。工具不会写文件、运行子进程、执行候选代码或调用 API。

对于 Skill 维护，检查返回项是否覆盖语言镜像、适用的链接语言/层级规则、直接本地目标及 Layer-01 结构。审阅 `not_evaluated`，因为反向入站链接、镜像语义和完整 CI 不属于预检。继续前解决 `unknown`、`fail`、截断或预算问题。通过结果不是授权；须单独取得写入权限，并在应用前重新检查当前状态。

## Claude Code CLI / Claude Desktop 特别优化指令

本项目 MCP Server 仅支持本地 Codex CLI；Claude 通用 MCP 能力不授权直接使用该 Server。本 owner 目前没有 Claude 专用直接工具优化。应依据当前会话实际暴露并授权的能力遵循通用规范；若可信读取器不可用，则将依赖磁盘的检查标记为 unknown，并使用适用的既有验证路线。

## 相关概念

- [Enhanced Host Binding](../enhanced-native-state/enhanced-host-binding_zh_cn.md) — 拥有可信身份和逐次调用守卫。
- [Workflow Routing Advice](workflow-routing-advice_zh_cn.md) — 拥有可选阶段建议。
- [Output Materialization](output-materialization_zh_cn.md) — 拥有受控输出准备与应用。
