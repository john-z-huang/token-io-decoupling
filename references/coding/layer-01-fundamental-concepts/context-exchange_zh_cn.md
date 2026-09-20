# Coding Context Exchange

[English](context-exchange.md) | [简体中文](context-exchange_zh_cn.md)

本模块只定义已分配 Coding Worker 的传输 capsule：其内容限制、freshness/invalidation 检查和权威 source 规则。不定义工作区布局、目录 ownership、capability 边界、handoff 记录、任务含义、Agent 拓扑、执行规划或验收。

## 传输 capsule

只传递接收 Worker 当前所需的上下文。优先把原文档以定向只读方式暴露给它；无法暴露时，父级或文件系统层可以创建父级准备的只读目录，并把点名文档机械复制到 `CONTEXT_ROOT/<worker-context-id>/imports/<source-context-id>/`；Worker 可以读取导入内容，但不得重写。父级必须在具体 handoff 或依赖关系中点名来源文档，权威 source 仍然优先且具有约束力。只有两种文件系统方式都不安全时，才使用精简的父级中转 handoff。

可复用 capsule 可以包含中性事实、准确路径和 source pointer、hash、freshness/invalidation 数据以及窄范围证据指针。不得包含实现推理、Contract 结论、私有 chain-of-thought、秘密、完整 diff、完整日志或大段源码副本。接收 Worker 先读 capsule，再只读自身需要的点名 source 路径；权威源文件仍具有约束力。

对于 `CONTEXT_ROOT/context-bootstrap/` 下的 capsule，使用：

```text
MANIFEST.md        快照身份、hash、freshness 规则
project-context.md 中性项目事实和 source pointer
policy-context.md  policy-routing pointer 和权威 section
```

Freshness 对照 `HEAD`/tree、tracked-delta fingerprint、列出的 source hash、相关未跟踪状态以及当前 task/scope 检查。实质字段变化时，只刷新受影响 section 后再依赖 capsule；否则直接读取点名的权威 source。Capsule 永远不能替代最终状态的独立验证。

## 相关概念

- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位工作区和 capability 边界。
- [Coding Context Exchange Handoff](context-exchange-handoff_zh_cn.md) — 定位 handoff 记录归属。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入边界。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位 named-path 派发边界。
