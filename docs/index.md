---
layout: default
title: Token I/O Decoupling
lang: en-US
---

[English](./) | [简体中文]({{ '/zh-cn/' | relative_url }})

# Token I/O Decoupling

An Agent orchestration Skill for separating semantic decisions, state consumption, and output execution.

## What it provides

The Skill routes a task to the flow that owns its primary state, then defines the responsibilities and information boundaries used during execution.

It provides one executable flow:

- **Coding Flow** for repository and development work.

Multimodal material is retained as reference content only; it is not an executable flow in this Skill.

## Coding Flow

Coding Flow covers repository and development tasks:

- progressive exploration of source and project state;
- code and configuration implementation;
- focused implementation checks;
- independent final change verification;
- approved documentation and Git operations.

Start with [`SKILL.md`](../SKILL.md), then follow the Coding references selected for the current stage.

## Multimodal reference material

The repository retains reference material for tasks that consume visual or temporal state:

- GUI and browser interaction;
- image and screenshot observation;
- video and other temporal state;
- visual-state verification;
- a narrow handoff to Coding when repository changes are required.

These references do not define a separately executable route. Start with the English [`SKILL.md`](../SKILL.md) or the Chinese [`SKILL_zh_cn.md`](../SKILL_zh_cn.md) Coding routing entry point.

## Responsibilities

| Responsibility | Function |
| --- | --- |
| Input-side Reasoning | Defines the goal, constraints, decisions, and acceptance criteria. |
| Primary Output | Explores the relevant state and materializes the approved implementation. |
| Change Verification | Independently checks the final changed state against the acceptance criteria. |
| Documentation / Git Operations | Handles approved documentation and repository Git operations. |

## Execution sequence

1. Route the task to the Coding flow; consult retained Multimodal references only when the Coding workflow explicitly names them.
2. Define a Semantic Contract containing the goal, constraints, decisions, and acceptance criteria.
3. Let the responsible output role explore state and materialize the approved direction.
4. Pass only the necessary context across responsibility boundaries.
5. Verify the final state against the acceptance criteria.

## Repository references

- [`references/`](https://github.com/john-z-huang/token-io-decoupling/tree/main/references) contains the detailed Flow, Coding, runtime, session, and execution references.
- [`MULTI_LINGUAL.md`](https://github.com/john-z-huang/token-io-decoupling/blob/main/MULTI_LINGUAL.md) defines the repository's bilingual documentation rules.
- [GitHub repository](https://github.com/john-z-huang/token-io-decoupling)
