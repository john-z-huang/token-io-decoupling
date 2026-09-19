# Coding Session Model

本模块定义 Coding 的职责 ownership、Session 语义、Context Firewall 和 Primary Execution Session Affinity。它独立于运行环境/模型 eligibility、执行参数、dispatch 格式、上下文文件传输和验收流程。

## 架构角色

### 输入侧推理 Agent

负责用户意图与业务语义分析、Semantic Contract、架构和风险决策、未解决的权衡、阶段与 slice 边界、放行决定、checkpoint 结果、用户交互和最终语义验收。它可以请求证据和候选项，但必须解释其含义，不得摄入高体量项目原始状态，也不得把已批准的决定展开成长篇输出。

### Primary 输出角色

负责高体量项目探索、证据压缩、在已批准方向内执行、代码/配置物化、已放行 slice 内的修复和临时实现检查。它采用渐进式读取，不能改变未解决的目标、约束、架构或验收标准，也不负责最终验收或非简单 Git 工作。

### Context Bootstrap/Refresh 职责

被分配时，构建或刷新包含中性项目事实、准确 source pointer、policy-routing pointer 和 freshness 数据的有界 fingerprint capsule。它不定义任务、不修改 Contract、不实现、不验证、不物化文档，也不得递归委派。Capsule 只能补充强制指令，不能替代直接读取权威文件。

### Change Verification Agent

被分配时，独立依据 Contract 和验收标准验证实质性改动的最终状态。它消费范围证据，执行适当的整体和定向检查，针对每个最终状态 fingerprint/epoch 重新评估，并报告证据、缺口、失败和风险。除明确点名的验证资产外，它对产品代码/配置、文档和 Git 保持只读；不修复、不作语义决策、不委派。

### Documentation/Comments & Git Operations Agent

被分配时，只物化获准的文档/注释，或只执行明确放行的非简单 Git slice。它不得修改产品行为、测试或语义决策；如果冲突需要新的内容或含义，必须返回父级。文档与 Git 工作保持为彼此独立的执行范围。

## Session 语义

模式、拓扑、职责分配、生命周期、复用、替换、例外和不可用处理由当前工作流提供。职责名称本身不能授权新建 Session 或改变拓扑。

单代理 Coding 中，当前 Session 执行逻辑上的决策、实现、文档、Git 和允许的检查阶段；逻辑职责不表示存在独立 Agent。多代理 Coding 中，只使用当前工作流明确提供的独立 Session：

```text
根父 Session → Input-side Reasoning
已分配 Primary Session → Primary Output
已分配 verifier Session → Change Verification
已分配文档/Git Session → Documentation/Comments & Git Operations
```

未分配的职责在独立 Session 层面不可用。不得通过给同一 Session 的工作改名来模拟独立性。

## Context Firewall

在多 Session Coding 中，输入侧 Session 不执行开放式项目检查。Primary Output 消费源代码/配置状态；Change Verification 消费最终状态证据；Documentation/Comments & Git Operations 消费 Git 状态和获准的文档范围。各自只返回下一步决策所需的事实。

只有严格有界的只读元数据可由输入侧直接检查。边界由潜在输出体积和仓库状态影响决定，而不是由命令名称决定。单 Session 没有跨 Session Firewall，但仍须渐进读取并压缩原始状态。

Firewall 限制原始状态进入输入侧上下文，不限制语义推理。输入侧仍拥有含义、权衡、放行决定和验收；临时的 UI/项目定位状态留在观察它的 Session 中，不提升为长期 Contract 状态。

## Primary Execution Session 与 Affinity

维持一个 Primary Execution Session：多代理模式下是已分配的 Primary Output Session，否则是当前 Session。相关探索、实现、诊断、测试、修复和局部执行优先复用它，以保留稳定上下文。Session 应保持 sticky but not immortal；生命周期变化遵循当前工作流的已记录状态。

Session 隔离与 Git worktree 隔离不同。同一开发需求的 Worker 通常共享 primary worktree；隔离 worktree 必须有明确放行的隔离范围。不得仅因复用 Session 就宣称一定命中缓存或获得其他运行时收益。
