# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` is an Agent orchestration Skill for hosts that support Agent Skills. It separates high-value semantic decisions from high-volume raw-state consumption and output materialization so the parent reasoning context does not have to continuously absorb low-decision-density repository state or visual world state.

The project contains two independent flows rather than one universal multi-Agent topology:

- **Coding Flow** is the actively maintained focus. Input-side Reasoning owns high-value decisions; Primary Output owns repository exploration, implementation/materialization, raw tool output, debugging, and mechanical verification. Coding Core is now independent of concrete Code Agent products and model names; a Runtime Contract selects the Host Adapter and Model Profile for the current deployment.
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

Coding Core no longer contains a model-specific “single-agent” branch. The active Runtime derives the topology:

- use **Single-Session Coding Mode** when the current Session is explicitly eligible for both Coding responsibilities, can satisfy the required runtime parameters, and there is no independent structural reason to split;
- use **normal two-Session mode** when the current Session owns input-side reasoning but the active Profile requires a separate Primary Output runtime;
- create additional Sessions only for concrete benefits such as fresh verification, real parallelism, context-capacity recovery, explicit isolation, or Profile-defined targeted escalation.

Repository size, long output, build/test work, or generic task complexity are not reasons by themselves to create another Session.

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

## Multimodal Flow

Multimodal Flow remains independent from Coding. It owns Primary Observation, Observation Firewall, Routine Interaction, Creative Visual Authoring, visual/temporal progressive disclosure, curated visual checkpoints, Computer Use observe/act behavior, Semantic Checkpoints, visual verification, and narrow Multimodal → Coding handoff.

The detailed rules are intentionally not duplicated in the root `SKILL.md` or this overview. See [`references/multimodal-flow.md`](references/multimodal-flow.md). The current OpenAI deployment binding is preserved separately in [`references/multimodal-openai-profile.md`](references/multimodal-openai-profile.md).

This separation reflects the current maintenance boundary: Coding runtime portability is the primary active direction, while Multimodal behavior is preserved without an untested cross-product redesign.

## Current verified Coding deployment

The Runtime Registry currently contains one verified pair:

- Host Adapter: [`references/runtime/hosts/codex.md`](references/runtime/hosts/codex.md)
- Model Profile: [`references/runtime/profiles/openai.md`](references/runtime/profiles/openai.md)

The current OpenAI Coding Profile preserves existing behavior:

- input-side reasoning: the current advanced parent model/session;
- Primary Output: `gpt-5.6-luna`;
- when the current Session is explicitly `gpt-5.6-luna` and the required runtime parameters are available, it is dual-role eligible and the generic Runtime selects Single-Session Coding Mode;
- normal two-Session Primary Output uses `reasoning_effort=xhigh` for general implementation, non-trivial debugging/refactoring, and complex verification/test code;
- bounded auxiliary materialization normally uses `reasoning_effort=high`;
- host-supported `medium` or lower tiers are restricted to strictly bounded, low-risk, mechanically verifiable tasks;
- `reasoning_effort=max` is reserved for a narrowly scoped task that has repeatedly blocked an existing high/xhigh Worker, with file-backed handoff context preferred before replacement.

If a required model or runtime parameter cannot be satisfied, the Profile blocks the corresponding substantive work rather than silently substituting another model.

## Current Multimodal deployment

The existing Multimodal OpenAI binding is preserved without being folded into the Coding Runtime abstraction:

- Decision Agent: current advanced parent model;
- Primary Observation Agent: `gpt-5.6-luna`, using `reasoning_effort=xhigh` for substantive high-volume visual/temporal analysis;
- Optional Primary Output Agent: `gpt-5.6-luna`, using `reasoning_effort=xhigh` for substantive long output.

Observation and Output remain distinct context owners even when the deployment binds them to the same model.

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
- `references/runtime/hosts/codex.md`: current Codex Host Adapter.
- `references/runtime/profiles/openai.md`: current OpenAI Coding Model Profile.
- `references/multimodal-flow.md`: complete Multimodal behavior.
- `references/multimodal-openai-profile.md`: preserved current Multimodal OpenAI deployment binding.
- [`BEST_PRACTICES.md`](BEST_PRACTICES.md): optional current Coding deployment setup and usage guide.
- `agents/openai.yaml`: OpenAI Agent Skill display and implicit-invocation configuration.

Every English reference under `references/` has a Simplified Chinese `_zh_cn.md` semantic mirror. The Skill loads references lazily by scenario and Runtime selection.
