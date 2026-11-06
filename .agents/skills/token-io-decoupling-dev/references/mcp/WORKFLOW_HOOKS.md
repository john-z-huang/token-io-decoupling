# 无状态 workflow 事件与 Hook


本文负责 `workflow_check_event` 与可选 Codex 原生 Hook 命令的运行时契约。[作者 Hook 文档](../../../../../instruction-compiler/sources/skill/references/coding/hooks/README.md)负责判断政策。Agent 根据简短流程指令选择执行路径，自行在上下文中记忆运行信息，并在相关事件发生时消费检查。

## 事件请求与交付

MCP 工具通过 `payload.request` 调用：

```json
{
  "payload": {
    "request": {
      "event": "task_received",
      "mode": "single-agent",
      "include_workflow": true,
      "language": "zh_cn",
      "facts": {
        "task": {"status": "provided", "value": "审阅请求的改动", "source": "用户请求"}
      },
      "evidence_refs": [{"kind": "request_source", "reference": "用户请求"}]
    }
  }
}
```

六种事件为 `task_received`、`boundary_requested`、`action_observed`、`progress_reported`、`completion_requested` 和 `session_resumed`。每次加载 `common.shared` 及当前事件正文，必需事实／证据和允许结果均来自文档。可选 `mode` 为 `single-agent` 或 `multi-agent`，不推断或改变 Agent 的模式。`include_workflow: true` 必须显式提供模式，并附上同批次短流程。

指令、清单及 Skill 索引使用 schema 3 的中文单源形状，不含语言镜像。`language` 保留为契约标记，仅接受 `zh_cn`，默认值也为 `zh_cn`；显式 `en` 被拒绝。外部节点查询的 `context_version=2` 与 bundle schema 2 不因此改变。

`context_summary` 最多 8,000 字符；最多接受 64 项命名事实和 64 项证据引用，事实值最多 16,000 字符，引用最多 512 字符。事实状态为 `provided`、`unknown` 或 `not_applicable`；已提供事实和不适用解释须含非空白值。完整规范信封不超过 32 KiB UTF-8 JSON。引用和断言均是未验证输入，不构成来源认证或权限。

`max_chars` 默认 24,000，范围 256–60,000，约束事件和可选流程的文本总量。这是交付容量，不是执行预算。容量不足时返回 `instructions_incomplete`，两份正文都为空，且不发送语义请求。旧 `rules_get_context` 保持 12,000 默认值。预期 build/rule hash 可钉住当前文档，但只检查内容，不是全局游标。

结果分为 `instructions`、`structural_check` 和 `advice`。顶层状态为 `checked`、`instructions_incomplete`、`rules_unavailable` 或 `stale`。结构 `ready_for_agent_review` 只表示声明形状齐全，不证明真实或验收成功。`unknown` 和 `not_applicable` 仍待 Agent 复核。结果不推进阶段或放行授权门禁；服务不提供 workflow 状态文件、数据库、日志、恢复记录或跨调用计数器。

## 显式模型建议

普通 stdio 提供静态规则与结构检查。以 `--enable-event-advice` 启动 workflow 命令，可启用独立的可选事件建议通道。每次请求仍须提供 `semantic_input.outbound_data_permitted: true`；可选 `focus` 是有界数据，不是政策。只有启动旗标或只有请求均不会外发数据。其它既有建议通道保持原配置和默认行为。

通过上述条件后才读取非空 `OPENAI_API_KEY`、`OPENAI_BASE_URL`，使用固定 `gpt-6-luna` 发送一次有界 Decisions 请求，20 秒超时且不自动重试。选项描述和 `feedback` 均摘录当前事件的结果与反馈段。`semantic_reason_provided: false` 明确 API 只返回选项，不提供逐案理由。结构缺口是独立发现，不得将规范反馈冒充模型针对本例的诊断。

只接受一个有效文档选项、固定模型和有效 token 用量。已安装 Decisions SDK 未声明 `status` 字段，因此允许缺失；额外提供时必须为 `completed`。显式 null、不完整、进行中、未知状态、非空 error/incomplete_details、拒绝和畸形答案均失败。成功与故障均关闭 client，关闭失败同样返回安全的 unavailable。供应商错误使用既有有界恢复分类，不输出原始消息或凭据。重新加载事件／流程后若 build/hash 变化，建议变为 stale 并移除所选结果。

`continue`、`needs_evidence`、`amend`、`wait`、`stop` 和 `not_applicable` 均为建议。完成事件的 `continue` 只是交由 Agent 实际验收的候选，`stop` 永不表示成功。重试次数及当前证据由 Agent 自行记忆；该操作不写文件、不派发、不创建子代理或调用其它工具。

## 可选原生命令

`token-io-decoupling-workflow hook [--mode single-agent|multi-agent] [--language zh_cn]` 从 stdin 读取一个最多 32 KiB 的 JSON 对象，输出一个最多 128 KiB 的响应。不读取 transcript 或任意文件，不接受凭据／端点旗标。`--max-chars` 仅控制指令交付容量。

| Codex 事件 | 逻辑事件 | 默认响应 |
| --- | --- | --- |
| `UserPromptSubmit` | `task_received` | `hookSpecificOutput.additionalContext` |
| `PreToolUse` | `boundary_requested` | `hookSpecificOutput.additionalContext` |
| `PostToolUse` | `action_observed` | `hookSpecificOutput.additionalContext` |
| `SubagentStop` | `progress_reported` | `systemMessage` |
| `Stop` | `completion_requested` | `systemMessage` |
| `SessionStart` | `session_resumed` | `hookSpecificOutput.additionalContext` |

这是已支持的本地 Codex schema，不是通用 MCP 客户端适配器。Stop/SubagentStop 不允许 additionalContext，默认 systemMessage 不会把规则回灌模型，也不证明逻辑检查已被消费；Skill 要求 Agent 主动调用完成／进展检查。原生观察不完整，permission_mode 和 session ID 不能证明授权或恢复任务历史。

调用方必须将命令限定到已采用本 workflow 的会话。适配器无法从原生输入确认采用状态，不默认注册全局 Hook，也不记录采用状态。无法可靠限定时改用主动 MCP 调用。独立工具保留自身的当前输入契约，不要求先调用 Hook。

原生语义模式须提供 `--semantic --outbound-data-permitted`。显式选择 `--block-once` 后，只有 Stop/SubagentStop 的原生 `stop_hook_active` 严格为 false、完整新鲜指令已检查、有效建议为 `needs_evidence` 或 `amend`，才输出 `decision: block`。true／缺失／非布尔标志、等待／停止结果、缺失／故障／陈旧建议均不阻塞。reason 包含结构缺口与完整规则，不伪造语义理由。此宿主续跑标志不证明预算、身份、授权或整个会话有界，也不自动重试。

Hook 选项／输入／运行错误返回退出码 1，argparse 非零错误从 2 转为 1，以免宿主意外阻塞；帮助返回 0。只有合法显式 JSON 会请求阻塞。安装和 setup 不修改真实 Hook 配置。

## 迁移与验证

`workflow_check_event` 替换已移除的 `decide_decoupling_workflow`，workflow 固定清单仍为 11 项，独立 tools 仍为 41 项。不提供 stage、next-stage、自动路线选择器或 Python DAG 模拟。旧规则查询和细粒度决策方法保持无状态，预设后继列表为空。分工政策从实际 Hook 语义段提取，不加载导航卡作为完整政策。

`token_io_decoupling_workflow.events` 包拥有该事件能力：`contracts` 定义编译文档，`models` 定义单次输入／结果，[checks](../../../../../mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/events/checks.py) 组装完整规则与结构诊断，[advice](../../../../../mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/events/advice.py) 拥有可选模型边界，[native](../../../../../mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/events/native.py) 映射原生事件，[cli](../../../../../mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/events/cli.py) 处理有界进程 I/O。`__init__` 不重导出或执行初始化。`RuleLoader` 只依赖编译文档契约，事件服务调用其公共加载方法；建议使用明确的 `decisions.validated_choice` 与 `decisions.is_refusal` 接口，另行校验整体响应状态、模型和用量。不移动其它既有服务。运行时测试只使用 fake；原生 schema 检查不代表真实集成或全局有界。遵循 [workspace 检查](DEVELOPMENT.md)与[最终用户安装](../../../../../INSTALL.md)。
