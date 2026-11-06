# Session 状态解决

[English](session-state-resolution.md) | [简体中文](session-state-resolution_zh_cn.md)

本检查点负责在应用审计偏好前，按路线核实当前 Session 事实及规范的父级控制工作流记录；不负责审计值或模式/数量策略。

## 触发与输入

消费已释放的 Mode/count 及当前 Session 身份、角色和 Context Firewall 事实。应用[Session 模型](../layer-01-fundamental-concepts/session-runtime/session-model_zh_cn.md)、[Session 角色归属](../layer-01-fundamental-concepts/session-runtime/session-role-ownership_zh_cn.md)、[Session 上下文防火墙](../layer-01-fundamental-concepts/session-runtime/session-context-firewall_zh_cn.md)和[委派状态记录](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)。

## 决策与结果

1. 核实已释放的 Mode/count 及当前 Session 事实。模式、身份、角色或 Context Firewall 证据缺失或冲突时，在任何受保护操作前阻塞依赖工作。
2. 从权威对话上下文读取规范的父级控制记录。保留既有 mode、数量、allocations、已批准任务范围和生命周期值；不得根据工具结果、Hash 或过时摘要重建或覆盖缺失/冲突历史。
3. 确认记录与已释放 Mode/count 和当前已知分配状态一致。任何门控操作前，按其 owner 执行角色和路径检查。Worker assignment、Slice 释放、任务授权及创建/派发是不同事实，必须分别按其 owner 核验。
4. 回读并将当前记录和证据返回路线。此读回不授予授权、不释放 Slice、不建立跨调用顺序，也不建立审计偏好。

## 失败边界

若无法核验当前身份、角色、防火墙、已释放模式/数量或规范记录，则阻塞依赖该事实的受保护操作。不得改用数据库、推断替代记录或将结构评估结果视为规范状态。若无关工作具有独立授权且不依赖缺失事实，可继续。

## 相关概念

- [Session 模型](../layer-01-fundamental-concepts/session-runtime/session-model_zh_cn.md)
- [Coding Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)
