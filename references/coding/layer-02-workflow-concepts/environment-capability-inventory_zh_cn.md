# Coding 运行环境能力清单

[English](environment-capability-inventory.md) | [简体中文](environment-capability-inventory_zh_cn.md)

本文档负责已分类运行环境的能力清单：暴露能力、未知能力处理和依赖路线阻断。分支定义和模型绑定由[运行环境与模型厂商支持](../layer-01-fundamental-concepts/runtime-provider-support_zh_cn.md)负责。本文档不分类运行环境，不选择执行模式，不绑定角色，不授权委派，不授权实现，也不定义任务策略。

## 暴露能力清单

只记录当前界面直接暴露的能力：模型身份和参数控制、Session 拓扑、文件系统与沙箱访问、工具、连接器、认证，以及委派工作可用的返回路径。

## 未知能力和路线阻断

未观察到的能力标记为未知。不得替换成其他运行环境、模型、参数、Session、工具、权限或推断出的能力。所需能力缺失或未知时，阻塞依赖该能力的切片。

## 路线消费

路线消费这份能力清单和状态，只记录各自拓扑差异。按[运行环境与模型厂商支持](../layer-01-fundamental-concepts/runtime-provider-support_zh_cn.md)应用分支特定的控制和模型绑定。

路线所需的 profile 是能力要求，不是对整个产品可用性的声明。分支特定路线只有在本清单记录当前 surface 实际生效的模型身份及该 profile 要求的每项参数后，才能消费该 profile。如果必需的模型或参数未暴露或未知，必须将该要求记录到 `unavailable_capabilities`，并阻塞依赖的切片或路线。不得静默替换模型、reasoning effort、Session、工具、权限或 mode/count；选择其他路线必须重新进入其适用门禁并取得新的明确确认。这使 Core 规则与产品细节解耦，同时允许路线消费其所需的、特定于 surface 的 profile。

## 相关概念

- [Coding Session Model](../layer-01-fundamental-concepts/session-model_zh_cn.md) — 定位 Session 拓扑归属。
- [Coding Session Role Ownership](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md) — 定位职责责任归属。
- [Coding Context Exchange 工作区边界](../layer-01-fundamental-concepts/context-exchange-workspace-boundary_zh_cn.md) — 定位文件系统和 worktree 能力归属。
- [Coding Delegation Mode Confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md) — 定位模式门禁能力消费者。
- [Coding Delegation Count Gate](../layer-01-fundamental-concepts/delegation-mode-count-gate_zh_cn.md) — 定位数量门禁能力消费者。
