# 候选内容合规预检

[English](CANDIDATE_COMPLIANCE.md) | [简体中文](CANDIDATE_COMPLIANCE_zh_cn.md)

本文负责只读 MCP 工具 `validate_decoupling_compliance` 的契约与边界。它描述有界的候选内容覆盖层检查，不定义工作流授权或最终验收。

## 用途与权限边界

此工具用于在另行授权写入之前，按照可信 checkout 检查拟议的文件变更。它接收候选内容，并将本次请求中的候选文件作为内存覆盖层共同检查，因此同一请求内的候选文件可以满足彼此的直接镜像和链接目标检查。工具不会写入候选文件、发送 API 请求、运行子进程或执行候选仓库代码。

可信根目录和允许的 policy scope 由服务器启动时通过 `--compliance-factory MODULE:CALLABLE` 加载的操作员代码提供。payload 和当前工作目录均不能选择根目录。仅将此 factory 配置为可信操作员代码，并指向预期 checkout。服务通过有界只读 reader 检查基线和直接目标。未配置 reader 时，不探测候选路径；依赖磁盘证据的检查保持 `unknown`，不得视为 `pass`。

## 请求契约

调用 `validate_decoupling_compliance` 时，在 `payload.request` 中提供 `{"policy_scope": ..., "candidates": [...]}`。

- `policy_scope` 为 `skill_maintenance` 或 `generic_project`。配置的服务必须明确允许所选 scope；不允许时返回 `unknown` 检查。
- `candidates` 包含 1–64 个条目，`path` 必须是唯一、规范的仓库相对 POSIX 路径，长度不超过 512 字符。拒绝绝对路径、反斜杠、NUL、空路径组件、`.` 和 `..`。
- 每个条目包含 `operation`（`create`、`replace` 或 `delete`）和 `baseline`。`create` 必须使用 `{"state":"absent"}`。`replace` 和 `delete` 必须使用 `{"state":"sha256","value":"<64个小写十六进制字符>"}`，对应当前磁盘字节的摘要。
- `create` 和 `replace` 必须提供 `content`（每个文件最多 131,072 个 Unicode 字符）；`delete` 不得含有内容（省略该字段或设为 null）。候选内容合计最多 524,288 个 UTF-8 字节；只计算候选内容，不包括 request、path 或 baseline 的编码开销。

调用时会将基线与可信根目录中的内容比较。基线不匹配、create 目标已存在或 replace/delete 目标不存在都会使基线检查失败。不安全或不可用的读取返回 `unknown`。基线不会锁定文件，也不授权后续写入；调用方必须独立取得写入授权，并在操作前重新核对当前状态。

## 检查与结果

对于 `skill_maintenance`，预检会检查候选镜像是否存在、适用的 Markdown 链接语言与层级规则、直接本地 Markdown 链接目标，以及候选属于 Layer-01 owner 时的章节结构。直接目标可由候选覆盖层或配置的根目录提供。不适用于某候选的检查标记为 `not_applicable`。

对于 `generic_project`，Skill 维护规则均为 `not_applicable`；此 scope 不会把仓库 Skill 规则套用于任意项目。启动配置未启用所请求的 scope 时，结果为 `unknown`。

结果包含 `policy_version`（`1`）、`status`、`policy_scope`、`checks`、`not_evaluated` 和 `limits`。每项检查报告 `rule_id`、status、path、line、有界 message 和 `evidence_missing` 列表；可用时也包含 `target_path` 和 `reason_code`。该列表说明解决 unknown 结果所需的证据；若无需补充证据则可以为空。状态为 `pass`、`fail`、`unknown` 或 `not_applicable`。总状态优先级为 `fail`、`unknown`、`pass`；若所有检查均不适用，则总状态为 `not_applicable`。出现 `unknown`、检查失败、输出截断或目标读取预算超限时，问题仍未解决；根据 `evidence_missing` 和 reason code 补齐或纠正，再用当前候选内容重新运行。

除上述请求限制外，直接目标最多读取 256 个，最多返回 512 项检查，每条消息最多 512 字符。超过直接目标或输出检查预算时会添加 `unknown` 结果；不得将省略的证据视为通过。

## 验收边界

预检通过仅表示：对于所提交的候选覆盖层和配置 reader 的观测，返回的检查均已通过。它不会扫描未变更文档中的反向入链，不比较英中镜像的语义等价性，也不运行完整仓库 CI 和最终集成验收；这些项目会明确列在 `not_evaluated` 中。接受或应用文档变更前，仍须完成适用的仓库检查和审阅。此工具不授权或执行该应用。

## 相关文档

- [MCP 目录指令](AGENTS_zh_cn.md)
- [Codex 调用方匹配](CODEX_CALLER_CONTEXT_zh_cn.md)
- [MCP 开发指南](DEVELOPMENT_zh_cn.md)
- [任务计划生命周期工具](TASK_PLAN_TOOLS_zh_cn.md)
- [Decoupling 工作流路由](WORKFLOW_ROUTING_zh_cn.md)
