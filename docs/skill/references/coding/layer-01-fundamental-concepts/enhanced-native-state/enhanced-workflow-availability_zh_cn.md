# 增强工作流可用性

[English](enhanced-workflow-availability.md) | [简体中文](enhanced-workflow-availability_zh_cn.md)

本文档负责判断何时可选择可选的 Enhanced 路径，以及能力不可用时如何处置。它不负责可信运行时身份、mode/count、状态生命周期或 Native 对账。

## 通用规范

Native 始终是默认路线，但仍须满足自身所需记录、权限和能力条件。Enhanced 是可选能力选择，不能由公共规则访问或产品/运行环境分类自动推出。只有任务需要其有状态操作，且[本地绑定](enhanced-host-binding_zh_cn.md) owner 确认当前请求范围、已登记角色、路径和操作授权后，才能选择 Enhanced。

未选择 Enhanced 且它从未成为规范权威时，记录 `Not applicable` 及原因；Native 自身条件满足时继续该路线。若既有 Enhanced Root store 已成为规范权威，服务不可访问或路线偏好都不会使 Native 写入自动安全：须遵循[Native 权威转移](native-authority-transfer_zh_cn.md)，完成前阻塞依赖写入。从规范 Native 记录切换到 Enhanced，依赖 Root 写入前须遵循[Native 对账](native-reconciliation_zh_cn.md)。仅 API 建议失败而 Enhanced 状态服务健康时，不能据此切换路线。不得丢弃、静默覆盖或重置有效记录，不得绕过硬约束或推断 Enhanced 能力。

Coding Mode 及其数量仍由既有 owner 负责。可用性判断不选择、重开或更改它们。公共规则上下文只能证明规则可读，不能证明当前会话范围、数据库可用或受保护操作权限。

## Codex CLI / ChatGPT Desktop 特别优化指令

标准本地 stdio 支持状态操作；按[绑定 owner](enhanced-host-binding_zh_cn.md)确认当前请求范围、分配和独立授权。无需特权宿主证明。禁止 Computer Use；未提供的能力仍记为不可用。

## Claude Code CLI / Claude Desktop 特别优化指令

此 MCP 优化不适用；不增加直接客户端支持。独立已授权的 Native 文档流程继续可用。

## 相关概念

- [增强宿主绑定](enhanced-host-binding_zh_cn.md) — 负责当前会话范围和操作守卫。
- [Native 权威转移](native-authority-transfer_zh_cn.md) — 负责 Enhanced 成为权威后的安全 Native 回切。
- [Native 对账](native-reconciliation_zh_cn.md) — 负责 Native-to-Enhanced Root 对账。
- [Coding Delegation State Record](../delegation/delegation-state-record_zh_cn.md) — 负责持久化工作流状态和 mode/count 记录。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 负责 Slice 释放和 Control 决策。
