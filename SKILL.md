---
name: token-io-decoupling
description: "High-volume Agent Token I/O decoupling for Coding. Coding separates high-value input-side reasoning, implementation output, independent change verification, and the Documentation/Comments & Git Operations role for approved documentation/comments and non-trivial repository Git work, while keeping Core role and Session rules independent of any specific Code Agent product or model; runtime-environment bindings and capability checks are declared in the Coding workflow."
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

This Skill maintains one executable workflow: Coding. It separates high-value semantic decisions from high-volume project-state consumption and output materialization. Multimodal and Mixed concepts are not maintained as executable workflows in this repository.

Coding delegation and Session-topology rules are split into atomic references: the state record, mode/count gate, and conditional child dispatch/lifecycle policy. The Mode checkpoint composes and validates them before route selection; the parent-controlled record stores a conversation-wide mode/count decision and current task state. Model and reasoning-effort binding checks are limited to child creation; the child never inspects or reports its settings, and the parent does not re-check them in later child operations.

The Skill defines orchestration conventions only. It cannot bypass higher-priority permissions, user authorization, product limitations, repository instructions, or safety rules, and it must not present unmeasured claims about price, cache hits, quota savings, latency, or runtime quality as facts.

Every Coding task uses a shared task plan by default under [Task Plan Memory Lifecycle](references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md). Existing and future routes consume the same owner: confirm storage scope and repository isolation, analyze current facts, persist/read back before implementation, update before reporting new facts/progress, and record requirement changes before analysis and revised execution. Shared global plans and archives use one stable local repository key across the main checkout and linked worktrees; other repositories remain separate. That owner also defines the configured deterministic lifecycle-tool path, legacy local compatibility, and verified receipts; tool discovery alone does not establish backend availability or permission. Explicit persistence restrictions follow that owner; a plan never grants authority.

## MCP support boundary

Use this project's MCP Server only from local Codex CLI, including local ChatGPT Work through local Codex CLI. Other Code Agents, cloud ChatGPT chats, and remote ChatGPT Work are not direct MCP clients. They may use the server only after installing Codex CLI in their own environment and following this project's installation instructions for that CLI. This remains Codex CLI use, without separate host or cloud compatibility. Codex CLI tool calls do not run an environment-identification checkpoint; verify the actual capabilities, identity, permissions, and guards required by each operation. See the [MCP client boundary](mcp/AGENTS.md).

Other Code Agents may follow the Skill as documents without this MCP Server. Continue maintaining compatible instruction descriptions for those Agents while developing the MCP Server exclusively for Codex CLI. The general document workflow and its capability checks remain available for document-only use.

## Start here

Follow these steps in order. Confirm each checkpoint's outcome before advancing; if a conditional step does not apply, record why instead of silently skipping it.

1. Read the [Coding workflow](workflows/coding.md) and complete its Contract checkpoint; confirm the task constraints and acceptance criteria.
2. Complete the Environment checkpoint; establish or load the Environment capability inventory and confirm the capabilities needed by this task.
3. Complete the Mode checkpoint using that inventory. On this conversation's first Coding directive, honor an explicit valid mode/count or custom-instruction mapping without asking again. Otherwise present the four-option menu in the Mode reference. Only when the Mode gate must be released and no valid user choice is available, select option 1, `mode_source: default`, and `child_count: 1`; explicit no-preference selects the same default. Do not infer a choice from a pending prompt or a preselected option. Invalid option 3 or ambiguous/invalid option 4 input requires one focused follow-up and keeps Mode unreleased. This reserves capacity only: do not initialize a child when presenting the menu, selecting a mode, or locking the count. Later directives reuse the locked mode/count.
4. Load [Session Audit Visibility](references/coding/layer-01-fundamental-concepts/session-runtime/session-audit-visibility.md) for configuration values and display semantics. Do not resolve route-level audit prompt, timing, resume, or migration decisions before route selection.
5. After Contract, Environment, capability inventory, and Mode pass, call [Route Entry](references/coding/layer-03-workflow-checkpoints/route-entry.md) and select exactly its authorized route: [Single-Agent](references/coding/layer-04-workflows/coding-single-agent.md) for released `mode: Single-Agent Coding`, or [Multi-Agent](references/coding/layer-04-workflows/coding-multi-agent.md) for released `mode: Multi-Agent Coding` with a locked positive `child_count`.
6. Follow the selected route's numbered checkpoint sequence one step at a time. Load only the references needed for the current step; complete or explicitly disposition each step before moving to the next.
7. Return to the [Coding workflow](workflows/coding.md) when the task changes direction or before final acceptance; confirm the route's completion evidence before reporting `COMPLETE`.

## Scope

Use Coding for repository or project exploration, implementation, refactoring, debugging, tests, documentation, developer-tool output, and non-trivial Git work. The Coding workflow owns the common queue, module composition, runtime-environment selection, mode routing, checkpoints, verification boundaries, documentation/Git boundaries, and acceptance.

The optional enhanced subsystem is specified in the [Enhanced Workflow Architecture Contract](ENHANCED_ARCHITECTURE.md); the existing Native workflow remains applicable.

## Hard constraints

- Record hard user, runtime environment, repository, permission, safety, and Session constraints before acting.
- A task-level prohibition, such as “do not create subagents” or “do not use a browser,” remains active for the whole task.
- Computer Use is categorically forbidden: never control a computer, browser, or desktop app through its graphical interface — no screenshots to locate controls, mouse or keyboard simulation, clicking, accessibility APIs, window automation, remote-desktop control, or GUI scripting — and do not route such interaction through an API, CLI, MCP server, helper, or another Agent. Treat this as a blacklist rather than a list of allowed channels: every other tool, command, or capability actually exposed to and authorized for the current Session remains permitted. If a required step needs a forbidden operation, stop and report the blocker instead of attempting, delegating, or skipping it.
- Before route selection or any delegation/Session-topology work, the Mode checkpoint must compose and validate the delegation references; those references own conversation-level mode selection with a default Multi-Agent route and one-child budget, child counts, conditional creation, allocation, reuse, replacement, exceptions, and limits at their respective atomic boundaries. A reserved budget never initializes or authorizes a child by itself.
- Never invent authorization, capability, evidence, product support, or an executable route for an unmaintained scenario.
- Keep Core rules independent of product details; read [Runtime and Model Provider Support](references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support.md) for supported runtime branches and model bindings.
- Read references on demand. Do not preload the entire Skill, `references/`, or raw project state merely because it may become useful.

## Completion

Follow the selected Coding workflow and return `COMPLETE` only after its final acceptance gate has explicit evidence. Report skipped or unavailable checks, assumptions, residual risks, and unauthorized effects clearly.
