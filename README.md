# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` is an Agent scheduling Skill for hosts that support Agent Skills. It separates high-value semantic decisions from high-volume raw-state consumption and large output materialization, so an advanced parent model does not have to continuously absorb low-decision-density project state or visual world state.

The Skill does not force one universal three-agent architecture. It provides two independent flows:

- **Coding Flow**: keeps the mature two-role model. The input-side reasoning role owns high-value decisions, while the Primary Output role owns repository exploration, code/document/config materialization, test fixing, and mechanical verification. If the current Code Agent is already Luna, both roles stay in the same session by default instead of delegating to another Luna.
- **Multimodal Flow**: handles Computer Use, Browser Use, video, large image/screenshot collections, and visual design. A Decision Agent owns high-value decisions while a Primary Observation Agent consumes high-volume visual/temporal input. An Optional Primary Output Agent is created only when substantial non-coding output is actually needed; code changes use a narrow handoff into Coding Flow.

Multimodal Flow explicitly separates two modes. **Routine Interaction** keeps a low-overhead observe/act loop inside the Observation Agent. **Creative Visual Authoring**—drawing, image editing, layout, visual design, illustration, compositing, and other open-ended visual work—uses Decision-led Visual Authoring. The Decision Agent first defines a Creative Brief/Visual Plan, then personally reviews curated screenshots or crops at a default 3–6 adaptive visual checkpoints, critiques the result, and issues amendments before the Observation Agent continues. The Decision Agent owns the primary visual direction; the Observation Agent performs local mechanical visual judgments, tool operations, and implementation of approved decisions.

## Design goals

- Ordinary coding tasks should not gain an Observation Agent or extra orchestration layer merely because the Skill also supports multimodal work.
- Large diffs, test logs, file trees, and other high-volume project state remain with the Coding Primary Output role for consumption and compression.
- Continuous screenshots, image sets, video frames, Computer Use observations, OCR, DOM, accessibility state, and other high-volume multimodal input remain with the Primary Observation Agent.
- Routine Computer Use observe/act loops stay in the same Observation session to avoid synchronizing ephemeral GUI state across agents on every step.
- Routine GUI work and open-ended visual creation are routed differently: creative work follows bounded visual pass → curated checkpoint → Decision critique/amendment, rather than letting the Observation Agent cross multiple visual milestones without review.
- In Creative Visual Authoring, composition, visual hierarchy, style, color relationships, overall visual quality, and cross-stage direction changes are high-value decisions owned by the Decision Agent. The Observation Agent must not become the de facto lead designer.
- Large image and video inputs use progressive disclosure so analysis density increases only for candidate regions, images, frames, or time ranges.
- A curated checkpoint screenshot/crop is a narrow exception to the Observation Firewall. Continuous screenshots, coordinates, click sequences, and full visual history are not passed upstream. If the host cannot provide curated visual evidence to the Decision Agent, Creative mode must stop and report a capability block.
- Semantic Checkpoints distinguish routine GUI interaction from high-impact actions such as sending, submitting, paying, deleting, or changing permissions.
- Visual analysis and Coding exchange only a narrow Handoff Contract rather than replaying full design assets, screenshot history, or OCR text into the Coding role.
- Dispatch Preview, event-driven reporting, Evidence-on-Demand, and cache-friendly incremental communication keep parent-session token use bounded.

## Scenario routing

```text
Token I/O Decoupling
        │
        ├── Coding Flow
        │     Input-side Reasoning Role
        │               ↓
        │     Primary Output Role
        │
        └── Multimodal Flow
              ┌─ Routine Interaction ───────────────┐
              │   Decision Agent                    │
              │          ↓                          │
              │   Observation observe/act loop      │
              │          ↓                          │
              │   Visual / State Digest             │
              └─────────────────────────────────────┘
              ┌─ Creative Visual Authoring ─────────┐
              │   Decision Agent: Brief / Plan      │
              │          ↓                          │
              │   bounded visual pass               │
              │          ↓                          │
              │   curated checkpoint screenshot     │
              │          ↓                          │
              │   Decision critique / amendment     │
              │          ↺ next approved pass       │
              └─────────────────────────────────────┘
                             ↓
                    optional Output / Coding Handoff
```

### Coding Flow

Use Coding Flow for repository exploration, implementation, refactoring, debugging, build/test/lint, and materializing code, configuration, or developer documentation.

Its main mechanisms include Context Firewall, Primary Execution Session affinity, Semantic Contract, two-level planning, Coding Verification Boundary, and input-side output discipline.

### Multimodal Flow

Use Multimodal Flow for Computer Use, Browser Use, continuous GUI observation, large image/screenshot collections, video or large frame sets, visual-reference comparison, and other high-volume visual world state.

Its main mechanisms include mode routing (Routine Interaction / Creative Visual Authoring), Observation Firewall, Visual / Temporal Progressive Disclosure, Ephemeral State Ownership, Routine Computer Use Observe/Act Loop, Decision-led Visual Authoring, Semantic Checkpoint, Visual / State Digest, and Multimodal Verification.

For open-ended visual creation, the Decision Agent defines composition, hierarchy, color/light, stages, and acceptance conditions first. The Observation Agent executes one bounded visual stage at a time and returns curated screenshots or crops at material milestones such as structure, color/lighting, detail, and final review. The Decision Agent must personally inspect, critique, and amend the result before approving the next stage. The intended division is not “Observation designs, Decision approves”; core visual direction is decided by the Decision Agent, while the Observation Agent realizes that approved direction in GUI tools such as Krita, Photopea, Figma, or Photoshop.

### Mixed tasks

For tasks such as “modify the frontend from this design,” first complete visual analysis in Multimodal Flow. Compress stable goals, Required changes, Constraints, Evidence references, and Acceptance into a narrow Handoff Contract, then enter Coding Flow. If visual verification is needed after implementation, reuse the original Primary Observation Agent.

## Current OpenAI profile

The current deployment strategy is:

- Coding input-side reasoning: the current advanced parent model;
- Coding Primary Output: `gpt-5.6-luna`, with `reasoning_effort=xhigh` for substantive materialization;
- Multimodal Decision Agent: the current advanced parent model;
- Multimodal Primary Observation Agent: `gpt-5.6-luna`, with `reasoning_effort=xhigh` for substantive high-volume visual/temporal analysis;
- Multimodal Optional Primary Output Agent: `gpt-5.6-luna`, with `reasoning_effort=xhigh` for substantive long output.

Observation and Output are different responsibilities with different session affinity. Even when the current profile binds them to the same model, their high-volume contexts are not merged by default.

This profile is a deployment policy, not the architecture itself. Future model changes should primarily update the model bindings while preserving the flow boundaries.

## Files and language layout

English is the default public-facing documentation. Simplified Chinese mirrors use the `_zh_cn` suffix.

- `README.md`: English project overview and public entry point.
- `README_zh_cn.md`: Simplified Chinese project overview.
- `SKILL.md`: canonical executable Skill entry in English. Standard Skill hosts should continue to load this file.
- `SKILL_zh_cn.md`: Simplified Chinese semantic mirror for review and maintenance.
- `references/shared-protocols.md`: English shared protocols.
- `references/coding-flow.md`: English Coding Flow rules.
- `references/multimodal-flow.md`: English Multimodal Flow rules.
- `references/shared-protocols_zh_cn.md`, `references/coding-flow_zh_cn.md`, `references/multimodal-flow_zh_cn.md`: Simplified Chinese mirrors that only cross-reference the Chinese document set.
- `agents/openai.yaml`: OpenAI Agent Skill display and implicit-invocation configuration; its public-facing text is English.

The Skill loads references lazily by scenario. Ordinary Coding does not load Multimodal Flow, and pure multimodal analysis does not preload Coding Flow.
