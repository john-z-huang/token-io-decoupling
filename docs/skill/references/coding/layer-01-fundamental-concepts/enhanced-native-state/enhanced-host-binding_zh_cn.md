# 增强宿主绑定

[English](enhanced-host-binding.md) | [简体中文](enhanced-host-binding_zh_cn.md)

本文档负责 Enhanced 身份与操作守卫的可信来源、角色暴露和每次调用重新核验。它不负责路线选择、mode/count、任务政策或跨运行时模型绑定。

## 通用规范

受保护操作要求可信嵌入端提供当前 project、root-session 和 current-session 身份、传输角色，以及实际权限/守卫证据。每次调用都要重新核验绑定和该操作所需的守卫，包括工具已列出之后。证据被撤销、缺失、含糊或不足时，拒绝受保护调用；若 Native 工作另有授权，则仍可继续。

环境变量、客户端元数据、调用方提供的身份或路径、操作参数，以及 `authorized=true` 等字段都不是身份或权限证据。未安装可信 Provider 时，生产默认拒绝受保护的 Enhanced 访问。未绑定时只暴露公共只读接口；只有对应绑定已验证时才暴露 Root 或 Worker 接口，并且每次调用都重新核验。Worker 绑定不授予访问其他 Worker 或 Root-only 数据的权限。

证据结论必须保持边界：fake provider 只验证服务是否符合测试契约；SDK 或 stdio 子进程只验证协议行为。两者都不能证明真实宿主提供了 attestation 或执行了 OS 权限边界。没有该宿主的直接证据时，不得声称真实宿主已验证。

## Codex CLI / ChatGPT Desktop 特别优化指令

当前生产 CLI 未安装可信宿主 Provider，因此默认拒绝受保护操作。每项任务都要核对当前 Session 实际暴露且获授权的能力和证据：若可信 Provider 提供可验证身份及足够的操作守卫，则按通用规则逐次核验；否则将该能力标记为不可用/未验证，不执行受保护调用。新增运行时能力在直接暴露、获授权并通过同一核验后即可使用；普通使用者无需先修改本 Skill。SDK 子进程测试和 fake 绑定只属于协议/契约证据。不得使用 Computer Use 检查桌面或制造身份凭据。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的宿主绑定优化。遵循通用规范；不得推断可信 Provider 已存在。

## 相关概念

- [增强工作流可用性](enhanced-workflow-availability_zh_cn.md) — 负责选择 Enhanced 或 Native 处置。
- [运行环境与模型厂商支持](../session-runtime/runtime-provider-support_zh_cn.md) — 负责跨运行时及模型/effort 绑定。
- [Coding Delegation State Record](../delegation/delegation-state-record_zh_cn.md) — 负责与身份关联的持久状态和 Worker 生命周期。
