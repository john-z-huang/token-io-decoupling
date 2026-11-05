# 检查点结构检查

[English](checkpoint-structure-checks.md) | [简体中文](checkpoint-structure-checks_zh_cn.md)

本文档负责对调用方提供的检查点事实和证据执行确定性结构评估。不负责认证输入、判定语义真实性、授权工作或验收任务。

## 通用规范

### 将评估视为可选的结构辅助

当结构检查有助于识别当前检查点判断中缺失或格式错误的所供事实时，可使用该检查。当前检查点 owner 仍是权威来源。应直接检查该 owner 并判断证据含义；结构完整的提交不证明事实真实，也不表示检查点已通过。

调用方提供的输入、证据引用、修订、指纹和 Hash 始终是调用方提供的事实。检查器可以拒绝格式错误、不一致、过期或不受支持的输入，但不能认证调用方、证明权限或来源、授予授权、建立跨调用顺序或验收任务。结果不持久化状态，也不会记住先前调用。

`ready_for_agent_review` 仅表示所供输入满足检查器的结构要求。`incomplete_for_agent_review` 报告缺失的必需事实或证据。`blocked_input` 报告无效、不一致、过期或不受支持的输入。无论何种状态，均须独立审阅当前 owner 和证据。

对于 Control，结构结果不能取代当前 Control owner、当前状态验证或必需的用户/Agent 判断。若可选结构检查不可用，应直接使用权威 owner 和可用证据；仅当无法以其他方式确立判断所需输入时，才阻塞该判断。

## Codex CLI / ChatGPT Desktop 特别优化指令

当可选结构检查有用且可用时，调用 `workflow_evaluate`，传入 `payload.node_id` 和 `payload.submission`；顶层 node 必须与 `submission.node_id` 一致。对于 Control，使用 `payload.submission` 调用 `evaluate_control_checkpoint`；其 node 必须为 `control`。两个 envelope 接受 `payload.language`（`en` 或 `zh_cn`，默认 `en`）、可选的 `payload.expected_rule_hash`、可选的 `payload.semantic_input` 和可选的 `payload.current_facts`。检查中文规则文本时，将 `language` 设为 `zh_cn`；默认值 `en` 选择英文规则。`current_facts` 默认为空 map；提供它不会启用 API 请求或授权披露。仅作结构检查时省略 `semantic_input`。若提供 `semantic_input`，还会单独请求 Decisions 建议，并遵循[Decisions Advisory](../execution-planning/decisions-advisory_zh_cn.md)；这不会改变结构结果。

类型化提交包含 1–128 项事实；顶层证据引用最多 128 项；覆盖维度最多三项；可选 evidence-request ID 长度为 1–128 字符。每项事实最多包含 16 个证据引用；`missing_evidence` 判断可指出 1–16 个必需引用。每个引用 URI 长度为 1–512 字符；evidence ID 或 request ID 长度为 1–128 字符。单独规范化提交（排除可选 `input_hash`）和完整规范化评估 payload 均限制为 32 KiB UTF-8 JSON；完整 payload 上限包含所有字段，包括 `submission`、`current_facts` 及任何 `semantic_input`，因此各字段上限不能同时全部用满。payload 的 `current_facts` map 可包含 0–16 组扁平字符串键值对，键长 1–64 字符，值长 1–1,024 字符；键和值不能为空或仅含空白字符。这些 JSON 字节上限适用于规范化模型 payload，不包括协议封装。

可选 `input_hash` 是一致性断言：省略时服务返回计算所得的 `source_input_hash`；若所提供的 Hash 不匹配，则返回 `blocked_input` 和 `source_input_hash_mismatch`。规范 SHA-256 的计算方式如下：对 `submission.model_dump(mode="json", exclude={"input_hash"})` 使用 `ensure_ascii=False`、排序键和紧凑的 `,`、`:` 分隔符进行序列化；将结果编码为 UTF-8，并对这些字节计算 Hash。`source_input_hash` 仅指纹化规范化后的提交。独立的可选 `expected_rule_hash` 必须来自相同 node 和所选语言的完整注册 node `rules_get_context` 结果，且须省略 `context_version`。不得传入 version 1 fragment bundle 的 `context_hash` 或 `index_sha256`；它们标识不同的规则片段集合。由于 `expected_rule_hash` 为可选项，若不需要该新鲜度断言，则不要额外查询规则。返回的 `rule_hash` 标识所选语言中当前注册 node 的完整规则，与 `source_input_hash` 不同。

结果报告 `status`、`reason`、评估所用的 `language`、`source_input_hash`、`rule_hash`，以及适用的分支和缺失要求。将结果视为 `authority: structural_check_only`；它绝不是检查点通过、权限、验收或顺序令牌。工具不持久化状态。schema 违反项会在评估前导致输入校验失败；应依据当前 schema 修正调用方输入后再重试，不能截断事实或证据以满足限制。返回的 `blocked_input` 表示提交不一致、过期或不受支持。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的检查点结构检查直接 MCP 优化。遵循通用规范，仅使用当前 Session 实际暴露的能力，并通过获准机制维护等效证据。可选检查不可用时，记录带理由的 `Not applicable`；若任务本身要求该结构结果，则只有在无法通过其他获准方式检查所需结构时，才阻塞依赖该结果的判断。

## 相关概念

- [工作流规则上下文](rule-context_zh_cn.md) — 负责有界导航至当前工作流规则。
- [工作流导航可用性](navigation-availability_zh_cn.md) — 负责导航不可用和可选检查分支。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 负责 Slice 与 Control 判断。
- [Decisions Advisory](../execution-planning/decisions-advisory_zh_cn.md) — 负责单独请求的可选语义建议。
