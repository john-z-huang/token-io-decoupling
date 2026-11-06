# 输出物化

[English](output-materialization.md) | [简体中文](output-materialization_zh_cn.md)

本文档定义通过单独授权的写入能力，对有界候选输出批次进行受控准备、检查和应用。它不拥有角色政策、授权签发、最终验证或通用文件写入。

## 通用规范

### 区分准备、审阅和应用

只有在当前调用中核实当前任务分配、操作专用授权、固定根目录、精确路径和必要安全能力后，才可准备输出。角色分配、工具发现、能力列表或普通写入权限均不能替代独立且匹配的授权。上下文或守卫缺失、过期、撤销或含糊时，应停止，不得猜测路径或能力。

准备会在项目目录外创建有界候选产物，不得称为项目写入。保留其标识符和清单哈希。只检查有界内容，并在应用前审阅候选内容。仅当重新核实当前权限、产物完整性、基线以及针对固定项目的新鲜整批预检后，才可应用同一候选内容。应用期间不得重新生成内容，也不得将先前预检视为当前授权。

仅使用有限的本地渲染模板和既定限制。任何可选语义服务只能在已提供的事实标识符中排序；本地代码保留原始事实并渲染输出。配置缺失、拒答、响应无效、上下文过期或超限时，准备应停止，不得替换成自由形式的输出。服务未报告用量时，不得推断用量为零。

应用仅限精确授权的路径和操作。重新检查当前文件状态，保留外部变更，并在部分或不确定结果后检查收据和实际文件。同一候选内容的重放不得覆盖用户后续变更。协作锁无法防止无关写入者并发修改；多文件批次可能只应用一部分，也不保证全局回滚。状态不确定或权限已变化时，应依据当前证据先解决问题，再准备新候选内容。

此能力是可选的。能力不可用时，可在自身授权路线允许的范围内继续 Native 输出工作。不得把不可用当作成功，也不得弱化相关角色、权限或验证 owner。

## Codex CLI / ChatGPT Desktop 特别优化指令

当前 MCP 操作为 `materialize_decoupled_output`，使用 `payload.request` 中的 `prepare`、`inspect` 或 `apply` 动作。它需要可信启动注入式授权 provider 提供当前 Worker 绑定和 assignment 上下文、单独的 operator grant、固定项目/产物根目录，以及必要的只读合规预检。服务核对该 provider 上下文与真实逐次调用 Worker 绑定一致，并在各阶段重新核验授权。工具 payload 不能选择或提供授权上下文。当前没有配置标准 provider；缺少可信 provider 或 grant 时能力不可用，不猜测默认根目录。

受支持角色为 `Primary Output`，输出类别为 `code_configuration`，政策范围为 `generic_project`。项目专属 Skill 作者维护属于私有开发 Skill；普通文档和其他角色/类别不受支持。政策版本 2 提供有限的 `literal_text`、`json_document` 和 `fact_markdown` 模板。`prepare` 在项目目录外保存候选内容；`inspect` 读取有界页面；`apply` 在写入前重新检查当前授权、任务分配、哈希、基线和整批预检。保留并传回同一个清单哈希。检查逐文件和批次收据，尤其是 `partial`、`conflict` 或 `uncertain`；不得假定存在回滚，也不得对变更后的内容重试。精确请求字段、限制和恢复分类由 MCP 输出物化契约管理。

可选的事实排序请求应遵循实际 MCP 工具元数据声明的固定 API 契约；模型只能返回已提供事实标识符的排序。该工具契约不会检查或改变 Agent Session 的模型。Agent 运行时、模型和推理力度绑定见 [Runtime and Model Provider Support](../session-runtime/runtime-provider-support_zh_cn.md)。

## Claude Code CLI / Claude Desktop 特别优化指令

本项目 MCP Server 仅支持本地 Codex CLI。Claude 通用 MCP 能力不代表该 Server 支持直接连接，本 owner 也没有 Claude 专用直接工具优化。应依据当前会话实际暴露并授权的能力遵循通用规范。若此受控能力不可用，则使用任何独立获授权的直接输出路线及其验证要求。

## 相关概念

- [Candidate Compliance Preflight](candidate-compliance_zh_cn.md) — 拥有只读候选检查。
- [Session Role Ownership](../session-runtime/session-role-ownership_zh_cn.md) — 负责角色责任；此服务仍需单独的可信绑定上下文和 grant。
- [Workflow Navigation Availability](../workflow-navigation/navigation-availability_zh_cn.md) — 负责可选导航不可用时直接读取 owner 的回退。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 拥有释放和 Control 转换。
- [Task Assignment](task-assignment_zh_cn.md) — 拥有执行者和输出责任选择。
