# 候选变更合规预检

[English](candidate-compliance.md) | [简体中文](candidate-compliance_zh_cn.md)

本文档定义对拟议仓库变更进行可选只读结构预检的规范。它不拥有写入授权、完整验证或最终验收。

## 通用规范

### 对照可信的当前状态检查候选内容

当已授权工作流需要提前获得候选反馈时，对照可信检出内容检查有界路径、操作、内容 envelope 和基线事实。基线记录观察到的文件状态；它不是锁、写入授权，也不保证状态保持不变。

产品预检仅提供通用候选路径和基线检查，不根据任务标签选择项目专属作者规则。候选请求不得选择自身可信根目录或策略来源；缺少必需可信读取器或基线证据时，结果保持 unknown，不得判为通过。静态 envelope 有效不替代当前磁盘证据。

分别将结果解释为 pass、fail、unknown 或 not applicable。将 unknown、失败、因限制未返回的检查以及过期基线视为未解决。修正原因或补齐证据后，应针对当前候选内容重新运行。成功预检只覆盖该覆盖层与读取器观察实际返回的检查。

预检不验证语言镜像存在、Markdown 链接或分层结构，不证明语义等价、不执行仓库代码、不授权应用文件，也不替代当前状态 Verification 和 Acceptance。通过实际可用且获授权的能力，运行目标仓库自身要求的文档、语言及其他检查。本项目的作者文档校验器属于私有开发流程，不属于安装后的产品；在其他仓库使用产品不要求访问该私有目录。应用变更后仍须完成目标项目适用的权威检查。

## Codex CLI / ChatGPT Desktop 特别优化指令

当前会话实际暴露并授权该能力时，调用 `validate_decoupling_compliance`，传入 `payload.request.policy_scope: generic_project` 及准确候选路径、操作、内容和基线。这是产品唯一支持的策略范围。可信根目录、启用服务范围和只读基线读取器来自操作方启动配置；请求或当前目录都不能选择它们。核对返回的 `policy_scope` 和 `policy_version: 2`。工具不会写文件、运行子进程、执行候选代码或调用 API。

包括 Skill 维护在内的所有任务，仅检查实际返回的通用路径或基线结果，并审阅 `not_evaluated`。不得期待该工具完成双语、Markdown、分层或目标项目语义检查。继续前解决 `unknown`、`fail`、截断或预算问题。通过结果不是授权；须单独取得写入权限、应用前重新核实当前状态，并保留目标仓库另外要求的检查。

## Claude Code CLI / Claude Desktop 特别优化指令

本项目 MCP Server 仅支持本地 Codex CLI；Claude 通用 MCP 能力不授权直接使用该 Server。本 owner 目前没有 Claude 专用直接工具优化。应依据当前会话实际暴露并授权的能力遵循通用规范；若可信读取器不可用，则将依赖磁盘的检查标记为 unknown，并使用适用的既有验证路线。

## 相关概念

- [Session Role Ownership](../session-runtime/session-role-ownership_zh_cn.md) — 拥有可信身份和逐次调用守卫。
- [Workflow Routing Advice](workflow-routing-advice_zh_cn.md) — 拥有可选阶段建议。
- [Output Materialization](output-materialization_zh_cn.md) — 拥有受控输出准备与应用。
