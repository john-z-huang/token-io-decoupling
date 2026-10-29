# 上下文检查点

[English](context.md) | [简体中文](context_zh_cn.md)

## 动作

1. 明确下一切片必须回答的最小问题。
2. 只读取回答该问题所需的文件、元数据、历史或生成证据。
3. 复用缓存或文件上下文前，检查其范围、所有者、来源路径、新鲜度和最终状态 epoch。
4. 将过期、不完整或互相冲突的上下文视为不可用。只刷新受影响的上下文，并记录发生了什么变化。
5. 保持上下文以事实和路由信息为主；不能用它替代 Contract、源文档或验证。
6. 对适用工作流决策节点选择的规则查询，应用[增强规则上下文](../../layer-01-fundamental-concepts/enhanced-native-state/enhanced-rule-context_zh_cn.md)：核对请求节点、owner、语言和来源/Hash，并单独读取摘录未包含的必需直接 owner。保持返回上下文有界，并在依赖前确认必需 owner 内容。
7. 已放行 Worker 需要持久化 memo 或交换记录时，必须确认具名持久 Memory 能力可用；memo 与跨 Worker 交换仍是独立触发条件。逻辑归属遵循所链接的 Layer-01 owner。能力不可用时报告并阻塞依赖工作；不得回退为文件存储。
8. 已放行任务要求复用先前 Agent 项目知识时，使用[项目 Memory 与代码结构能力](../../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools_zh_cn.md)访问获准 Memory，并对照权威项目文件核验来源指针和新鲜度。能力不可用时报告限制并返回获准的权威项目文件；仅当必需事实无法从其他获准方式确认时才暂停。Memory 不能替代获准路径中的权威项目文件。

9. 应用[任务计划 Memory 生命周期](../../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)：复用前读取匹配共享计划，对照当前权威来源核验，新实质事实先记录再汇报或执行依赖动作。必需访问/更新失败阻塞依赖工作；已记录的持久化限制按 owner 的例外处理。

## 通过条件

下一切片拥有有界且当前有效的上下文，或已记录具体缺失的上下文并暂停该切片。

## 边界

本检查点只收集和判断上下文，不作实质性决策，不授权实现，也不宣布验证完成。

## 相关概念

- [Coding Context Exchange](../../layer-01-fundamental-concepts/context-exchange/context-exchange_zh_cn.md) — 定位 Memory capsule 和新鲜度归属。
- [Coding Session Context Firewall](../../layer-01-fundamental-concepts/session-runtime/session-context-firewall_zh_cn.md) — 定位原始状态进入和事实返回归属。
- [项目 Memory 与代码结构能力](../../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools_zh_cn.md) — 定位可复用项目知识和结构化代码浏览。
