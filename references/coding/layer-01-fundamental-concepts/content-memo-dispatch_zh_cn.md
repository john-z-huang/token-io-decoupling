# Worker Content Memo Dispatch

[English](content-memo-dispatch.md) | [简体中文](content-memo-dispatch_zh_cn.md)

本文档只定义父 Agent 控制的 Worker 文件化执行 memo `write_content_memo` dispatch 开关。不定义 memo 内容、memo 生命周期、上下文传输或子 Agent 生命周期。

## 通用规范

### Dispatch 开关

父 Agent 使用：

```text
write_content_memo: true
```

省略该字段时也按 `true` 处理。它为当前 dispatch 启用文件化 memo。`false` 只关闭文件化 memo，且仅适用于 memo 成本明显高于预期复用、恢复或 handoff 价值的情况。

内部派发配置可以省略字段并使用上述 `true` 默认值。但在父级序列化 released task bundle 前，必须显式写出 `write_content_memo: true` 或 `write_content_memo: false`。Worker 只消费其 released bundle 中的显式值；如果 released bundle 省略该字段，则派发不完整，Worker 不得自行推断默认值。

### 父级授权

Worker 不得修改或重新解释该开关；只有父 Agent 可以为后续 slice 选择取值。该授权只控制 memo 文件是否物化，不授予其他范围或 capability。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Worker Content Memo](content-memo_zh_cn.md) — 定位 memo 内容契约。
- [Worker Content Memo Lifecycle](content-memo-lifecycle_zh_cn.md) — 定位 memo 生命周期规则。
