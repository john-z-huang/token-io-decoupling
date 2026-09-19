# Coding 委派状态记录

本文档负责 Coding 委派使用的任务控制记录，定义状态结构、ownership 和 Worker 读写边界。不决定模式，不创建子 Agent，不分配职责，也不定义生命周期转换。

## Ownership

根父级负责当前根用户指令的记录。记录是任务状态，不通过编辑 policy 文件保存；父级控制的任务面板或等价运行时记录是规范位置。

## 记录结构

路线放行前记录：

```text
owner: <根父级身份>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode: Single-Agent Coding | Multi-Agent Coding
child_count: 0 | <正整数>
allocations: [{agent, role, interaction_slice, scope, mutations, return_conditions, lifecycle}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<能力名称>]
```

单代理的 `child_count` 为 0，多代理为已锁定的正整数。子 Agent 推进时，allocation 的 lifecycle 可以与顶层记录不同。

## Worker 边界

Worker 只能接收父级 Dispatch 中相关的已放行快照，不得推断、修改或替换根记录。放行后，Worker 通过父级 Dispatch Preview 进入，不重新打开根用户模式或数量门禁。运行时无法持久化或返回记录时，依赖该记录的路线被阻塞。
