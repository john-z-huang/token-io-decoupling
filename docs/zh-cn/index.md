---
layout: default
title: Token I/O Decoupling
lang: zh-CN
---

[English]({{ '/' | relative_url }}) | [简体中文](./)

# Token I/O Decoupling

用于分离语义决策、状态消费和输出执行的 Agent 调度 Skill。

## 提供的功能

Skill 根据任务的主要状态选择对应的 Flow，并定义执行过程中使用的职责和信息边界。

它只提供一条可执行 Flow：

- **Coding Flow**：面向仓库和开发工作。

仓库保留 Multimodal 内容作为 reference，但它不是本 Skill 中可执行的独立 Flow。

## Coding Flow

Coding Flow 覆盖仓库和开发任务：

- 渐进式探索源代码和项目状态；
- 实现代码和配置改动；
- 运行聚焦的实现检查；
- 独立验证最终变更状态；
- 执行已批准的文档和 Git 操作。

从 [`SKILL_zh_cn.md`](../../SKILL_zh_cn.md) 开始，然后按照当前阶段选择对应的 Coding reference。

## Multimodal reference

仓库保留以下需要消费视觉或时间状态的任务 reference：

- GUI 和浏览器交互；
- 图片和截图观察；
- 视频及其他时间状态处理；
- 视觉状态验证；
- 当需要修改仓库时，向 Coding 进行窄范围移交。

这些 reference 不定义独立的可执行路线。Coding 路由入口分别是英文 [`SKILL.md`](../../SKILL.md) 和中文 [`SKILL_zh_cn.md`](../../SKILL_zh_cn.md)。

## 职责

| 职责 | 功能 |
| --- | --- |
| Input-side Reasoning | 定义目标、约束、决策和验收标准。 |
| Primary Output | 探索相关状态并物化已批准的实现方向。 |
| Change Verification | 根据验收标准独立检查最终变更状态。 |
| Documentation / Git Operations | 处理已批准的文档和仓库 Git 操作。 |

## 执行顺序

1. 将任务路由到 Coding；只有 Coding 工作流明确点名时，才查阅保留的 Multimodal reference。
2. 定义包含目标、约束、决策和验收标准的 Semantic Contract。
3. 由负责输出的角色探索状态并物化已批准方向。
4. 在职责边界之间只传递必要上下文。
5. 根据验收标准验证最终状态。

## 仓库 reference

- [`references/`](https://github.com/john-z-huang/token-io-decoupling/tree/main/references) 包含 Flow、Coding、runtime、session 和 execution 的详细 reference。
- [`MULTI_LINGUAL_zh_cn.md`](https://github.com/john-z-huang/token-io-decoupling/blob/main/MULTI_LINGUAL_zh_cn.md) 定义仓库的双语文档规则。
- [GitHub 仓库](https://github.com/john-z-huang/token-io-decoupling)
