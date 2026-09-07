---
name: token-io-decoupling
description: "High-volume Agent Token I/O decoupling. Coding keeps high-value input-side reasoning separate from Primary Output responsibilities, while defaulting to single-session self-execution when the current Code Agent is already Luna. Browser Use, Computer Use, continuous browser/desktop GUI workflows, video, large image/screenshot sets, and visual design use an independent Multimodal Flow that isolates high-volume visual/temporal input between a Decision Agent and a Primary Observation Agent. Open-ended drawing, image editing, and visual creation use Decision-led Visual Authoring and hand off to output or Coding only when needed."
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

This Skill defines two scenario-specific Agent orchestration flows that separate high-value semantic decisions from high-volume raw-state consumption and output materialization. Coding and Multimodal have materially different execution architectures, so they share only a small set of orchestration protocols instead of forcing one universal role topology.

This Skill defines orchestration conventions only. It cannot bypass higher-priority permissions, user authorization, product limitations, or safety rules, and it must not present unmeasured claims about price, cache hits, or quota savings as facts.

## Core principles

1. **Choose the Flow first, then load its details**: do not load every reference unconditionally at startup.
2. **Keep Coding simple**: ordinary Coding keeps the logical two-role model “input-side reasoning → Primary Output.” Role separation does not imply Agent or Session separation. When the current Code Agent is explicitly `gpt-5.6-luna`, the current Session performs both roles by default and must not create another Luna merely to preserve the two-role shape.
3. **Isolate high-volume Multimodal Observation**: Computer Use, video, large image/screenshot sets, visual design, and similar tasks are routed so the Primary Observation Agent consumes visual/temporal world state while the Decision Agent receives compressed Digests. Open-ended visual creation additionally follows the curated-evidence loop of Decision-led Visual Authoring.
4. **Use narrow Handoffs for mixed tasks**: visual analysis and Coding exchange only stable goals, required changes, constraints, evidence references, and acceptance criteria. Do not dump full raw state across Flows.
5. **Map roles to models and Sessions by responsibility**: a role represents responsibility and context ownership first; it does not require a one-to-one Agent instance. Split Sessions only when model tiering, independent context ownership, real parallelism, fresh verification, capacity management, or another concrete isolation benefit exists. In Multimodal Flow, Observation and Output may remain separate even when both use Luna because they own different high-volume contexts.

## Scenario Routing

### Coding Flow

Route the following tasks to Coding Flow by default:

- repository or project exploration;
- implementation, refactoring, bug fixing, debugging;
- materializing code, configuration, or developer documentation;
- build, test, lint, formatting, type checking, diff/log analysis;
- other development tasks where project text state and large output are the primary Token pressure.

After selecting Coding Flow, load:

1. [`references/shared-protocols.md`](references/shared-protocols.md)
2. [`references/coding-flow.md`](references/coding-flow.md)

Ordinary Coding must not load `multimodal-flow.md` or create a Primary Observation Agent merely because this Skill also supports Multimodal Flow.

### Multimodal Flow

Route the following tasks to Multimodal Flow by default:

- Computer Use and continuous browser/desktop GUI observe/act workflows;
- large image, screenshot, design-reference, or rendered-UI analysis;
- video, large frame sets, or other temporal visual input;
- UI / visual design comparison and verification;
- tasks where high-volume OCR, DOM, accessibility tree, or other world state is primarily obtained through visual/interface Observation.

After selecting Multimodal Flow, load:

1. [`references/shared-protocols.md`](references/shared-protocols.md)
2. [`references/multimodal-flow.md`](references/multimodal-flow.md)

Then distinguish two working modes:

- **Routine Interaction**: browsing, control localization, form filling, normal page inspection, and bounded edits whose intended visual result is already clear. Keep the low-overhead observe/act loop inside the Primary Observation Agent.
- **Creative Visual Authoring**: drawing, illustration, image editing, compositing, layout, visual design, canvas creation, stylization, or any open-ended work that requires decisions about composition, visual hierarchy, color/light, material, or overall visual quality. Use Decision-led Visual Authoring. The Decision Agent owns the primary visual design direction: composition, hierarchy, style, color relationships, overall look, and cross-stage direction changes must not be delegated to the Observation Agent. The Observation Agent performs local mechanical visual judgments and materializes approved direction.

If a Routine Interaction task evolves into open-ended changes to core composition, style, or visual hierarchy, switch immediately to Creative Visual Authoring. Do not allow the Observation Agent to continue the creative work independently. See `multimodal-flow.md` for the full loop, curated-evidence boundary, and host capability-block rules.

Do not load Coding Flow merely for architectural symmetry. Load Coding Flow only when the task actually enters a code/repository materialization stage via a narrow Multimodal → Coding handoff.

### Small visual-input exception

A single simple image, a few strictly bounded screenshots, or another clearly small Observation does not require mechanical creation of a Primary Observation Agent. Decide based on potential raw-input volume, temporal/interaction complexity, and decision density rather than the mere presence of images. This size exception does not downgrade open-ended visual creation to Routine Interaction; creative work still follows Creative Visual Authoring.

### Mixed tasks and Flow Handoff

Do not preload both complete Flows at the start of a mixed task. Select the Flow whose Token pressure dominates the current stage and hand off only when responsibilities truly change.

Typical design-driven Coding:

```text
Multimodal Flow
→ Primary Observation Agent analyzes reference / current UI
→ Visual / State Digest
→ Decision Agent confirms semantic changes
→ narrow Handoff Contract
→ Coding Flow
→ Primary Output Role implements and mechanically verifies
→ return to the original Multimodal Flow for visual verification when needed
```

Typical ordinary Coding followed by UI verification:

```text
Coding Flow
→ implementation / tests
→ load Multimodal Flow only when high-volume visual verification becomes necessary
→ visual verification
```

The Handoff fields and prohibited raw-state payloads are defined in `multimodal-flow.md`.

## Reference loading rules

- Load only the Flow documents and shared protocols required for the current scenario.
- If a relevant reference is already loaded and its rules remain valid, do not read it again.
- When switching Flows, load only the newly required Flow reference; do not reload unchanged shared protocols.
- The main `SKILL.md` is the routing and Profile entry point, not a replacement for Flow details. Load the selected Flow reference before substantive execution.
- When correctness requires cross-Flow information, use a narrow Handoff or Evidence-on-Demand instead of loading all references and raw state at once.

## Current OpenAI Profile

Model bindings are part of the current runtime Profile, not the Token I/O Decoupling architecture itself. Future model changes should update this section before changing Flow responsibility boundaries.

### Coding Flow

At Coding Flow startup, first confirm the current Code Agent model identity and then map responsibilities to Sessions:

- **Current Agent is explicitly `gpt-5.6-luna`**: enter **Single-Agent Luna Mode**. The current Session performs both the Input-side Reasoning Role and Primary Output Role, including project exploration, implementation, debugging, mechanical verification, and output. Do not create or require another Luna Primary Output Agent merely to preserve a two-role topology.
- **Current Agent cannot explicitly confirm it is `gpt-5.6-luna`**: constrain the current Agent as the input-side reasoning role and use an independent `gpt-5.6-luna` for the Primary Output Role, preserving the normal two-Session Coding Flow.
- Substantive implementation, long output, and other materialization work require the Luna performing the Primary Output Role to use `reasoning_effort=xhigh`; this also applies in Single-Agent Luna Mode.
- Single-Agent Luna Mode may create another Agent only for fresh verification, real parallelism, clearly degraded/overgrown current context, or another explicit isolation benefit. Project exploration, implementation, testing, long output, or generic task complexity are not exceptions.

### Multimodal Flow

- Decision Agent: the current advanced parent model.
- Primary Observation Agent: `gpt-5.6-luna`; substantive large image/video/Computer Use Observation analysis uses `reasoning_effort=xhigh`.
- Optional Primary Output Agent: `gpt-5.6-luna`; substantive long output uses `reasoning_effort=xhigh`.
- Observation and Output are different responsibilities with different Session Affinity. Even if the current Profile binds both to Luna, do not merge their high-volume contexts by default. Single-Agent Luna Mode changes only the default Coding role mapping and does not weaken Multimodal Observation ownership.

### Profile constraints

- Do not silently replace a role that requires Luna with another model.
- If an independent Luna role is required but `gpt-5.6-luna` identity cannot be confirmed, the model cannot be selected explicitly, or substantive Observation/materialization cannot satisfy `reasoning_effort=xhigh`, stop that substantive work and briefly report the block.
- Purely read-only, strictly bounded diagnosis or observation may continue when Luna identity is confirmed but the host cannot set reasoning effort. Do not use that exception to move complex high-volume work back to the advanced parent model.

## Loading boundary

This Skill may be automatically discovered, but a normal Skill `description` only influences implicit matching and cannot guarantee that the complete Skill is loaded on every host startup. If a host must always obey specific invariants, put those invariants in that host's persistent instruction mechanism—for example, Codex global `~/.codex/AGENTS.md` or host-injected system/developer instructions.

References under `references/` are loaded on demand. Do not read all of them at task startup merely because they might become useful later.
