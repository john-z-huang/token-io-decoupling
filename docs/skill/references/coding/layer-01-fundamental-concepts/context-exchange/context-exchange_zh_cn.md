# Coding Context Exchange

[English](context-exchange.md) | [简体中文](context-exchange_zh_cn.md)

本文档定义已分配 Coding Worker 的 Serena 项目 Memory 上下文 capsule 内容与新鲜度规则，不定义 Memory 命名/授权、handoff 记录、任务含义、Agent 拓扑或验收。

## 通用规范

### Capsule 内容与权威来源

只有已授权 handoff 或 context bootstrap 需要持久记录时才写入 capsule。内容限于精简中性事实、指向权威来源的准确指针、hash、新鲜度/失效数据和窄范围证据指针。不得把来源文件全文复制到 Memory；权威仓库文件仍具有约束力。接收 Worker 只读取已放行任务中点名的 capsule Memory，再对照获准且点名的来源核实所需事实。

使用以下 bootstrap Memory 名称保留原文件名：`context-exchange/context-bootstrap/MANIFEST`、`context-exchange/context-bootstrap/project-context` 和 `context-exchange/context-bootstrap/policy-context`。`MANIFEST` 记录快照身份、hash 和新鲜度规则；其他 Memory 保存中性项目事实/指针及 policy-routing 指针。其他交换/import 记录在 `context-exchange/` 下沿用原 basename 和子目录意图。

根据 `HEAD`/tree、tracked-delta fingerprint、所列来源 hash、相关未跟踪状态和当前 task/scope 检查新鲜度。实质字段变化时只刷新受影响条目；否则直接读取点名权威来源。Capsule 不能替代 Contract 或最终状态的独立验证。Memory 列表/读写能力不可用时，报告限制并阻塞依赖工作；不得回退为文件存储。

## Codex CLI / ChatGPT Desktop 特别优化指令

只使用实际暴露且获准的 Serena Memory 工具。在已放行任务中点名准确 capsule Memory，使用前先读取并核验来源指针/新鲜度，写入后确认结果。不得仅为加载 capsule 而扩大来源或工具权限。

## Claude Code CLI / Claude Desktop 特别优化指令

仅当当前 Agent Session 暴露且授权 Serena MCP 工具时使用 Serena Memory。Claude Code MCP Tool Search 可能延迟工具定义；依赖前先发现并核实工具。Claude auto memory 或 compaction 不能替代具名交换 capsule。

## 相关概念

- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位逻辑命名和授权。
- [Coding Context Exchange Handoff](context-exchange-handoff_zh_cn.md) — 定位 handoff 记录内容。
- [Coding Session Context Firewall](../session-runtime/session-context-firewall_zh_cn.md) — 定位有界输入规则。
- [Coding Child Dispatch](../delegation/delegation-child-dispatch_zh_cn.md) — 定位已放行任务授权。
