---
name: token-io-decoupling
description: "面向 Coding 的高体量 Agent Token I/O 解耦：将输入侧高价值推理、实现输出、独立改动验证，以及负责获准文档/注释与非简单仓库 Git 工作的 Documentation/Comments & Git Operations 角色分离，同时让 Core 的角色与 Session 规则保持对具体 Code Agent 产品和模型无关；运行环境绑定和能力检查由 Coding 工作流声明。"
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

当前本 Skill 只维护一套可执行工作流：Coding。它用于把高价值语义决策与高体量项目状态消费、输出物化分离。Multimodal 和 Mixed 内容目前不作为本仓库中的可执行工作流维护。

Coding 的根指令模式和委派状态由唯一权威文档决定；Coding 工作流必须在路线选择前将其与其他 Coding reference 一并加载。

本 Skill 只定义调度约定，不能绕过更高优先级的权限、用户授权、产品限制、仓库指令或安全规则，也不把价格、缓存命中、额度节省、延迟或 Runtime 质量表述为未经实测的事实。

## 从这里开始

1. 读取 [`workflows/coding_zh_cn.md`](workflows/coding_zh_cn.md)，再按唯一权威文档执行根指令模式确认门禁，然后只加载一个模式工作流：
   - 用户明确确认单代理 Coding 后，读取 [`workflows/exist-workflow/coding-single-agent_zh_cn.md`](workflows/exist-workflow/coding-single-agent_zh_cn.md)；
   - 只有用户明确确认多代理 Coding，并进一步确认正整数子 Agent 数量后，才读取 [`workflows/exist-workflow/coding-multi-agent_zh_cn.md`](workflows/exist-workflow/coding-multi-agent_zh_cn.md)。
2. 只按选定工作流和当前步骤加载所需 reference。
3. 只有任务改变方向或进行最终验收前才回到 `workflows/coding_zh_cn.md`。

## 适用范围

仓库或项目探索、实现、重构、调试、测试、文档、开发工具输出以及非简单 Git 工作均使用 Coding。Coding 工作流负责共用队列、模块组合、运行环境选择、模式路由、checkpoint、验证边界、文档/Git 边界和验收。

## 硬约束

- 采取行动前记录用户、运行环境、仓库、权限、安全和 Session 硬约束。
- “不要创建子代理”“不要使用浏览器”等任务级禁止条件在整个任务中持续有效。
- 路线选择或任何委派/Session 拓扑工作前，Coding 工作流必须加载并遵循 `references/coding/agent-delegation-control_zh_cn.md`；该文档唯一规定根指令模式确认、子 Agent 数量、创建、分配、复用、替换、例外和限制。
- 不得虚构授权、能力、证据、产品支持，或为未维护场景推导可执行路线。
- Core 规则不依赖具体产品；Coding 工作流只支持本地 Codex、ChatGPT Work 和标准 ChatGPT，并在其中检查当前界面实际提供的能力。
- 按需读取 reference。不要仅因为可能以后有用，就预加载整个 Skill、`references/` 或原始项目状态。

## 完成

遵循选定的 Coding 工作流，只有 [`workflows/coding_zh_cn.md`](workflows/coding_zh_cn.md) 中的最终验收门禁拥有明确证据后才能返回 `COMPLETE`。清楚报告跳过或不可用的检查、假设、剩余风险和未授权效果。
sed: --: No such file or directory
