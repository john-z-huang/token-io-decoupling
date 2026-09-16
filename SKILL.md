sed: --: No such file or directory
---
name: token-io-decoupling
description: "High-volume Agent Token I/O decoupling for Coding. Coding separates high-value input-side reasoning, implementation output, independent change verification, and the Documentation/Comments & Git Operations role for approved documentation/comments and non-trivial repository Git work, while keeping Core role and Session rules independent of any specific Code Agent product or model; runtime-environment bindings and capability checks are declared in the Coding workflow."
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

This Skill maintains one executable workflow: Coding. It separates high-value semantic decisions from high-volume project-state consumption and output materialization. Multimodal and Mixed concepts are not maintained as executable workflows in this repository.

Coding delegation and Session-topology decisions are defined exclusively by `references/coding/agent-delegation-control.md`; the Coding workflow loads that authority together with the other Coding references before route selection.

The Skill defines orchestration conventions only. It cannot bypass higher-priority permissions, user authorization, product limitations, repository instructions, or safety rules, and it must not present unmeasured claims about price, cache hits, quota savings, latency, or runtime quality as facts.

## Start here

1. Read [`workflows/coding.md`](workflows/coding.md), then load and follow `references/coding/agent-delegation-control.md` before substantive work. Load exactly one mode workflow according to that authority:
   - [`workflows/exist-workflow/coding-single-agent.md`](workflows/exist-workflow/coding-single-agent.md) for its recorded Single-Agent outcome;
   - [`workflows/exist-workflow/coding-multi-agent.md`](workflows/exist-workflow/coding-multi-agent.md) for its recorded Multi-Agent outcome.
2. Load only the references required by the selected workflow and current step.
3. Return to `workflows/coding.md` only when the task changes direction or before final acceptance.

## Scope

Use Coding for repository or project exploration, implementation, refactoring, debugging, tests, documentation, developer-tool output, and non-trivial Git work. The Coding workflow owns the common queue, module composition, runtime-environment selection, mode routing, checkpoints, verification boundaries, documentation/Git boundaries, and acceptance.

## Hard constraints

- Record hard user, runtime environment, repository, permission, safety, and Session constraints before acting.
- A task-level prohibition, such as “do not create subagents” or “do not use a browser,” remains active for the whole task.
- Before route selection or any delegation/Session-topology work, the Coding workflow must load and follow `references/coding/agent-delegation-control.md`; it is the sole authority for root-directive mode confirmation, child counts, creation, allocation, reuse, replacement, exceptions, and limits.
- Never invent authorization, capability, evidence, product support, or an executable route for an unmaintained scenario.
- Keep Core rules independent of product details; the Coding workflow supports only local Codex, ChatGPT Work, and standard ChatGPT, and contains the checks for their exposed capabilities.
- Read references on demand. Do not preload the entire Skill, `references/`, or raw project state merely because it may become useful.

## Completion

Follow the selected Coding workflow and return `COMPLETE` only after the final acceptance gate in [`workflows/coding.md`](workflows/coding.md) has explicit evidence. Report skipped or unavailable checks, assumptions, residual risks, and unauthorized effects clearly.
