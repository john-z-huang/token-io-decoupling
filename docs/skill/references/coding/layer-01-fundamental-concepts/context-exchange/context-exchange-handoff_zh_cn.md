# Coding Context Exchange Handoff

[English](context-exchange-handoff.md) | [简体中文](context-exchange-handoff_zh_cn.md)

本文档定义以 Serena 项目 Memory 持久化的 handoff 和 Worker context-index 记录的内容、更新与后继者暴露，不授权子 Agent 复用/替换，也不定义 capsule 新鲜度。

## 通用规范

### Context index 与 handoff 记录

使用 `context-exchange/INDEX` 作为父级路由索引，使用 `context-exchange/workers/<worker-context-id>/INDEX` 记录 Worker 的 task、scope、status、最近一次实质更新、记录名称及 blocker/handoff 目标。Handoff 记录保留已完成状态、带证据的失败方案、当前修改和验证、阻塞、下一步动作及准确权威来源指针。只在状态/证据/handoff 实质变化时更新，不要逐命令记录。

原 handoff/import 名称在 `context-exchange/` 下沿用相同 basename 和子目录意图映射。后继者只读取其已放行任务明确暴露的 Memory 名称；除非明确授权，不得写入其他 Worker 的名称。这只是指令逻辑归属，不是技术隔离；Serena 可能向任何获准 Session 暴露记录。不得重建完整 transcript。Memory 工具不可用时，报告并阻塞依赖工作；不得回退为文件。

### 授权边界

Context ID 或 Memory 名称本身不授权创建/替换 Agent，也不授权改变父级实时任务状态。mode/count/allocation/epoch 状态仍由其原 owner 管理。

## Codex CLI / ChatGPT Desktop 特别优化指令

只使用实际暴露且获准的 Serena 工具。在已放行 handoff 中点名准确记录，只读这些记录，核验来源新鲜度，并确认写入结果。Thread/worktree 转移本身不会创建或交付 Memory handoff。

## Claude Code CLI / Claude Desktop 特别优化指令

仅当当前 Session 暴露且授权时使用 Serena MCP Memory；依赖前先发现延迟加载的 MCP 工具。Claude resume/branch 和 auto memory 不授权或交付此记录。能力不可用时按报告/阻塞规则处理。

## 相关概念

- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 capsule 和新鲜度规则。
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位逻辑命名与授权。
- [Coding Session Context Firewall](../session-runtime/session-context-firewall_zh_cn.md) — 定位原始状态输入。
- [Coding Child Reuse and Replacement](../delegation/delegation-child-reuse-replacement_zh_cn.md) — 定位替换授权。
