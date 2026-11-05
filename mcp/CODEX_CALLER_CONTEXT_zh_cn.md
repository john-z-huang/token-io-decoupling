# Codex MCP 本地会话上下文

[English](CODEX_CALLER_CONTEXT.md) | [简体中文](CODEX_CALLER_CONTEXT_zh_cn.md)

本文档负责本地 stdio 请求的项目、线程与角色范围；这些标识不是独立身份认证，也不是操作系统隔离。

## 安装与调用

标准 `setup codex` 注册当前两个独立的本地 stdio 可执行程序：workflow 和 tools，均不带启动参数。无需特权服务、宿主描述符或外部 identity provider；旧 `--host-fd` 和 `--codex-context` 选项已删除。从目标项目目录启动 Codex，MCP 在启动时固定该目录的 canonical path，并以 SHA-256 派生项目分区。

Codex 在 MCP 请求顶层 `_meta` 中传入 `threadId` 和 `sessionId`。状态操作要求两者都是有界非空字符串，线程还必须是安全路径分量；不要将它们放入工具 payload。`sessionId` 是不透明标识，其变化不重置线程状态。公共能力、规则与配置诊断不要求会话元数据。能力报告的 `support.local_stdio` 和 `runtime.binding` 区分本地支持与当前请求上下文；报告本身不测试所有依赖。

## 分配与权限

Root 必须通过现有 reserve、slice 与 `delegation_bind` 流程登记 Worker；登记是应用记录，不是宿主对真实父子关系的认证。Worker 按当前项目下已有 allocation 和 Worker 状态解析 Root，只能访问自己的分配。重复 Root 归属、数据库身份不匹配或不安全路径均拒绝。首次未知线程只有在显式打开自己的 Root 工作流后才能使用该状态；可执行程序或工具发现不能证明调用方的实际角色。请求作用域通过 ContextVar 在结束/异常时恢复，不借用其他并发请求。

路径穿越、派生符号链接、数据库身份、角色、分配生命周期、revision、幂等及物化的独立 grant 检查保持生效。API 请求仍要求配置和逐调用外发授权。能力字段不是用户授权。

## 信任边界与验证

同一 OS 用户能修改本地文件或自行发送元数据，因此本服务不抵抗该用户的恶意进程，也不声明独立进程认证或 OS 级 Worker 隔离。可信计算边界是用户已批准的本地 Codex/MCP 配置及实际 OS 权限。内部 Python 注入接口只供嵌入/测试，不是标准安装前置条件。

只支持本地 Codex CLI。源代码 `core/src/mcp_tool_call.rs::with_mcp_tool_call_ids_meta` 负责线程元数据；[官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp)说明本地 stdio 注册。缺元数据、角色不匹配、危险路径与并发隔离由本地回归覆盖；安装包和 fresh CLI 检查按开发指南执行，不把合成标识称为认证证据。

## 相关概念

- [开发指南](DEVELOPMENT_zh_cn.md)
- [增强宿主绑定](../docs/skill/references/coding/layer-01-fundamental-concepts/enhanced-native-state/enhanced-host-binding_zh_cn.md)
