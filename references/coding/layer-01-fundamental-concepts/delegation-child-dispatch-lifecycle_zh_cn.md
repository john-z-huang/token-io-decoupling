# Coding 子 Agent Dispatch 与生命周期

本文档负责多代理子 Agent 创建、职责分配、Dispatch Preview、Worker 边界、复用、替换和生命周期。它消费已放行且数量已锁定的多代理状态，不重新打开模式或数量确认。

## 创建能力

创建子 Agent 必须使用真实的 MultiAgentV1 或 MultiAgentV2 spawn 操作，不能用平级聊天或普通 task 代替。运行时必须暴露子 Agent 身份、父级控制的发送/返回路径、有界等待和生命周期状态。子 Agent 接收职责、Interaction Slice、获准范围/修改、返回条件和所需上下文；任一能力缺失或无法核验时停止并报告阻塞。

## 分配与辅助职责

只能在锁定数量内分配。Primary Output、Change Verification、Documentation/Comments & Git Operations、Context Bootstrap/Refresh 和其他独立职责各消耗一个名额。没有分配独立 verifier 或辅助职责时，在安全且获准的情况下由当前或已有 Agent 承担，否则报告不可用；不得用同一 Session 改名模拟独立性。

只有复用可能超过建立成本时才分配 Context Bootstrap/Refresh：至少两个独立下游 Worker、广泛探索并需加载三个以上 policy module，或 source set 大约超过 20k 字符/5k token-equivalents。一个小 Worker 或仅文档快路径应跳过。这些是路由启发式，不是已测量的运行时或质量收益。

## Dispatch 与 Worker 边界

每次实质性 Dispatch 前发布已授权切片的简洁 preview。Worker 只能向直接父级返回，不得创建、fork、handoff、消息联系、替换或协调其他 Agent/Session，也不得联系任意线程。Worker 发现不能改变根模式或数量。

每个 Worker 使用独立的 context-exchange 目录，只授予命名路径。除非明确允许独立且不冲突的并行工作，否则一次只发布一个 Interaction Slice。授权后续或修复 epoch 复用同一子 Agent。

## 生命周期

已创建子 Agent 必须保持可见和持久。不得关闭、shutdown、归档、删除或从任务面板移除。只有返回最终结果和证据后才能进入 completed。pending 或 running 时只能等待或发送已授权输入；发生错误或中断时复用同一子 Agent 进行获准修复或报告阻塞，不得以清理为由关闭。
