# Coding 委派模式确认

[English](delegation-mode-confirmation.md) | [简体中文](delegation-mode-confirmation_zh_cn.md)

本文档负责会话首次的模式选择、默认值、选择前限制以及单代理路线限制。它消费并更新状态记录；不定义数量锁定、重新进入、子 Agent 创建或生命周期。

## 通用规范

### 会话模式选择

宿主识别的 Session 生命周期中，第一次 Coding 指令到达后，根父级必须：

1. 直接遵循指令中明确给出的有效模式/数量选择，不再询问。
2. 若没有有效选择，呈现以下编号菜单。只有必须放行 Mode gate 且仍没有有效用户选择时，才采用所示缺省值；仅仅尚未收到对提问的回复，并不要求放行门禁。用户明确表示无偏好时也选择缺省值：
   1. Multi-Agent Coding，1 个子代理（推荐且缺省）。
   2. Single-Agent Coding，0 个子代理。
   3. Multi-Agent Coding，自定义正整数子代理数（通过自由文本填写整数）。
   4. 自定义指令（通过自由文本填写完整指令，并映射到受维护的模式和有效数量）。
3. 选项 3 必须提供明确正整数。若缺失或无效，只提出一个聚焦的补充问题，并保持 Mode gate 未放行；不得替换为 1。选项 4 的文本只用于推导受维护的 Single-Agent 或 Multi-Agent 路线及有效数量，同时记录其他任务约束。若文本缺失、无效、有歧义、冲突或要求未维护的路线，提出一个聚焦澄清并保持门禁未放行。自定义文本不得覆盖更高优先级的权限、安全、仓库、用户授权或能力边界，也不能创建路线或能力。
4. 将有效用户选择记录为 `mode_source: explicit`。将无回复或明确无偏好时的缺省选择记录为 `mode_source: default`、`mode: Multi-Agent Coding`、`child_count: 1`。路线放行前应用数量 owner。模式在完整宿主 Session 生命周期内固定，而非只对一次用户/助手交互生效。后续指令、compact 和同一 Session 的恢复均沿用它。初始数量也保持固定，唯一例外是数量门禁在用户实际明确批准为不同且未占用职责增加一个名额后，恰好增加一。该流程不重新打开模式选择。具有新 Session 身份的 Fork 必须按 Re-entry owner 重新完成模式/数量选择，不继承来源 Session 的选择。
5. 将已放行的 Multi-Agent 数量视为仅预留容量。展示菜单、选择模式或锁定数量均不会创建或初始化子代理；创建仍受职责、输出类型和已放行切片门禁约束。

默认值只选择工作模式和预留数量，不绕过任务级禁止事项，也不创造能力。更高优先级规则禁止子代理时，必须遵循该规则。缺少所需记录能力时，阻塞依赖路线，不得假装记录存在。

只有数量门禁放行有效正整数数量、相关职责和具体切片均已放行，且输出属于代码/配置实现或本 Skill 指令/参考文档的编写编辑时，才可创建子代理。普通非 Skill 文档由根父级编写，即使任务同时包含代码修改也一样。如果本次会话已经锁定为单代理 Coding，遇到冲突的后续指令时先遵循模式重新进入 owner。

### 单代理 Coding

确认后所有工作保留在当前 Session。不得创建、fork、handoff、消息联系、替换或管理子 Agent 或额外 Session。结构收益、验证、文档/Git、bootstrap、恢复或运行便利都不是例外。独立验证仍是语义要求，但该路线不可用。

## Codex CLI / ChatGPT Desktop 特别优化指令

### ChatGPT Desktop

仅当当前活动运行时实际暴露 `request_user_input_async` 时，才可用一个问题展示菜单并提供自由文本输入，例如：`request_user_input_async({questions: [{title: "选择 Coding 模式", options: ["1. Multi-Agent Coding，1 个子代理（推荐/缺省）", "2. Single-Agent Coding，0 个子代理", "3. Multi-Agent Coding，自定义正整数子代理数", "4. 自定义指令"]}]})`。该工具最多接受 1–3 个问题；设置选项仍允许自由文本回答，答案会异步地作为新用户消息到达。预选的第一个选项不代表用户已提交选择。工具不能只在选项 3 或 4 时条件显示输入框，因此须在同一提示中说明选项 3 填写正整数、选项 4 填写完整指令；输入缺失或无效时，按通用规则进行聚焦补问。等待回复期间不得推断用户选择。如果没有收到有效选择且必须放行 Mode gate 才能继续，才采用缺省值；不得引入计时器。若未暴露此工具，则以普通文本发送编号菜单，通过常规对话接收回复。不得用 GUI 或 Computer Use 展示或操作菜单。

### Codex CLI

在 Codex CLI 中以纯文本呈现四项编号菜单，例如 `1. Multi-Agent Coding，1 个子代理（推荐/缺省）；2. Single-Agent Coding，0 个子代理；3. Multi-Agent Coding，自定义正整数子代理数；4. 自定义指令`。通过后续文本回复接收选择，例如 `3: 4` 或 `4: ...`（后者填写完整自定义指令）；不假设存在结构化表单。如果没有收到有效选择且必须放行 Mode gate 才能继续，才采用缺省值；不得引入计时器。本 Session 不假定存在结构化表单/输入工具，因此不得声称有条件输入框。终端无法传递回复时，除非必须放行门禁才能继续，否则保持门禁未放行；必须继续时遵循通用缺省值或聚焦补问规则，不引入等待时限。

## Claude Code CLI / Claude Desktop 特别优化指令

若当前 Claude Code Session 实际暴露并授权 `AskUserQuestion`，以 `questions` 数组调用；每个问题提供 `question`、`header` 和 `options`（每个选项含 `label` 与 `description`），本次单一模式选择设置 `multiSelect: false`。例如：`AskUserQuestion({questions: [{question: "本次会话使用哪种 Coding 模式？", header: "Mode", options: [{label: "1. Multi-Agent Coding", description: "预留 1 个子代理（推荐/缺省）。"}, {label: "2. Single-Agent Coding", description: "使用 0 个子代理。"}, {label: "3. Multi-Agent Coding", description: "填写自定义正整数子代理数。"}, {label: "4. 自定义指令", description: "映射到受维护的模式和数量。"}], multiSelect: false}]})`。用户可以选择选项，或通过 `Other`/备注栏输入自由文本；对文本执行通用校验和澄清规则。问题默认保持打开并等待用户回答。只有用户设置 `askUserQuestionTimeout` 为 `60s`、`5m` 或 `10m` 时才可能自动继续；不得更改该设置或引入隐式超时。若工具结果报告超时，按返回结果处理，不得虚构用户选择；只有必须放行 Mode gate 时才应用通用的无有效选择缺省规则。工具不可用时，以普通文本提出相同的编号菜单。

## 相关概念

- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位数量锁定归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。
