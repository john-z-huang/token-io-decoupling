# Coding 运行环境能力清单

[English](environment-capability-inventory.md) | [简体中文](environment-capability-inventory_zh_cn.md)

本文档负责已分类运行环境的能力清单：暴露能力、未知能力处理、依赖路线阻断以及按分支使用能力。不分类运行环境，不选择执行模式，不绑定角色，不授权委派，不授权实现，也不定义任务策略。

## 暴露能力清单

只记录当前界面直接暴露的能力：模型身份和参数控制、Session 拓扑、文件系统与沙箱访问、工具、连接器、认证，以及委派工作可用的返回路径。

## 未知能力和路线阻断

未观察到的能力标记为未知。不得替换成其他运行环境、模型、参数、Session、工具、权限或推断出的能力。所需能力缺失或未知时，阻塞依赖该能力的切片。

## 按分支使用能力

路线消费这份能力清单和状态，只记录各自拓扑差异。在本地 Codex 中使用当前暴露的模型/Session 控制；修改全局指令、覆盖指令、Skill 或仓库指令后重新启动。在 ChatGPT Work 中只使用明确暴露的模型、Session、文件、连接器和执行工具。在标准 ChatGPT 中不假设拥有本地执行、Git、worktree 或独立 Session。

## 相关概念

- [Coding Session Model](../layer-01-fundamental-concepts/session-model_zh_cn.md) — 定位 Session 拓扑归属。
- [Coding Session Role Ownership](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md) — 定位职责责任归属。
- [Coding Context Exchange 工作区边界](../layer-01-fundamental-concepts/context-exchange-workspace-boundary_zh_cn.md) — 定位文件系统和 worktree 能力归属。
- [Coding Delegation Mode Confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md) — 定位模式门禁能力消费者。
- [Coding Delegation Count Gate](../layer-01-fundamental-concepts/delegation-mode-count-gate_zh_cn.md) — 定位数量门禁能力消费者。
