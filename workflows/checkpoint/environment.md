# Environment Checkpoint

[English](environment.md) | [简体中文](environment_zh_cn.md)

## Actions

1. Read explicit runtime metadata in the current system, developer, and application context. If that metadata names local Codex, ChatGPT Work, or standard ChatGPT, use it as the primary fact.
2. Use the callable tool inventory, workspace roots, permission profile, sandbox details, and other exposed task metadata as corroborating evidence. A local shell, worktree, model name, or tool pattern alone does not uniquely identify the runtime environment.
3. If authorized by the current task, inspect only non-sensitive runtime metadata exposed by local process or environment information; never print or persist credentials or tokens.
4. Do not use a browser, GUI navigation, screenshots, or visual page content to identify the runtime environment.
5. Classify the runtime environment into exactly one supported branch:
   - **Local Codex**: the task exposes local filesystem/shell or worktree capabilities and Codex Agent tools.
   - **ChatGPT Work**: the task exposes Work sessions/connectors/files, but local execution is not implied.
   - **Standard ChatGPT**: no local execution or independent Session capability is assumed unless explicitly exposed.
6. If the runtime environment does not fit any branch, mark the environment unsupported and stop work that depends on it.
7. Record only capabilities directly exposed by the current surface: model identity and parameter controls, Session topology, filesystem and sandbox access, tools, connectors, authentication, and any available return path for delegated work.
8. Mark an unobserved capability as unknown. Do not substitute another runtime environment, model, parameter, Session, tool, permission, or inferred capability.
9. If the evidence still leaves the runtime environment ambiguous, stop the dependent work and return this exact question to the user: `I cannot determine the current runtime environment from the available metadata. In your next instruction, explicitly state whether it is "local Codex", "ChatGPT Work", or "standard ChatGPT", then resume.`

## Pass condition

The actual runtime environment is uniquely classified from explicit metadata or the user has supplied the fallback clarification, and the next workflow has a current capability inventory to evaluate. This checkpoint does not decide whether that inventory is sufficient for Single-Agent or Multi-Agent Coding.

## Boundary

This checkpoint does not choose an execution mode, bind a model to a role, authorize delegation, require an independent verifier, decide how a runtime-environment-specific tool may be used, implement changes, or claim that an unobserved operation was performed.
