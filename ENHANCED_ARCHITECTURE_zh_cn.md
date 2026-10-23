# 增强工作流架构契约

[English](ENHANCED_ARCHITECTURE.md) | [简体中文](ENHANCED_ARCHITECTURE_zh_cn.md)

本文档负责可选增强工作流架构的组件与接口契约。它将稳定规则节点映射到既有 owner，不复制其政策正文。这是一份设计规范，不表示 MCP 服务、数据库或 API 集成已经实现或可用。

## 组件与权威数据

设计采用 `mcp/` 下独立的 Python 子项目，由 uv 管理，使用 Pydantic、`sqlite3`、官方 MCP SDK v2 和 OpenAI SDK。本地 stdio 传输的目标 MCP 协议修订为 `2026-07-28`。这些选择定义预期实现，不代表运行时能力已验证。

Markdown owner 文档仍是政策文本的唯一权威。JSON 注册表 [`mcp/rule-registry.json`](mcp/rule-registry.json) 将稳定节点 ID 映射到 owner 标题、事实、证据、分支、判断方式、失败处理和后续检查点，不得复制 owner 正文。实现加载时读取当前 owner 文本并计算 Hash；不维护第二份人工编写的政策正文或持久化节点 Hash。普通正文变化通过动态重读生效。节点结构、分支枚举或硬约束变化时，必须使用变化后的 `contract_version` 同步兼容实现与测试。

SQLite 保存结构化控制状态、证据引用、语义正文引用及 Hash、索引。完整 Contract、Decision Brief、Plan、Memo、Capsule、Handoff 等语义正文仍保存在 Markdown 或 Serena Memory 中，并遵守各自 owner。SQLite 索引不取代正式消息、可见性要求或共享 worktree 冲突控制。

## 身份与状态边界

Root 数据库是根控制状态的逻辑 Owner。Worker 数据库只包含只读任务快照，以及该 Worker 自身的进度、里程碑、局部检查、证据、阻塞项和恢复上下文。Root 仅通过授权接口读取摘要和证据，核验后执行根级状态迁移；Worker 自报不等于 Root 确认完成。

预期目录为 `~/.local/state/token-io-decoupling/<project-id>/<root-session-id>/workflow.sqlite3`，Worker 数据库位于 `subagents/<subagent-session-id>/worker.sqlite3`。Project 和 Session 绑定必须来自可信运行时上下文。调用方提供的身份、路径或 `authorized=true` 不足以建立信任。只有真实子 Agent 身份经过验证并绑定到预留 Allocation 后，才初始化 Worker 数据库。路径由可信绑定生成，并拒绝目录穿越及越界符号链接。

模式/数量、Allocation、状态 Revision、规则/Schema 兼容版本，以及 implementation/content、documentation、Git metadata 三类 Verification Epoch 是彼此独立的维度，不得互相替代。其约束政策仍由既有 owner 负责，见“相关概念”一节。

## 接口与事务契约

计划中的 MCP 接口包括公共只读能力、规则上下文和 Schema 状态操作；Parent 操作包括打开及读取工作流状态、预留/绑定 Allocation、检查/释放 Slice、评估检查点、记录证据、迁移状态、读取 Worker 摘要和协调；Worker 操作包括读取自身任务/状态、记录进度/证据、报告阻塞项及获取恢复上下文。输入采用明确类型和枚举。写入携带预期 Revision 与幂等键，并返回结果状态、原因、规则版本、证据引用、当前 Revision 和后续要求。接口不提供任意 SQL、Shell 或自由格式提示词执行。

Root 与 Worker 使用独立迁移序列，均从 `v0001` 开始。每个数据库记录自身类型及迁移版本、名称、checksum、应用时间和耗时。授权写入打开数据库时，先验证身份、权限、路径、数据库类型、迁移历史、checksum 和程序兼容性；获取每个数据库的独占迁移锁；有待执行迁移时先备份；再逐个以事务提交迁移及其历史记录。开放业务写入前校验 Schema 和完整性。只读诊断不触发迁移。已发布迁移不可修改；不提供自动降级。迁移失败会回滚当前迁移，并保留此前成功的迁移和备份。历史缺失、checksum 不符、未来 Schema、损坏或不兼容都会阻止增强写入；不得静默重建数据库。

单库状态迁移使用事务、约束、单调 Revision 检查和幂等键。跨库交换使用事件 ID 与 Parent 确认，不假设 Root 和 Worker 数据库可以原子提交。

## Native 与 Enhanced 运行

Native 是默认运行方式：Agent 阅读权威文档，并按其 owner 维护既有结构化记录和语义正文。Enhanced 是可选方式，只有可信宿主身份和实际权限边界均通过验证后，才可开放相应能力。任一条件未知或失败时，阻止依赖该能力的增强读写；在其自身所需状态可用时继续 Native 操作。

Decisions API 默认关闭。本实施阶段只通过 Mock 检验 API 行为；本文档没有授权真实请求。显式启用的 API 不可用、超时、拒绝输入或返回无效/过期结果时，语义判断切回文档路径。若 MCP 和 SQLite 仍可用，继续维护其状态。API 输出不授权操作，也不释放 Slice。

MCP 不可用时使用 Native 记录。MCP 恢复后，Root 必须先显式协调有效 Native 记录、数据库 Revision、生命周期和证据新鲜度，再恢复增强写入。协调必须保留有效 Native 记录；禁止采用“最后写入获胜”覆盖。损坏或不兼容的数据库不得通过 Native 降级直接写入。任何降级都不能绕过硬约束或必需的宿主守卫。

## 规则节点映射

机器可读映射 [`mcp/rule-registry.json`](mcp/rule-registry.json) 只是节点映射，不是政策来源。每个节点包含稳定 ID、owner 路径和实际存在的章节标题、必需事实与证据、合法分支、判断方式（`direct`、`deterministic`、`semantic` 或 `hybrid`）、失败处理和后续检查点 ID。`contract_version` 标识映射结构。ID 保持稳定，不得重新分配给其他概念。节点 Hash 从已加载的 owner 正文计算，不在注册表中维护。

注册表消费者只应加载当前检查点所需节点及其直接 owner 标题，不应扫描整个仓库。直接引用仍是解释规则的权威；确定性检查只执行明确的结构化约束；语义分类可以辅助判断，但不能授权；混合判断将语义结果与确定性硬约束校验组合。

## 相关概念

- [Coding Delegation State Record](references/coding/layer-01-fundamental-concepts/delegation-state-record_zh_cn.md) — 根控制记录的责任边界。
- [Coding Execution Control](references/coding/layer-01-fundamental-concepts/execution-control_zh_cn.md) — Slice 与控制边界的责任归属。
- [Verification Epoch Checkpoint](references/coding/layer-02-workflow-concepts/verification-epoch_zh_cn.md) — Epoch 失效规则的责任归属。
- [Coding workflow selector](workflows/coding_zh_cn.md) — 路线导航。
