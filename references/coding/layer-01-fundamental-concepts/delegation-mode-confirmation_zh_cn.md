# Coding 委派模式确认

[English](delegation-mode-confirmation.md) | [简体中文](delegation-mode-confirmation_zh_cn.md)

本文档负责根指令的模式建议和明确确认、确认前限制以及单代理路线限制。它消费并更新状态记录；不定义数量锁定、重新进入、子 Agent 创建或生命周期。

## 根指令模式确认

每个新的根用户指令到达后，根父级必须：

1. 确认运行环境暴露了父级控制的任务面板或等价的任务控制记录能力。
2. 如果能力存在，在提出确认问题前创建或初始化 `gate_status: awaiting-mode` 记录。如果能力缺失或未知，则阻塞依赖该记录的路线，不得假设记录存在。
3. 分析任务到足以形成有用建议的程度。
4. 建议单代理 Coding 或多代理 Coding，并给出简短理由。
5. 询问用户选择并等待明确确认。

根指令中写明的模式不能替代确认。在确认前不得创建/管理 Agent 或 Session、发布 Dispatch，或开始实质性侦察、实现、验证、文档和 Git 工作。为形成问题所需的强制指令加载和能力检查可以执行。

将确认模式记录到任务控制记录。确认多代理 Coding 后，将记录转为 `gate_status: awaiting-count`；确认单代理 Coding 后，设置 `child_count: 0`，并仅在所需放行条件满足后释放路线。含糊或未回答不能放行。

## 单代理 Coding

确认后所有工作保留在当前 Session。不得创建、fork、handoff、消息联系、替换或管理子 Agent 或额外 Session。结构收益、验证、文档/Git、bootstrap、恢复或运行便利都不是例外。独立验证仍是语义要求，但该路线不可用。

## 相关概念

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位数量锁定归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。
