# Coding Agent 推理摘要可见性

[English](reasoning-summary-visibility.md) | [简体中文](reasoning-summary-visibility_zh_cn.md)

本模块定义 Agent 在一轮推理结束时向会话展示的安全、简洁摘要；不要求披露私有内部推理，也不替代决策、阶段反馈、验证或消息可见性 owner。

## 通用规范

### 摘要边界与内容

“已完成的 Agent 推理回合”指 Agent 即将向用户或父级返回、暂停、让出控制或交接工作的可见会话边界。同一回合内的内部工具调用及继续处理无需逐项输出摘要。

在每个此类边界，于当前会话提供简洁摘要，包含当前结论或进展、关键证据及其来源、简短决策依据、重要假设/不确定性/阻塞，以及下一步。没有实质变化时，用一句话说明并指出后续动作。

### 固定可见格式

摘要必须使用以下精确 ASCII 标记包围，并让每个标记各自独占一行：`[[REASONING_SUMMARY_BEGIN]]` 和 `[[REASONING_SUMMARY_END]]`。普通答复、状态说明及其他非摘要内容均放在标记之外；不得在标记外输出未标记的推理摘要。使用会话语言，并按固定顺序完整填写以下字段：结论/进展；关键证据及来源；简短依据；重要假设/不确定性/阻塞；下一步。

没有实质变化时，仍保留两个标记及所有字段。写明“无实质变化”、无新增证据、决定或假设，并给出下一步；不得输出空块。推理回合尚未结束时，不输出空标记块。

英文示例：

```text
[[REASONING_SUMMARY_BEGIN]]
Conclusion / progress: No material change.
Key evidence and source: No new evidence.
Brief rationale: No new decision.
Material assumptions / uncertainty / blockers: No new assumptions or blockers.
Next step: Continue the released task.
[[REASONING_SUMMARY_END]]
```

简体中文示例：

```text
[[REASONING_SUMMARY_BEGIN]]
结论/进展：无实质变化。
关键证据及来源：无新增证据。
简短依据：无新增决定。
重要假设/不确定性/阻塞：无新增假设或阻塞。
下一步：继续已放行的任务。
[[REASONING_SUMMARY_END]]
```

标记只标识安全摘要，不允许输出私有逐步内部推理、隐藏思维链或原始 scratchpad。

不得包含私有逐步内部推理、隐藏思维链、原始 scratchpad、穷尽式内部过程、秘密或未核实断言。不得将摘要描述为完整的内部推理记录。

### 与其他证据的关系

摘要不能替代 Decision Brief、声明的阶段边界所需的 Progress Signal、验证证据或子代理消息可见性所要求的完整安全正文。在 Multi-Agent Coding 中，Worker 返回正文保留完整安全内容；摘要块只是其中一部分，父级仍须依据子代理消息可见性 owner 展示完整正文后再依赖。推理回合结束与阶段边界重合时，将两者所需信息合并为一个简洁可见摘要，避免重复。摘要不可见或不完整时，报告限制并阻塞依赖动作；不得声称已经展示。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有厂商专用优化；仅使用当前 Session 可见的会话输出遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有厂商专用优化；仅使用当前 Session 可见的会话输出遵循上述通用规范。

## 相关概念

- [Coding Session 职责归属](session-role-ownership_zh_cn.md)——定位职责及语义所有权。
- [Coding 执行阶段反馈](execution-stage-feedback_zh_cn.md)——定位 Progress Signal 边界。
- [Coding 子代理消息可见性](delegation-child-message-visibility_zh_cn.md)——定位完整消息正文可见性要求。
- [Coding 执行决策门](execution-decision-gate_zh_cn.md)——定位 Decision Brief 及决策职责。
