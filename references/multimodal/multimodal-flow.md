sed: --: No such file or directory
# Multimodal Flow

This is a compact descriptive module for non-Coding multimodal work; it is not an executable workflow or an Agent-creation policy. The caller supplies the available roles, Sessions, tools, permissions, and lifecycle.

## Role ownership

### Decision Agent

Owns visual/interaction intent, semantic and safety constraints, the Semantic Contract, analysis focus, semantic checkpoints, creative direction, amendments, and final acceptance. In Creative Visual Authoring it personally reviews curated evidence and owns composition, hierarchy, style, color/light, and overall quality. It does not continuously ingest full screenshots, video frames, OCR/DOM dumps, or routine navigation state.

### Primary Observation Agent

Owns high-volume screenshots, images, references, rendered UI, video frames, Computer Use observations, OCR, DOM/accessibility state, screening, deduplication, temporal localization, focused inspection, and ephemeral world-state tracking. It returns a compact Visual/State Digest. It may perform ordinary low-risk Routine Interaction and one approved bounded Creative pass, but cannot redefine creative direction or semantic intent.

### Optional Primary Output Agent

When the caller assigns a separate materialization role for a non-Coding report or artifact, it receives the Contract, Observation Digest, and targeted evidence. It materializes only the approved output and does not reanalyze the full visual history. Repository or code work leaves this module through a narrow Coding handoff.

## Observation Firewall

Continuous screenshots, large image sets, video-frame sets, OCR text, DOM/accessibility dumps, Computer Use history, and repeated localization evidence stay with Observation. The Decision Agent receives only findings, risks, open questions, and selected evidence needed for the next decision. A small bounded visual state may be inspected directly when it will not create a context dump. Use targeted evidence requests rather than forwarding raw collections.

## Working modes

- **Routine Interaction**: browsing, localization, scrolling, form filling, menu operations, parameter changes, and bounded edits from a clear plan. Observation may keep the observe → act → observe loop inside its Session.
- **Creative Visual Authoring**: drawing, editing, compositing, layout, design, stylization, or any task whose next step may change composition, hierarchy, color/light, material, whitespace, or overall visual quality.

If a task becomes Creative, stabilize a short `Creative Brief/Visual Plan` before continuing. Routine navigation and local mechanical adjustments may remain within Observation, but do not replace Creative review.

## Creative control loop

1. Decision stabilizes goal, composition/hierarchy, visual language, stage order, checkpoints, and acceptance.
2. Observation executes one bounded pass with an explicit changed region, preserved intent, completion condition, and pause boundary.
3. Observation returns a small curated set of current screenshots/crops and minimal status at the material milestone.
4. Decision personally reviews the evidence and returns `Keep`, `Change`, `Next pass`, updated acceptance, and approval to continue.
5. Observation cannot cross an unapproved milestone, redefine core direction, or turn a local repair into a new design. If curated evidence cannot reach Decision, stop open-ended Creative work and report the capability block.

Curated evidence is the narrow exception to the firewall: do not send continuous screenshots, click sequences, full layer state, or complete GUI history. Typical milestones are structure, color/lighting, detail/material, and final review; merge or split them to fit complexity, but do not cross several unreviewed material milestones.

## Progressive disclosure

For large visual inputs use:

```text
inventory → coarse screening → dedup/group → candidate selection → focused inspection → local evidence
```

For video or temporal streams use sampling, segment localization, key-frame selection, repeated-frame removal, focused inspection, and a Temporal Digest. Increase density around relevant ranges instead of inspecting every input at maximum detail.

## Session state and Routine safety

Observation normally owns screen coordinates, scroll position, dynamic layout, popups, current page/video position, and other ephemeral localization. Keep this state out of long-lived semantic records. Observation may perform ordinary navigation and no-side-effect actions under the approved Contract; pause before sending, publishing, payment, deletion, permission/security changes, external resource creation, or another hard-to-reverse side effect unless explicitly authorized by the Contract and runtime.

## Digest and verification

Use only informative fields:

```text
State: <current state>
Findings: <facts relevant to the next decision>
Evidence: <selected image/frame/time references>
Issue: <risk or anomaly>
Need: <decision required>
```

Observation owns mechanical visual/temporal checks; Decision owns semantic acceptance and, in Creative mode, visual design acceptance at every material milestone. Do not treat an Observation “done” message as semantic acceptance. Re-evaluate changed final state rather than carrying forward an earlier verdict.

## Narrow Coding handoff

When the next work is code, repository, configuration, or Coding verification, end the visual stage and pass only:

```text
Goal; Required changes; Constraints; Evidence references; Acceptance
```

Do not copy full image sets, video frames, OCR, DOM, or observation history. After Coding, reuse the assigned Observation context for visual verification when possible.
