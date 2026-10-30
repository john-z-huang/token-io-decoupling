---
name: token-io-decoupling-skill
description: "面向 Coding 的高体量 Agent Token I/O 解耦：将输入侧高价值推理、实现输出、独立改动验证，以及负责获准文档/注释与非简单仓库 Git 工作的 Documentation/Comments & Git Operations 角色分离，同时让 Core 的角色与 Session 规则保持对具体 Code Agent 产品和模型无关；运行环境绑定和能力检查由 Coding 工作流声明。"
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

当前本 Skill 只维护一套可执行工作流：Coding。它用于把高价值语义决策与高体量项目状态消费、输出物化分离。Multimodal 和 Mixed 内容目前不作为本仓库中的可执行工作流维护。

Coding 的委派和 Session 拓扑规则拆分为原子 reference：状态记录、模式/数量门禁，以及按条件加载的子代理派发/生命周期策略。模式检查点在路线选择前组合并验证这些 reference；父级控制的记录保存会话级模式/数量选择和当前任务状态。模型和 reasoning-effort 绑定核验仅限创建子代理时；子代理不自查或报告这些设置，父级也不在后续子代理操作中重新核验。

本 Skill 只定义调度约定，不能绕过更高优先级的权限、用户授权、产品限制、仓库指令或安全规则，也不把价格、缓存命中、额度节省、延迟或 Runtime 质量表述为未经实测的事实。

每项 Coding 任务默认按[任务计划 Memory 生命周期](references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)使用共享任务计划。现有及未来路线消费同一 owner：确认存储 scope 与仓库隔离，分析当前事实，实施前持久化/读回，新事实/进度先更新再汇报，需求变化先记录再分析并修订执行方案。共享全局规划及归档在主工作区与 linked worktrees 之间使用同一个稳定本机仓库 key，其他仓库保持隔离。该 owner 也负责已配置的确定性生命周期工具路径、旧版本地兼容行为及核验回执；仅发现工具不证明后端可用或具备权限。明确持久化限制按该 owner 处理；计划绝不授予授权。

## MCP 支持边界

本项目的 MCP Server 仅通过本地 Codex CLI 使用，包括本地 ChatGPT Work 通过本地 Codex CLI 使用的情形。其他 Code Agent、云端 ChatGPT 聊天和远端 ChatGPT Work 不是直接 MCP 客户端；只有在各自环境中安装 Codex CLI，并按本项目安装说明为该 CLI 安装 Server 后，才能通过该 CLI 使用。这仍属于 Codex CLI 使用，不另行提供宿主或云端兼容。Codex CLI 工具调用不执行环境识别检查点；仍须核验各操作实际需要的能力、身份、权限和守卫。参见 [MCP 客户端边界](../../mcp/AGENTS_zh_cn.md)。

其他 Code Agent 可以不使用此 MCP Server，通过纯文档方式遵循 Skill。MCP Server 仅面向 Codex CLI 开发，同时持续维护对这些 Agent 兼容的指令描述；通用文档工作流及其能力检查仍适用于纯文档使用。

## 从这里开始

按以下顺序逐项执行。确认当前检查点的结果后才能进入下一项；条件步骤不适用时，记录原因，不得默默跳过。

1. 读取 [Coding 工作流](workflows/coding_zh_cn.md)并完成 Contract 检查点；确认任务约束和验收条件。
2. 完成运行环境检查点；建立或加载运行环境能力清单，确认本任务所需能力。
3. 使用该清单完成模式检查点。本次会话首次 Coding 指令遵循用户明确给出的有效模式/数量选择或自定义指令映射，不再询问。否则呈现 Mode reference 中的四项菜单。只有必须放行 Mode gate 且没有有效用户选择时，才选择选项 1，记录 `mode_source: default` 和 `child_count: 1`；明确表示无偏好时也选择该缺省值。不得从待回复的提问或预选项推断用户已作选择。选项 3 数量无效，或选项 4 输入有歧义/无效时，只提出一个聚焦补问并保持 Mode 未放行。这只预留容量：展示菜单、选择模式或锁定数量均不得初始化子代理。后续指令沿用已锁定模式/数量。
4. 加载[会话审计可见性](references/coding/layer-01-fundamental-concepts/session-runtime/session-audit-visibility_zh_cn.md)，了解配置值和可见性语义。选择路线前不要解析路线级审计提问、计时、恢复或迁移决策。
5. Contract、Environment、能力清单和 Mode 通过后，调用[路线入口](references/coding/layer-03-workflow-checkpoints/route-entry_zh_cn.md)，只选择其授权路线：已释放的 `mode: Single-Agent Coding` 使用[单代理路线](references/coding/layer-04-workflows/coding-single-agent_zh_cn.md)；已释放的 `mode: Multi-Agent Coding` 且已锁定正整数 `child_count` 时使用[多代理路线](references/coding/layer-04-workflows/coding-multi-agent_zh_cn.md)。
6. 按所选路线的编号检查点顺序逐项执行。只加载当前步骤需要的 reference；每项完成或明确处置后才能进入下一项。
7. 任务改变方向或最终验收前，返回 [Coding 工作流](workflows/coding_zh_cn.md)；报告 `COMPLETE` 前确认路线的完成证据。

## 适用范围

仓库或项目探索、实现、重构、调试、测试、文档、开发工具输出以及非简单 Git 工作均使用 Coding。Coding 工作流负责共用队列、模块组合、运行环境选择、模式路由、checkpoint、验证边界、文档/Git 边界和验收。

可选增强子系统契约见[增强工作流架构契约](ENHANCED_ARCHITECTURE_zh_cn.md)；现有 Native 工作流仍然适用。

## 硬约束

- 采取行动前记录用户、运行环境、仓库、权限、安全和 Session 硬约束。
- “不要创建子代理”“不要使用浏览器”等任务级禁止条件在整个任务中持续有效。
- 绝对禁止 Computer Use：不得通过图形界面控制计算机、浏览器或桌面应用——包括以操纵控件为目的的截图、鼠标／键盘模拟、点击、辅助功能 API、窗口自动化、远程桌面控制或 GUI 脚本——也不得把此类交互包装为 API、CLI、MCP Server、辅助程序或其他 Agent 调用来绕过。本节是黑名单而非允许渠道清单：当前 Session 实际暴露且已获授权的其他工具、命令或能力仍然允许。若必需步骤需要借助被禁止的操作，应停止并报告阻塞，而不是尝试、委派或跳过。
- 路线选择或任何委派/Session 拓扑工作前，模式检查点必须组合并验证委派 references；这些 references 在各自的原子边界内规定会话级模式选择及默认多代理路线和单个子代理预算、子代理数量、条件创建、分配、复用、替换、例外和限制。预留预算本身不会初始化或授权创建子代理。
- 不得虚构授权、能力、证据、产品支持，或为未维护场景推导可执行路线。
- Core 规则不依赖具体产品；受支持的运行环境分支和模型绑定见[运行环境与模型厂商支持](references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support_zh_cn.md)。
- 按需读取 reference。不要仅因为可能以后有用，就预加载整个 Skill、`references/` 或原始项目状态。

## 完成

遵循选定的 Coding 工作流，只有其最终验收门禁拥有明确证据后才能返回 `COMPLETE`。清楚报告跳过或不可用的检查、假设、剩余风险和未授权效果。
