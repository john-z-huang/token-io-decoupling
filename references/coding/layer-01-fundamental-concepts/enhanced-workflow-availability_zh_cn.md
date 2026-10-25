# 增强工作流可用性

[English](enhanced-workflow-availability.md) | [简体中文](enhanced-workflow-availability_zh_cn.md)

本文档负责判断何时可选择可选的 Enhanced 路径，以及能力不可用时如何处置。它不负责可信运行时身份、mode/count、状态生命周期或 Native 对账。

## 通用规范

Native 始终是默认路线，但仍须满足自身所需记录、权限和能力条件。Enhanced 是可选能力选择，不能由公共规则访问或产品/运行环境分类自动推出。只有任务需要其有状态操作，且[可信宿主绑定](enhanced-host-binding_zh_cn.md) owner 确认身份和具体必需守卫均已实际验证后，才能选择 Enhanced。

未选择 Enhanced 且它从未成为规范权威时，记录 `Not applicable` 及原因；Native 自身条件满足时继续该路线。若既有 Enhanced Root store 已成为规范权威，服务不可访问或路线偏好都不会使 Native 写入自动安全：须遵循[Native 权威转移](native-authority-transfer_zh_cn.md)，完成前阻塞依赖写入。从规范 Native 记录切换到 Enhanced，依赖 Root 写入前须遵循[Native 对账](native-reconciliation_zh_cn.md)。仅 API 建议失败而 Enhanced 状态服务健康时，不能据此切换路线。不得丢弃、静默覆盖或重置有效记录，不得绕过硬约束或推断 Enhanced 能力。

Coding Mode 及其数量仍由既有 owner 负责。可用性判断不选择、重开或更改它们。公共规则上下文只能证明规则可读，不能证明可信身份、数据库可用或受保护操作权限。

## Codex CLI / ChatGPT Desktop 特别优化指令

只有使用当前实际暴露且获授权的能力结果，才能确认 Enhanced 操作可用。当前项目实现和 SDK 级测试不能证明真实桌面宿主提供可信身份或守卫。若缺少宿主证据，则保留 Native 操作并将 Enhanced 可用性标为未验证；不得通过 Computer Use 来建立证明。跨运行时及模型/effort 绑定仍由[运行环境与模型厂商支持](runtime-provider-support_zh_cn.md)负责。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的可用性优化。遵循通用规范，并将任何未观察到的能力标为未知。

## 相关概念

- [增强宿主绑定](enhanced-host-binding_zh_cn.md) — 负责可信身份和操作守卫。
- [Native 权威转移](native-authority-transfer_zh_cn.md) — 负责 Enhanced 成为权威后的安全 Native 回切。
- [Native 对账](native-reconciliation_zh_cn.md) — 负责 Native-to-Enhanced Root 对账。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 负责持久化工作流状态和 mode/count 记录。
- [Coding Execution Control](execution-control_zh_cn.md) — 负责 Slice 释放和 Control 决策。
