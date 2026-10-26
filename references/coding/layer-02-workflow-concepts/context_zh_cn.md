# 上下文检查点

[English](context.md) | [简体中文](context_zh_cn.md)

## 动作

1. 明确下一切片必须回答的最小问题。
2. 只读取回答该问题所需的文件、元数据、历史或生成证据。
3. 复用缓存或文件上下文前，检查其范围、所有者、来源路径、新鲜度和最终状态 epoch。
4. 将过期、不完整或互相冲突的上下文视为不可用。只刷新受影响的上下文，并记录发生了什么变化。
5. 保持上下文以事实和路由信息为主；不能用它替代 Contract、源文档或验证。
6. 为回答下一问题而选择有界当前规则上下文读取时，应用[增强规则上下文](../layer-01-fundamental-concepts/enhanced-rule-context_zh_cn.md)：核对请求节点、owner、语言和来源/Hash，并单独读取摘录未包含但判断必需的直接 owner。不需要读取时，仍须直接核验必需 owner，并记录 `Not applicable` 及原因。读取失败时，在权威 owner 可访问的情况下改为直接读取；无法确认必需 owner 内容时，阻塞依赖该内容的判断。
7. 已放行 Worker 需要持久化 memo 或交换记录时，必须确认具名持久 Memory 能力可用；memo 与跨 Worker 交换仍是独立触发条件。逻辑归属遵循所链接的 Layer-01 owner。能力不可用时报告并阻塞依赖工作；不得回退为文件存储。
8. 当前问题需要复用先前积累的 Agent 项目知识时，使用[项目 Memory 与代码结构能力](../layer-01-fundamental-concepts/LSP-MCP-Tools_zh_cn.md)列出 Memory 并读取相关条目，再对照权威项目文件核验来源指针和新鲜度。Memory 列表可用但不含相关条目，或无需跨会话知识时，记录 `Not applicable` 及原因。能力不可用时，报告不可用并回到获准的权威项目文件；不得据此推断不存在相关 Memory。只有必需事实无法从其他获准来源确认时才暂停。Memory 不能替代获准路径中的权威项目文件。

## 通过条件

下一切片拥有有界且当前有效的上下文，或已记录具体缺失的上下文并暂停该切片。

## 边界

本检查点只收集和判断上下文，不作实质性决策，不授权实现，也不宣布验证完成。

## 相关概念

- [Coding Context Exchange](../layer-01-fundamental-concepts/context-exchange_zh_cn.md) — 定位 Memory capsule 和新鲜度归属。
- [Coding Session Context Firewall](../layer-01-fundamental-concepts/session-context-firewall_zh_cn.md) — 定位原始状态进入和事实返回归属。
- [项目 Memory 与代码结构能力](../layer-01-fundamental-concepts/LSP-MCP-Tools_zh_cn.md) — 定位可复用项目知识和结构化代码浏览。
