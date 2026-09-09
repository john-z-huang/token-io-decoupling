# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` is an Agent orchestration Skill for hosts that support Agent Skills. It separates high-value semantic decisions from high-volume raw-state consumption and output materialization so the parent reasoning context does not have to continuously absorb low-decision-density repository state or visual world state.

The project contains two independent flows rather than one universal multi-Agent topology:

- **Coding Flow** is the actively maintained focus. Input-side Reasoning owns high-value decisions; Primary Output owns repository exploration, implementation/materialization, raw tool output, debugging, and mechanical verification. Coding Core is independent of concrete Code Agent products and model names; a Runtime Contract selects the Host Adapter and Model Profile for the current deployment.
- **Multimodal Flow** remains available for Computer Use, Browser Use, video, large image/screenshot collections, visual design, and related high-volume visual/temporal state. Its existing architecture is preserved as a separate routed flow. Current Multimodal deployment bindings are isolated from the root Skill rather than generalized without testing.

## Architecture

### Coding: responsibility, runtime, and host are separate concerns

```text
Coding Flow
    │
    ├─ Input-side Reasoning responsibility
    └─ Primary Output responsibility
              │
              ▼
      Coding Runtime Contract
              │
              ▼
        Runtime Registry
          ┌───────┴────────┐
          ▼                ▼
     Host Adapter      Model Profile
       "how"              "who"
          └───────┬────────┘
                  ▼
       concrete Sessions / models /
       execution parameters
```

The separation is deliberate:

- **Core responsibilities** define who owns decisions, project state, materialization, verification, and context.
- **Host Adapter** defines how a Code Agent product creates/reuses independent Sessions, exposes model/runtime parameters, loads persistent instructions, and maps sandbox/filesystem capabilities.
- **Model Profile** defines which concrete runtime is eligible for each role, task-specific execution parameters, targeted escalation, and unavailable handling.

A model being technically capable of implementation does not automatically make it eligible for Primary Output. Eligibility is deployment policy and can intentionally keep high-volume execution away from the parent reasoning Session.

### Single-Session versus normal two-Session Coding

Coding Core contains no product- or model-specific “single-agent” branch. The active Runtime derives the topology:

- use **Single-Session Coding Mode** when the current Session is explicitly eligible for both Coding responsibilities, can satisfy the required runtime parameters, and there is no independent structural reason to split;
- use **normal two-Session mode** when the current Session owns input-side reasoning but the active Profile requires a separate Primary Output runtime;
- create additional Sessions only for concrete benefits such as fresh verification, real parallelism, model tiering, context-capacity recovery, explicit isolation, or Profile-defined targeted escalation.

Repository size, long output, build/test work, or generic task complexity are not reasons by themselves to create another substantive Primary Output Session.

## Coding Flow mechanisms

The Coding Flow keeps the architecture that has been iterated in this project while removing concrete runtime bindings from Core documents:

- **Semantic Contract** stabilizes `Goal`, `Constraints`, `Decisions`, and `Acceptance` without re-encoding complete context.
- **Context Firewall** keeps high-volume project state in the independent Primary Output Session when the active Runtime uses two Sessions.
- **Primary Execution Session Affinity** reuses the execution context for related exploration, implementation, diagnosis, testing, and fixes.
- **Two-level planning** keeps architecture/product decisions on the input side and local execution planning on the output side.
- **Bounded Coding stages and Decision Checkpoints** prevent an independent Worker from crossing meaningful semantic boundaries without parent review.
- **Context Exchange** externalizes reusable multi-Worker state into bounded, ownership-controlled workspace documents and prefers filesystem capabilities over parent-generated retransmission.
- **Evidence-on-Demand** returns only the evidence needed for a high-value decision instead of replaying complete diffs or logs.
- **Coding Verification Boundary** separates high-volume mechanical verification from semantic acceptance.

## Registered Coding deployments

The Runtime Registry currently contains three independent Host/Profile pairs.

### Codex + OpenAI

- Host Adapter: [`references/runtime/hosts/codex.md`](references/runtime/hosts/codex.md)
- Model Profile: [`references/runtime/profiles/openai.md`](references/runtime/profiles/openai.md)
- Status: current verified deployment.

The OpenAI Coding Profile keeps Primary Output on `gpt-5.6-luna`, uses generic Single-Session Coding Mode when the current Session is explicitly the same eligible runtime, uses `xhigh` for substantive Primary Output, `high` for bounded auxiliary materialization, lower tiers only for strictly mechanical work, and `max` only for targeted escalation after repeated blocking.

### Claude Code + Anthropic API

- Host Adapter: [`references/runtime/hosts/claude-code.md`](references/runtime/hosts/claude-code.md)
- Model Profile: [`references/runtime/profiles/anthropic.md`](references/runtime/profiles/anthropic.md)
- Status: integration mapped against current official Claude Code capabilities; a live `claude` CLI smoke test has not been run in the environment that authored this change.

The Anthropic Coding Profile now uses a **two-model execution tier** instead of treating Sonnet as the answer to every output task:

- Input-side Reasoning remains with the current advanced Claude parent Session.
- **Substantive Primary Output** is bound to explicit `claude-sonnet-5` for general feature implementation, non-trivial debugging/refactoring, cross-module work, complex tests, migrations, compatibility/security-sensitive changes, and other judgment-heavy execution.
- **Lightweight Output / Auxiliary Workers** prefer explicit `claude-haiku-4-5-20251001` for bounded repository exploration, factual inventory, mechanical verification/log compression, exact extraction/replacement, deterministic formatting, fixed-semantics documentation/comment synchronization, and already-specified simple unit-test materialization.
- The routing rule is **model tier first, effort tier second**: move truly bounded low-risk work to Haiku before trying to save cost by lowering Sonnet effort.

When the current main Session is itself explicitly `claude-sonnet-5` and the required Sonnet effort can be applied, the generic Runtime still selects Single-Session Coding Mode for substantive Primary Output. That does not prohibit a Haiku auxiliary Worker when model tiering has concrete benefit; the Sonnet Session remains the Primary Execution Session.

Sonnet 5 uses `effort=xhigh` for normal substantive Primary Output, `high` for narrower work that still requires Sonnet-level judgment, and `max` only for targeted escalation after repeated blocking. `medium`/`low` are no longer the default way to handle work that safely qualifies for Haiku.

Haiku 4.5 does **not** inherit the Sonnet effort policy. Current Claude Code effort support does not include Haiku 4.5, so Haiku is controlled by strict task eligibility and exact model selection rather than invented `high`/`xhigh`/`max` tiers. If a task needs materially more reasoning than the Haiku tier can safely provide, it is rerouted to Sonnet.

Claude Code can substitute or fail over a requested subagent model because of organization `availableModels`, provider restrictions, configured fallback chains, or runtime availability; organization effort caps can also clamp Sonnet effort. Those Host behaviors are **not** accepted as Profile fallback. The actual subagent runtime must be checked when the Host exposes it, and a mismatched model/effort is handled as an explicit capability/rerouting decision rather than silently accepted.

For one-shot read-only research, built-in Explore may still be used when a Haiku cost guarantee is not required. Current Claude Code versions make built-in Explore inherit the main conversation model, so deployments that require low-cost exploration must use an explicit Haiku custom `Explore` definition or another explicit Haiku subagent. Repeated lightweight work that needs context continuity uses a resumable custom/general-purpose Haiku subagent. Sticky substantive Primary Execution Session semantics continue to use resumable Sonnet custom/general-purpose subagents when normal two-Session mode applies.

### Claude Code installation notes

Claude Code supports standard Agent Skills directly. Typical local installation locations are:

- personal: `~/.claude/skills/token-io-decoupling/SKILL.md`;
- project: `.claude/skills/token-io-decoupling/SKILL.md`.

For persistent local startup guidance, keep only a short bootstrap in `~/.claude/CLAUDE.md` or project `CLAUDE.md` and point it to the Skill; do not duplicate the full Skill policy there. Claude Code cloud sessions do not read the machine's personal `~/.claude/skills/`, so use a project/synced deployment that the cloud session actually loads.

### Qwen Code + Alibaba Qwen

- Host Adapter: [`references/runtime/hosts/qwen-code.md`](references/runtime/hosts/qwen-code.md)
- Model Profile: [`references/runtime/profiles/alibaba-qwen.md`](references/runtime/profiles/alibaba-qwen.md)
- Status: integration mapped against current Qwen Code and Alibaba Cloud Model Studio capabilities; a live Qwen Code CLI Max-parent/Flash-subagent smoke test has not yet been run for this deployment.

The Alibaba Qwen Coding Profile is intentionally cost-asymmetric:

- **Input-side Reasoning** binds to `qwen3.8-max`.
- **Primary Output** binds to `qwen3.8-flash` and remains the sticky execution owner for repository exploration, implementation, debugging, build/test loops, and mechanical verification.
- Normal two-Session mode uses a Max parent plus a resumable regular Flash subagent. If the current Session is itself explicitly `qwen3.8-flash`, the generic Runtime may use Single-Session Coding Mode rather than creating another Flash agent only to preserve the nominal topology.

Qwen3.8 currently has three effective native reasoning tiers for this deployment: `low`, `medium`, and `xhigh`. The Profile uses `xhigh` on the Max parent for substantive semantic decisions, defaults ordinary Flash Primary Output to `medium`, raises a bounded Flash stage to `xhigh` only when it genuinely needs stronger local implementation judgment, and reserves `low` for strictly mechanical work. Generic `high`/`max` requests map to Qwen3.8 `xhigh`; they are not treated as separate effective tiers.

Qwen Code regular subagents have independent context, explicit model selection, background continuation through `list_agents` + `send_message`, and can bind to an existing git worktree through `working_dir`. Model selection and effort are separate controls, however: the subagent definition can bind Flash directly, while effective effort may depend on Session/provider configuration. The Host Adapter therefore requires the actual model binding to remain authoritative and does not pretend a per-subagent effort tier was applied when Qwen Code cannot confirm it.

Qwen Code supports personal Skills under `~/.qwen/skills/`, project Skills under `.qwen/skills/`, and persistent instructions through `QWEN.md`; it also reads an existing `AGENTS.md`. A short persistent bootstrap should point to this Skill instead of duplicating the full Coding Flow.

## Multimodal Flow

Multimodal Flow remains independent from Coding. It owns Primary Observation, Observation Firewall, Routine Interaction, Creative Visual Authoring, visual/temporal progressive disclosure, curated visual checkpoints, Computer Use observe/act behavior, Semantic Checkpoints, visual verification, and narrow Multimodal → Coding handoff.

The detailed rules are intentionally not duplicated in the root `SKILL.md` or this overview. See [`references/multimodal-flow.md`](references/multimodal-flow.md). The current OpenAI deployment binding is preserved separately in [`references/multimodal-openai-profile.md`](references/multimodal-openai-profile.md).

The Claude Code/Anthropic and Qwen Code/Alibaba Qwen runtimes above apply to **Coding Flow only**. They do not claim corresponding Multimodal support.

## Scenario routing

Use Coding Flow for repository exploration, implementation, refactoring, debugging, build/test/lint, and code/config/developer-document materialization.

Use Multimodal Flow when continuous GUI Observation, large visual collections, video/temporal state, design comparison, or open-ended visual authoring is the dominant source of input state.

For mixed tasks, select the Flow that owns the current stage and exchange only a narrow Handoff Contract. Do not preload both complete Flows or replay full raw state across the boundary.

## Files and language layout

English is the default public-facing documentation. Simplified Chinese mirrors use the `_zh_cn` suffix.

- `SKILL.md`: canonical executable routing entry.
- `references/shared-protocols.md`: cross-Flow orchestration protocols.
- `references/coding-flow.md`: stable Coding module loader.
- `references/coding/session-model.md`: runtime-neutral Coding roles and Session topology.
- `references/coding/runtime.md`: Coding Runtime Contract.
- `references/coding/execution-control.md`: stages, checkpoints, verification, and output discipline.
- `references/coding/context-exchange.md`: file-backed multi-Agent context transport and ownership.
- `references/runtime/index.md`: concrete Coding deployment registry.
- `references/runtime/hosts/codex.md`: Codex Host Adapter.
- `references/runtime/hosts/claude-code.md`: Claude Code Host Adapter.
- `references/runtime/hosts/qwen-code.md`: Qwen Code Host Adapter.
- `references/runtime/profiles/openai.md`: OpenAI Coding Model Profile.
- `references/runtime/profiles/anthropic.md`: Anthropic Coding Model Profile for the registered Claude Code deployment.
- `references/runtime/profiles/alibaba-qwen.md`: Alibaba Qwen Coding Model Profile for the registered Qwen Code deployment.
- `references/multimodal-flow.md`: complete Multimodal behavior.
- `references/multimodal-openai-profile.md`: preserved current Multimodal OpenAI deployment binding.
- [`BEST_PRACTICES.md`](BEST_PRACTICES.md): optional Codex/OpenAI Coding deployment setup and usage guide.
- `agents/openai.yaml`: OpenAI Agent Skill display and implicit-invocation configuration.

Every English reference under `references/` has a Simplified Chinese `_zh_cn.md` semantic mirror. The Skill loads references lazily by scenario and Runtime selection.
