# Coding 子 Agent 生命周期

[English](delegation-child-lifecycle.md) | [简体中文](delegation-child-lifecycle_zh_cn.md)

本文档负责已创建多代理子 Agent 的持久性和生命周期状态。它消费已由各自 owner 概念处理创建、分配和派发的子 Agent；不定义创建、职责分配、Dispatch Preview、Worker 边界、复用/替换或上下文传输。

## 通用规范

### 生命周期状态

在父级记录中持久保存每个已创建子 Agent 的身份和生命周期。运行环境存在持久任务面板时，不得仅为清理而关闭、shutdown、归档、删除或移除子 Agent。运行时状态界面是短暂的情形下，其条目消失后仍在父级记录保留子 Agent ID 和状态。pending 或 running 时只能等待或发送已授权输入。只有返回最终结果和证据后才能进入 completed。

### 错误与中断

发生错误或中断时，保持原 child 状态明确并保留现有证据；未经授权不得以清理为由关闭它。先通过复用同一个 child 尝试获准修复。只有在 `child_count` 尚未锁定时，父级才能使用受控 replacement 路径。数量锁定后，如果同一个 child 无法安全复用，报告阻塞并将多代理路线置为 `blocked`；不得创建 replacement child。获准复用或锁定前的 replacement 遵循对应 owner 概念。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

可用时通过 `Agent` 结果和 `/tasks` 观察运行中的子代理；以有界运行时等待取得结果。`/tasks` 是短暂状态界面，其条目消失后仍在父级记录保留返回的 Agent ID 和完成或错误状态。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位 Dispatch Preview 和 Worker 边界。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准修复和替换关系。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。
