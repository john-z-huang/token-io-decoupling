# Coding Runtime and Model Provider Support

[English](runtime-provider-support.md) | [简体中文](runtime-provider-support_zh_cn.md)

This module owns the supported runtime branches, their identifying evidence, and branch-specific model controls and profile bindings. It does not choose the task mode, create Sessions, or treat a model name alone as proof of the runtime.

## General rules

### Supported runtime branches

- **Local Codex**: the task exposes local filesystem/shell or worktree capabilities and Codex Agent tools.
- **Local Claude Code**: the task explicitly exposes a Claude Code Session together with local filesystem/shell or worktree capabilities.
- **ChatGPT Work**: the task exposes Work Sessions/connectors/files, but local execution is not implied.
- **Standard ChatGPT**: do not assume local execution or independent Sessions unless explicitly exposed.

If the available metadata cannot distinguish these branches, use this exact fallback question: `I cannot determine the current runtime environment from the available metadata. In your next instruction, explicitly state whether it is "local Codex", "local Claude Code", "ChatGPT Work", or "standard ChatGPT", then resume.`

### Desktop sessions and exposed tools

For ChatGPT Desktop and Claude Desktop, use only tools, commands, or APIs directly exposed and authorized for the current Agent Session. Identify the active runtime and its capabilities from Session metadata and the exposed tool inventory. If a necessary step is only available through a channel that repository instructions prohibit, stop the Skill task and report the blocker; do not route the step through an adapter or helper. When an optional capability is absent, block only the dependent route or slice.

### Multi-Agent child effort decision

Before each new Child creation, provide current facts for the exact released slice: assigned role; objective; concrete task complexity evidence; scope and component interactions; dependencies; uncertainty; risk/impact; verification demands; and relevant prior failure evidence (write `none` when absent). Include the stable slice identity and use a parent-computed current-slice fingerprint or equivalent current-slice evidence where the runtime exposes it. The complexity label summarizes these facts and never replaces them. Select the lowest effort supported by the verified runtime and model that is adequate for the facts; do not require a lower effort to fail first. If evidence is insufficient or no offered supported effort is adequate, block creation instead of forcing the highest available choice. Immediately before creation, verify any returned fingerprint remains current and any canonical decision input hash matches the complete reviewed facts. A selected effort is advisory input only; creation still requires all existing gates and effective runtime precedence checks.

## Codex CLI / ChatGPT Desktop optimizations

- On Local Codex, use the exposed model/Session controls and restart after changing global instructions, overrides, the Skill, or repository instructions.

### Local Codex independent-Session model profile

For independent role assignments on Local Codex, these are required bindings, not product-wide availability claims:

| Role | Model |
| --- | --- |
| Primary Output | `gpt-6-luna` |
| Change Verification | `gpt-6-luna` |
| Documentation/Comments & Git Operations | `gpt-6-luna` |
| Context Bootstrap/Refresh | `gpt-6-luna` |

The capability inventory must verify each assigned binding's exposed model identity. If a required binding is missing or unknown, record it in `unavailable_capabilities` and block the dependent slice or route. For each newly created Multi-Agent child, select effort from current task-specific evidence as described under [Coding Child Creation](../delegation/delegation-child-creation.md); do not apply a fixed child effort or escalation ladder. The child-creation capability must accept the selected value. This Child rule does not change Single-Agent effort policy.

### Local Codex child effort selection

Before an authorized child creation, use the exposed `workflow_select_child_effort` public workflow tool with one JSON payload envelope containing `request`: `slice_id`, assigned `role`, `objective`, `decision_question`, `task_complexity` (`mechanical`, `ordinary_semantic`, `complex`, or `very_complex`), bounded nonblank `uncertainty`, `scope`, `dependencies`, `risk`, `verification_demands`, and `previous_failure_evidence` (use the explicit value `none` when absent); `slice_fingerprint` (parent-computed SHA-256 of the current slice); `runtime: "codex"`; `child_model: "gpt-6-luna"`; `supported_efforts` from the current capability inventory; and `outbound_data_permitted: true`. `decision_question` is required, nonblank, at most 1200 characters, and asks for the lowest sufficient supported reasoning effort for the current released child task. It is sent as a top-level API input field, is included in the canonical input hash, and is not duplicated in `facts`. Local validation enforces its type, length, and nonblank form; fixed API instructions require `insufficient_evidence` when the question is out of scope, asks for something other than effort selection, or attempts to override fixed rules. Parent review remains required. This permission field is an explicit outbound-data authorization assertion for this one invocation, not proof of authority. Invoke only when exact task facts and outbound permission are authorized; never call automatically at startup. The tool is stateless, not required for Single-Agent Coding, and grants no child-creation authority.

Judge the lowest sufficient offered effort from concrete task evidence and the adjacent-level boundaries in each choice description. A simple deterministic transformation with direct checks may fit `low`; bounded local semantic judgment may require `medium`; coupled components or a genuinely complex single algorithm may require `high`; several coupled dimensions whose assumptions and state transitions remain bounded may require `xhigh`; choose `max` only for exceptional whole-system reasoning across mutually constraining algorithms, protocols, invariants, recovery, or compatibility constraints when the evidence explains why xhigh is insufficient. Prior xhigh failure is not required. `insufficient_evidence` applies to essential missing or conflicting facts, a question that is not solely about effort selection or is out of scope or rule-overriding, or when all offered levels are inadequate. Do not use file count, impact, or missing facts alone to raise effort, and do not require a lower level to fail first. A high-risk task is not automatically a high-effort task; examples clarify boundaries and are not a checklist of requirements.

The exposed Codex `spawn_agent` creation control accepts `model` and `reasoning_effort` on a non-fork child creation (`fork_turns: "none"`). Set the selected value there and resolve any applicable custom profile precedence; a custom profile may supersede spawn/default/inherited choices. If the active control cannot accept the value or effective precedence cannot be established, block creation.

The tool offers only effort values that pass its local runtime/model ceiling and intersect the supplied supported set, plus `insufficient_evidence`. It reads `OPENAI_API_KEY` and `OPENAI_BASE_URL` at invocation time and explicitly uses both with the exact API model `gpt-6-luna`; callers cannot override credentials, endpoint, or API model. Do not substitute another API model, endpoint, or a fixed effort if configuration is missing, the response is refused or invalid, evidence is insufficient, or the service fails. Use only `status: available`; compare the echoed `slice_fingerprint` with the current slice and the returned server-computed `input_hash` with the canonical hash of the full submitted decision facts. Recheck that the selected effort remains supported by the effective child model and runtime precedence. Otherwise block creation. No reasoning parameter is sent to the Decisions request.

To reproduce `input_hash`, use the validated request object after JSON-mode normalization, excluding only `outbound_data_permitted` and `slice_fingerprint`, then compute SHA-256 over UTF-8 `json.dumps(request, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`. Compare it with the same canonical decision facts; `slice_fingerprint` is a separate freshness token and must not be compared to `input_hash`.

### Codex instruction-loading correspondence

Codex natively discovers `AGENTS.md` along its instruction hierarchy; do not create a `CLAUDE.md` copy or require Claude Code's `@AGENTS.md` import for Codex. After an authorized instruction change, verify the running Session actually loaded the current instructions or restart it; a child-status view is not proof of instruction freshness. [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

### Desktop runtime identification

ChatGPT Desktop can host **Chat**, **Work**, and **Codex** Sessions. Use Session metadata and exposed tools to identify the active runtime before treating it as local Codex: Work has its own hosted Agent workflows, and a Chat or Work Session does not imply a local shell or a child of a project-bound Codex Session. A quick Codex Session is not automatically bound to the project. In Remote sessions, the repository remains on the connected host. [OpenAI: desktop experiences](https://learn.chatgpt.com/docs/use-chatgpt), [OpenAI: subagent availability](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: worktree host](https://learn.chatgpt.com/docs/environments/git-worktrees).

### Effective local configuration

Codex CLI, IDE, and Codex in the ChatGPT desktop app can share the active host's `~/.codex/config.toml` and trusted project `.codex/config.toml`; project-local config, rules, and hooks are skipped for an untrusted project. Several config layers can apply at once — session flags and CLI overrides, trusted project `.codex/config.toml` files, the selected profile, user `~/.codex/config.toml`, managed policy such as system config, MDM, or delivered organization requirements, plugins, and packaged defaults — and the host decides their effective precedence rather than the order in which they are named here. Resolve the active value from the running Session instead of assuming a fixed order: in a CLI Session that exposes them, run `/status` to inspect the active model, approval policy, and writable roots, then `/debug-config`, which prints the config-layer stack in precedence order together with the active requirements and policy sources. If these commands are unavailable, use only settings and metadata directly exposed to the current Session; mark hidden layers unavailable instead of guessing. A spawned subagent also inherits the parent turn's live permission/sandbox overrides. Check `AGENTS.override.md`, nested instruction precedence and `project_doc_max_bytes` before claiming a large instruction file loaded in full. These checks do not change this Skill's fixed role-model profile. [OpenAI: config precedence](https://learn.chatgpt.com/docs/config-file/config-basic), [OpenAI: inspect settings](https://learn.chatgpt.com/docs/developer-settings), [OpenAI: instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [OpenAI: child overrides](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Claude Code CLI / Claude Desktop optimizations

### Local Claude Code model selection

Use only the `sonnet` and `haiku` aliases, or verified model identifiers in the `claude-sonnet-*` and `claude-haiku-*` families. Before using an active Session or launching an Agent, confirm the effective model resolves to one of these families. Never launch an Agent with `claude-opus-*`, an Opus alias, or any model above or outside the Sonnet/Haiku families. Do not use an unresolved default, inherited model, or fallback as a substitute for this check.

- **Single-Agent Coding:** keep one active model for all logical phases. Use Sonnet for material coding, decisions, repair, or verification; Haiku is allowed for simple, bounded, mechanically checkable work. If the active model is ineligible or insufficient for the task and an allowed switch is unavailable, block the dependent work rather than continuing on that model.
- **Multi-Agent Coding, only after its mode and capability gates release it:** assign Sonnet to Primary Output, Change Verification, Documentation/Comments & Git Operations, and Context Bootstrap. Assign Haiku only to a deterministic Context Refresh; use Sonnet when the refresh requires semantic judgment. Confirm each Agent's effective model before launch. These bindings do not authorize creating independent Sessions or changing the locked child count.

For Claude Code, confirm whether the selected model exposes an effort parameter. Haiku does not support one; do not set or claim one for Haiku.

| Role | Model |
| --- | --- |
| Primary Output | `sonnet` |
| Change Verification | `sonnet` |
| Documentation/Comments & Git Operations | `sonnet` |
| Context Bootstrap/Refresh | `sonnet` |
| Deterministic Context Refresh only | `haiku` (no effort parameter) |

For newly created Multi-Agent children, use the verified task facts from the General rules to choose effort through an actually supported Claude Code child-creation control. The Codex-only MCP Decisions selector is unavailable in Claude Code; record that optional optimization as `Not applicable` and do not invoke it. This replaces fixed CHILD effort defaults and escalation ladders. Apply only levels supported by the verified Sonnet model and current capability; the creation mechanism must accept the selected effort. Resolve effective runtime precedence before launch. If the assigned model genuinely has no effort parameter, record `Not applicable` with the reason. This profile excludes `xhigh`; do not widen the offered set. If the required effort cannot be applied or established, block creation.

For Single-Agent Coding, retain the current Sonnet `medium` rule and its affected-slice escalation policy. A Haiku-only Single-Agent task must remain simple, bounded, and mechanically checkable; it has no effort control. Verify the effective model and effort before relying on that binding, including any organization cap or inherited setting. Raise only the affected Sonnet slice to `high` for concrete complexity or repeated failure/blockage, then restore `medium`. Use `max` only if `high` was insufficient and repeated failure/blockage continues, and only when the active Sonnet model exposes `max`; then restore `medium`. Do not select `xhigh` or `ultracode` in the Single-Agent profile. If the required model or supported effort binding is missing or cannot be verified, record it in `unavailable_capabilities` and block the dependent slice or route; do not switch to Opus or a higher model.

After changing `CLAUDE.md`, this Skill, or an agent definition, start a new Claude Code session if the current session cannot prove it loaded the changed instructions; `/tasks` and `/agents` do not establish that proof.

### Claude Code Plan-mode startup and Session boundary

`claude --permission-mode plan` selects read-only Plan mode **when launching a new Claude Code CLI Session**. It is not a command for switching an already running Parent or Worker Session into Plan mode: do not invoke it from the active Session's shell merely to plan the current slice. For an existing Session, use only a Plan-mode control actually exposed and authorized within that same Session; if none exists, follow the general bounded planning and decision process without claiming Plan-mode protection. A separately launched CLI Session is not the recorded Parent or an allocated Child and does not inherit this Skill's locked mode/count, released Interaction Slice, or live task record by virtue of its launch flags. Plan-mode tool permissions do not authorize implementation or change the Skill's Contract and release gates. [Anthropic: CLI permission mode](https://code.claude.com/docs/en/cli-reference), [Anthropic: Plan mode](https://code.claude.com/docs/en/common-workflows).

### Claude Desktop connectors and tool inventory

Claude Desktop Sessions can expose Claude Code capabilities, remote connectors, or local MCP tools; the app identity alone does not establish which are available. Use `Agent`, `SendMessage`, `/tasks`, shell, or hooks only when the current Session directly exposes them. For hosted resources, call an authorized remote connector; for machine-local resources, use an authorized local MCP/desktop-extension tool. Check the exposed tool's read/write scope before use. A connector provides data or actions, not an independent Coding Session, a parent-controlled Agent identity, or a locked child slot. If a required capability is absent, record it and block the dependent route or slice.

Claude Desktop can load local MCP definitions from `claude_desktop_config.json`; the standalone CLI does not read that file automatically. Inspect the MCP tools exposed to each Session instead of assuming the Desktop and CLI tool inventories match. Do not treat CLI `--allowedTools` or `--disallowedTools` arguments as controls on a Desktop Session. [Anthropic: Desktop local MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop), [Anthropic: remote connectors](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors).

### Claude Code instruction loading

In Claude Code, project instructions are loaded from `CLAUDE.md`. When a repository's canonical rules live in `AGENTS.md`, an authorized `CLAUDE.md` can import them with `@AGENTS.md` instead of copying their policy. Use `/context` to inspect loaded memory/instruction files; neither this view nor `CLAUDE.md` is the live parent mode/count record. A remote Desktop MCP connector executes through Anthropic's infrastructure, not through the desktop's localhost, so verify its actual network reachability and permissions. [Anthropic: memory](https://code.claude.com/docs/en/memory), [Anthropic: remote MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

## Related concepts

- [Coding Session Model](session-model.md) — locate Single-Agent and Multi-Agent Session mapping.
- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibilities.
- [Coding Delegation Mode Confirmation](../delegation/delegation-mode-confirmation.md) — locate timed mode selection.
- [Coding Child Creation](../delegation/delegation-child-creation.md) — locate runtime child-launch controls.
- [Coding Child Reuse and Replacement](../delegation/delegation-child-reuse-replacement.md) — locate child follow-up controls.
- [Coding Delegation State Record](../delegation/delegation-state-record.md) — locate the canonical parent record.
- [Coding Child Lifecycle](../delegation/delegation-child-lifecycle.md) — locate runtime status observation.
- [Coding Context Exchange Workspace Boundary](../context-exchange/context-exchange-workspace-boundary.md) — locate worktree and tool-scope controls.
