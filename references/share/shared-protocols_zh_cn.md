# 共享调度协议

本模块定义可复用的 Coding 消息与上下文原语，不选择路线、Session 拓扑、Runtime 或 Agent 数量。

## Semantic Contract

Decision/Input-side 职责负责固化安全执行所需的最小语义：

- `Goal`：最终目标；
- `Constraints`：不可破坏的业务、兼容性、安全或用户边界；
- `Decisions`：已批准的架构与取舍；
- `Acceptance`：成功标准。

Contract 是决策锚点，不替代原始上下文。相关上下文直接提供给负责的职责，后续只发送新增目标、变化和必要约束。更新优先使用 amendment；只有修订冲突到无法判断当前状态时才发送一次 authoritative snapshot。所需上下文无法安全共享或表达时，停止并报告上下文阻塞。

## 父级返回路径

根父 Agent 负责当前请求的父级控制通道。每个 Worker 都必须非递归，只能通过运行环境的仅限父级通道、控制边界或最终 result 返回。越界事项只返回非空的 `Status`、`Issue`、`Need` 和 `Parent action`。Worker 不得选择兄弟、任意 thread 或其他编排路径。运行环境不能强制该边界时，Worker 视为阻塞。

## Dispatch Preview

工作流已经授权创建子 Agent 或向独立 Worker 发送新指令后，仅当配置审计预设选择 preview 时，才在执行动作前显示极简预览；若选择 full，则展示完整安全消息正文。预览是可见摘要，不是隐藏推理，也不能替代必要的用户确认。

只使用有意义的字段：

```text
Dispatch → <role> | Task: <objective>; Scope: <needed paths>; Constraints: <direct execution limits>; Runtime: <only if required>
```

配置预设选择 preview 时，最多 3 项（目标、允许改动、返回条件），总计不超过 600 个 Unicode 码位；按实际显示的 Markdown 源文本计数，包括空白和链接文字/目标。这不是 token 估算，无需逐条消息调用计数工具。优先精简措辞并指向完整正文；重要授权或失败证据无法容纳时，只允许必要超限并说明原因，不得截断或拆分以规避限制。复用 Worker 时只显示新 delta。同 Session 的职责切换和本地工作不属于 Dispatch，不得打印虚构的 self-dispatch。

## 事件驱动反馈

Worker 将普通读取、局部分析、常规编辑、重复检查和原始日志保留在自身上下文中。只有发生实质里程碑、需要父级判断的决策、阻塞、重大偏差或无法满足 Contract 时，才向父级发送简短信号。只返回下一步决策所需事实、证据指针和所需动作；不得附完整日志、diff、截图、OCR 或历史。完成时返回压缩结果、验证结论和剩余风险。完整实际任务与返回正文必须始终可供负责的父级取得，并在依赖前读取；只有其显示副本遵循配置的审计预设。压缩信号或摘要不能替代实际返回正文或对其审查。

## Evidence-on-Demand

决策职责向持有原始状态的职责提出定向证据请求。只返回最小的相关路径、图片/帧引用或事实摘录。不得为了同步上下文重新读取或生成完整证据。每个新的最终状态 epoch 都必须重新评估；此前结论只能作为上下文，不能作为证明。

## 缓存感知的稳定性

优先使用 `stable prefix + small delta`：保留稳定决策和工作上下文，只追加新目标、amendment 或验证要求。不要周期性重写完整 Contract 或任务历史。优先采用事件驱动的有界等待，仅在状态变化时更新记录。缓存 key、命中条件、quota、latency 和质量影响由 Runtime 决定，不得擅自保证。稳定历史妨碍正确理解时，执行一次压缩或重建。

本模块不能绕过用户授权、权限、产品限制、仓库规则、安全限制或 Runtime capability 检查。
