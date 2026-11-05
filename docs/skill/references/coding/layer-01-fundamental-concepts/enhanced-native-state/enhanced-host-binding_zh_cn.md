# Enhanced 宿主绑定

[English](enhanced-host-binding.md) | [简体中文](enhanced-host-binding_zh_cn.md)

本文档负责 Enhanced 的本地会话范围、角色分配与逐操作检查。这里的“绑定”是应用内登记，不表示独立宿主认证或 OS 隔离；不负责模式、计数或路线选择。

## 通用规范

### 本地登记与操作范围

使用本进程固定项目范围、当前请求会话标识和已登记的分配。状态操作必须校验角色、所属 Root、自己的 Worker 分配、数据库身份、路径、revision、幂等和独立授权；缺失、冲突或越界即拒绝。不要求额外特权宿主、外部 identity provider 或无从验证的 guard 证明，也不得以全量填充 guard 来假装已验证。

Root 登记 Worker 需要已批准的角色和已释放 Slice。分配记录是应用关系，不证明真实运行时父子身份。未知线程必须显式打开自己的 Root 工作流后才能使用该状态；发现同一线程有多个 Root 归属应阻断。每个调用重新读取当前分配，请求作用域在结束和异常时恢复。

### 信任边界

元数据只用于本地路由，payload、环境变量、profile 和 `authorized=true` 不能取代操作授权。同一 OS 用户可以修改本地数据或伪造元数据；本设计不防御该用户的恶意进程，不提供独立进程认证或 OS 级 Worker 隔离。实际文件访问仍受 OS 权限约束。历史数据字段名中的 verified/trusted/guard 不扩大这一保证。

Native Coding 角色不自动登记 MCP Worker。未选择 Enhanced 或其依赖不可用时，独立已授权的 Native 工作仍可继续；已有 canonical 状态的转移遵循原 owner，不重建或覆写记录。合成测试和协议测试只证明所测行为，不证明宿主认证。

## Codex CLI / ChatGPT Desktop 特别优化指令

### 本地 stdio

标准本地 Codex CLI stdio 使用启动 cwd 的 canonical path 派生项目分区，并解析 MCP `_meta.threadId/sessionId`。状态调用需要有界非空元数据和安全线程分量；不透明 sessionId 的变化不重置线程。Root 用现有分配操作登记 Worker，Worker 从当前项目已有分配中解析范围。调用前查看能力与独立配置，不需要特权通道启动步骤。

源码依据：`core/src/mcp_tool_call.rs::with_mcp_tool_call_ids_meta`；[官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp)说明 stdio 注册。只有当前会话实际暴露且授权的调用入口可用；禁止 Computer Use。此优化只支持本地 Codex CLI。

## Claude Code CLI / Claude Desktop 特别优化指令

### 不适用

[官方 MCP 文档](https://code.claude.com/docs/en/mcp)说明该产品也有 stdio，但不能据此假定其元数据与上述契约相同。本仓库 MCP 不支持其直接连接，不增加适配；文档使用者可继续执行通用规范及独立已授权的 Native 工作，不因缺少此优化阻断无关任务。

## 相关概念

- [增强工作流可用性](enhanced-workflow-availability_zh_cn.md)
- [增强状态存储](enhanced-state-store_zh_cn.md)
- [委派状态记录](../delegation/delegation-state-record_zh_cn.md)
