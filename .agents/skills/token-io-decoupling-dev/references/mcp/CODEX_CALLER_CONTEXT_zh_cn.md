# Codex MCP 本地会话上下文

[English](CODEX_CALLER_CONTEXT.md) | [简体中文](CODEX_CALLER_CONTEXT_zh_cn.md)

本文档负责本地 stdio 应用范围和请求元数据边界。这些标识不是独立身份认证，也不构成操作系统隔离。

## 安装与调用

标准 `setup codex` 注册当前两个独立的本地 stdio 可执行程序：workflow 和 tools，均不带启动参数。无需特权服务、继承的宿主描述符或外部 identity provider；旧 `--host-fd` 和 `--codex-context` 选项已删除。从目标项目目录启动 Codex。MCP 在启动时捕获其规范路径，用于项目范围检查。无状态规则和工作流调用不会持久化项目分区。

Codex 在 MCP 请求顶层 `_meta` 中传入 `threadId` 和 `sessionId`。使用请求元数据的操作要求相应字段是有界非空字符串；使用路径的操作还会验证相关路径。不要将这些字段放入工具 payload。`sessionId` 是不透明标识，不能认证调用方。公共能力、规则与配置诊断无需会话元数据。能力报告描述已配置的支持，不证明身份、权限或所有依赖。

## 分配与权限

无状态导航和结构评估不存储 allocation、角色或工作流状态。所供身份、任务分配、证据指针和 Hash 都是调用方事实，不能证明真实的父子关系或授予权限。每项受保护操作必须分别执行当前角色、路径、grant 和授权检查。

`materialize_decoupled_output` 要求可信启动注入式授权 provider、匹配的逐次调用 Worker 绑定、独立操作方 grant、固定根目录和当前预检。工具 payload 不能选择 provider 或提供授权。当前未配置标准 provider，因此该操作默认不可用。

## 信任边界与验证

同一 OS 用户能修改本地文件或自行发送元数据，因此本服务不抵抗该用户的恶意进程，也不声明独立进程认证或 OS 级 Worker 隔离。可信计算边界是用户已批准的本地 Codex/MCP 配置及实际 OS 权限。内部 Python 注入接口只供嵌入/测试，不是标准安装前置条件。

只支持本地 Codex CLI。源代码 `core/src/mcp_tool_call.rs::with_mcp_tool_call_ids_meta` 负责线程元数据；[官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp)说明本地 stdio 注册。缺元数据、角色不匹配、危险路径与并发隔离由本地回归覆盖；安装包和 fresh CLI 检查按开发指南执行，不把合成标识称为认证证据。

## 相关概念

- [开发指南](DEVELOPMENT_zh_cn.md)
- [Session 角色归属](../../../../../instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/session-runtime/session-role-ownership_zh_cn.md)
