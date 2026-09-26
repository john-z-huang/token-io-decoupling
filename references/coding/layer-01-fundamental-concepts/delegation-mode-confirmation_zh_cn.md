# Coding 委派模式确认

[English](delegation-mode-confirmation.md) | [简体中文](delegation-mode-confirmation_zh_cn.md)

本文档负责会话首次的模式问题、明确选择或超时默认、选择前限制以及单代理路线限制。它消费并更新状态记录；不定义数量锁定、重新进入、子 Agent 创建或生命周期。

## 通用规范

### 会话模式选择

本次会话第一次 Coding 指令到达后，根父级必须：

1. 检查用户是否已经在该指令中明确选定单代理或多代理 Coding；若已选定，直接记录，不再重复提问。
2. 否则只询问一次：`本次会话请选择单代理 Coding 或多代理 Coding；选择多代理时可同时指定正整数子代理数量。我等待 15 秒；若没有明确回复，默认使用多代理 Coding 和 1 个子代理。` 在同一条消息中简要说明建议及理由。
3. 问题发出后开始计时 15 秒。运行环境暴露非阻断输入通道时使用该通道；此门禁不得使用无限期阻断的问题工具。等待期间只能加载强制指令并检查能力；不得创建子代理、发布 Dispatch，或开始实质性项目工作。
4. 截止前可观察到明确选择则按选择执行；没有可观察到的明确选择则选择多代理 Coding 和 1 个子代理。迟到的回复不得暗中改变本次会话已锁定的模式。
5. 在父级控制的状态记录中写入模式及来源（`explicit` 或 `timeout-default`）。路线放行前应用数量 owner；本次会话内保持模式不变。

超时只选择工作模式，不提供缺失的用户授权，不绕过任务级禁止事项，也不创造能力。更高优先级规则禁止子代理时，不能依据超时默认值启动子代理。缺少所需记录能力时，阻塞依赖路线，不得假装记录存在。

### 单代理 Coding

确认后所有工作保留在当前 Session。不得创建、fork、handoff、消息联系、替换或管理子 Agent 或额外 Session。结构收益、验证、文档/Git、bootstrap、恢复或运行便利都不是例外。独立验证仍是语义要求，但该路线不可用。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

未查到 Claude Code 原生 `AskUserQuestion` 超时或等价异步回复工具。以普通进度文字发出模式问题，保持当前 turn 活跃并计时 15 秒，检查宿主在截止前提供的回复。不得为此门禁调用会阻断的 `AskUserQuestion`。若宿主在活跃 turn 中无法提供回复，记录该限制并在 15 秒后采用默认值，不得无限等待。

## 相关概念

- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位数量锁定归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。
