# Worker Content Memo

本模块只定义 Worker 文件化执行 memo 的语言、开关、内容边界和生命周期，不定义 Agent 拓扑、上下文传输、权限或任务验收。

## 范围与语言

Memo 是保存在 Worker 专属 context 目录中的精简执行状态文档。Worker 编写的上下文 prose 使用**中文**。路径、文件名、命令、symbol、配置 key、hash、准确错误文本和日志片段保持原文。机械复制的源文档保留来源语言和内容。本规则不改变代码注释、commit、Issue/PR、README、产品文档或用户消息的语言。

## Dispatch 开关

父 Agent 使用：

```text
write_content_memo: true
```

省略该字段时也按 `true` 处理。`true` 表示在出现可复用执行状态后维护精简 memo。`false` 只关闭文件化 memo，且仅适用于 memo 成本明显高于预期复用、恢复或 handoff 价值的情况。Worker 不得修改这个开关；父 Agent 可以为后续 slice 重新选择值。

## Memo 内容与生命周期

使用 `content-memo.md`，或使用一个已被明确标识为 memo 的等价既有文档。只记录稳定、可复用的状态：

- 已完成结果和相关发现；
- 变更路径或 symbol；
- 验证状态和准确证据指针；
- 可避免重复的失败方案；
- 剩余工作、阻塞或 handoff 需求。

首次出现可复用状态时创建或更新，并在实质里程碑、阻塞边界、handoff、替换或正常退出时更新。不要写成逐命令日志。禁止写入完整日志、完整 diff、大段源码副本、秘密、私有推理和无关历史。父 Agent 或获准的接手 Agent 必须能从 Worker 本地索引定位它。

`write_content_memo: false` 时，Worker 仍须遵守已放行范围、return conditions、授权和必要检查，并向父 Agent 返回完成当前 slice 所需的压缩结果与证据。如果后续 handoff 缺少足够事实，父 Agent 只能记录当前确知内容，不得虚构或重建不存在的历史。

最小派发形式：

```text
Objective: 修复已确认的 token-refresh 边界
Own Context RW: <context-directory>
write_content_memo: true
```
sed: --: No such file or directory
