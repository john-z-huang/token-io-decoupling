---
name: token-io-decoupling
description: "High-volume Agent Token I/O decoupling for Coding. Coding separates high-value input-side reasoning, implementation output, independent change verification, and the Documentation/Comments & Git Operations role for approved documentation/comments and non-trivial repository Git work, while keeping Core role and Session rules independent of any specific Code Agent product or model; runtime-environment bindings and capability checks are declared in the Coding workflow."
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

This Skill maintains one executable workflow: Coding. It separates high-value semantic decisions from high-volume project-state consumption and output materialization. Multimodal and Mixed concepts are not maintained as executable workflows in this repository.

Coding delegation and Session-topology rules are split into atomic references: the state record, mode/count gate, and conditional child dispatch/lifecycle policy. The Mode checkpoint composes and validates them before route selection; the task control record stores the confirmed per-task state.

The Skill defines orchestration conventions only. It cannot bypass higher-priority permissions, user authorization, product limitations, repository instructions, or safety rules, and it must not present unmeasured claims about price, cache hits, quota savings, latency, or runtime quality as facts.

## Start here

1. Read [Coding workflow](workflows/coding.md), complete the Contract checkpoint, then complete the Environment checkpoint and establish or load the Environment capability inventory. The Mode checkpoint then consumes that established inventory and releases exactly one mode workflow:
   - [Single-Agent route](references/coding/layer-03-workflows/coding-single-agent.md) when the task control record contains `mode: Single-Agent Coding`;
   - [Multi-Agent route](references/coding/layer-03-workflows/coding-multi-agent.md) when it contains `mode: Multi-Agent Coding` and a locked positive `child_count`.
2. Load only the references required by the selected workflow and current step.
3. Return to `workflows/coding.md` only when the task changes direction or before final acceptance.

## Scope

Use Coding for repository or project exploration, implementation, refactoring, debugging, tests, documentation, developer-tool output, and non-trivial Git work. The Coding workflow owns the common queue, module composition, runtime-environment selection, mode routing, checkpoints, verification boundaries, documentation/Git boundaries, and acceptance.

## Hard constraints

- Record hard user, runtime environment, repository, permission, safety, and Session constraints before acting.
- A task-level prohibition, such as “do not create subagents” or “do not use a browser,” remains active for the whole task.
- Before route selection or any delegation/Session-topology work, the Mode checkpoint must compose and validate the delegation references; those references own root-directive mode confirmation, child counts, creation, allocation, reuse, replacement, exceptions, and limits at their respective atomic boundaries.
- Never invent authorization, capability, evidence, product support, or an executable route for an unmaintained scenario.
- Keep Core rules independent of product details; read [Runtime and Model Provider Support](references/coding/layer-01-fundamental-concepts/runtime-provider-support.md) for supported runtime branches and model bindings.
- Read references on demand. Do not preload the entire Skill, `references/`, or raw project state merely because it may become useful.

## Completion

Follow the selected Coding workflow and return `COMPLETE` only after its final acceptance gate has explicit evidence. Report skipped or unavailable checks, assumptions, residual risks, and unauthorized effects clearly.
