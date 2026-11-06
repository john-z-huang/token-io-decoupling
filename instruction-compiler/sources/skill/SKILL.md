---
name: token-io-decoupling-skill
description: "可选 Coding 指令与无状态事件 Hooks；独立工具不要求工作流"
---

# Token I/O Decoupling


选择 Coding 工作流时才加载本 Skill。独立工具、计划和 Memory 操作不要求本 Skill 或工作流调用顺序；每项操作保留自身当前契约及宿主授权。

## 从这里开始

读取 [Coding](workflows/coding.md)、[共享契约](references/coding/hooks/shared.md)及所选简短[单代理](references/coding/layer-04-workflows/coding-single-agent.md)或[多代理](references/coding/layer-04-workflows/coding-multi-agent.md)指令。Code Agent 根据当前目标、获准范围和真实证据选择行动，只使用当下适用的[逻辑事件](references/coding/hooks/README.md)。这些指令表达必要依赖，不由 Python 阶段执行器决定下一节点。

Agent 在自身上下文维护任务状态、运行时事实、mode/count、真实 allocation、当前证据/epoch、已尝试效果及待办。Workflow 只提供无状态方法和指令，不提供状态数据库/文件、Memory 后端、持久化或恢复服务。同 Session 各轮/compact/恢复保留已确认事实；必需上下文缺失须明确解决，不推断补全。

实际暴露且获准的本地 Codex CLI workflow server 可通过 workflow_check_event 提供事件指令及可选检查；rules_get_context 仍用于有界规则查询。结构完整不是事实真实性、权限或验收。可选模型建议具有自身 API 配置及外发要求。静态指令不需要 API、tools 服务或计划/Memory 后端。其他 Agent 使用批准的生成文档及自身获准能力，不是本 MCP server 的直接客户端。

## 硬约束

- 产生效果前遵守用户禁止条件、仓库范围、实际权限、运行限制和当前授权。职责、建议、资源 ID 或 Hash 不产生权限。
- 绝对禁止 Computer Use：不得通过截图、点击、键盘/辅助功能自动化、GUI 脚本、辅助程序或其他 Agent 操作浏览器/桌面界面。包装被禁止渠道不会使其获准。
- Multi-Agent 的 mode/count 只预留容量；真实子级工作须有当前身份、能力、匹配职责、已放行范围和父级控制返回路径。用户明确分工优先，Single-Agent 不创建子级。
- 只按当前需要消费完整、当前、同批次指令。必需指令缺失阻塞依赖工作，不推断遗漏政策或查找作者源。
- 声明完成前主动使用 completion_requested，逐项按真实最终状态证据审阅适用标准。原生 Stop 提示、模型建议或检查 schema 不能替代验收。

## 完成

报告真实结果、当前验证维度、获准效果与未解决限制。等待、阻塞或预算受限工作可按准确状态结束当前轮。独立服务与无状态交付边界见[工作流架构](WORKFLOW_ARCHITECTURE.md)。
