# Multimodal Flow

This Flow covers Computer Use, continuous GUI Observation, large image/screenshot collections, video or large frame sets, visual-design analysis, reference-design comparison, high-volume OCR / DOM / accessibility state, and other tasks where visual or temporal world state dominates Input Token volume.

This Flow is independent from Coding Flow. Do not introduce an Observation Agent into ordinary Coding merely to unify role models, and do not pass high-volume visual history directly into Coding Flow.

All roles also follow [`shared-protocols.md`](shared-protocols.md).

## Architecture roles

### Decision Agent

Owns high-value semantic and risk judgment: understanding the user's visual or interaction goal, defining business and safety constraints, choosing analysis focus, creating or amending the Semantic Contract, resolving semantic ambiguity and Semantic Checkpoints, receiving compressed visual conclusions, and performing final semantic acceptance. In Creative Visual Authoring it must also define the Creative Brief/Visual Plan, personally inspect curated visual evidence at each material visual milestone, critique the result, issue amendments, and approve the next stage.

The Decision Agent owns the primary visual-design direction in Creative Visual Authoring. Composition, visual hierarchy, style, color relationships, overall visual quality, and cross-stage creative direction are high-value responsibilities and must not be implicitly delegated merely because the Observation Agent owns the continuous canvas or GUI context. The Decision Agent is not a final-only approver; it performs active design analysis and direction revision throughout the work.

The Decision Agent does not continuously inspect large screenshot sets, analyze every video frame, ingest full OCR/DOM dumps, or participate in every routine navigation step. Curated Creative checkpoints are a narrow exception to the Observation Firewall and do not remove this boundary.

### Primary Observation Agent

Owns consumption and compression of high-Input-Token world state, including:

- screenshots, image collections, design references, rendered UI;
- video frames, key frames, and temporal segments;
- Computer Use observations;
- OCR, DOM, accessibility tree, and other high-volume visual/interface state.

It performs screening, deduplication, grouping, visual understanding, temporal localization, local OCR, difference analysis, focused inspection, evidence selection, and ephemeral world-state tracking.

Its default output is not a long report but a low-Token, high-information-density Visual / State Digest. Within an approved Semantic Contract it may autonomously perform ordinary low-risk actions required for Routine Interaction observe/act loops. In Creative mode it executes one approved bounded visual pass, captures curated checkpoint evidence, and pauses for Decision critique and approval.

In Creative mode it may make local mechanical visual judgments needed to complete the current pass—for example control localization, edge/alignment checks, local occlusion checks, or verification of explicit conditions—but it must not become the primary visual designer. It may not independently redefine core composition, hierarchy, style, color relationships, or cross-stage creative direction, and it may not replace Decision analysis merely because it knows the current canvas state best.

### Optional Primary Output Agent

Create this role only when a Multimodal task still requires substantial non-Coding materialization after visual/temporal analysis, such as a long report or large structured artifact.

It receives only the Decision Agent's Semantic Contract, the Observation Agent's compressed Digest, and necessary Evidence-on-Demand. It does not receive the full visual history by default.

If subsequent work is repository modification, code implementation, debugging, build, or test work, do not duplicate Coding execution rules here. Use the narrow handoff defined below and enter [`coding-flow.md`](coding-flow.md).

## Observation Firewall

The following raw state is normally ingested only by the Primary Observation Agent and does not continuously flow into the Decision Agent:

- continuous full-screen screenshots and screenshots generated while scrolling;
- Computer Use observation history;
- large raw image sets, design references, or rendered results;
- full video-frame sets or large temporal slices;
- full OCR text;
- DOM dumps, accessibility trees, UI-state dumps;
- repeated intermediate evidence generated for control localization or visual-change verification.

The Primary Observation Agent returns only the state, findings, risks, evidence references, and open questions required for the next high-value decision. When the Decision Agent must confirm a specific visual fact, use Evidence-on-Demand for the minimum necessary evidence rather than re-ingesting the entire visual collection.

Use potential raw Observation volume and decision density as the criterion, not the media type alone. A single simple image or strictly bounded small visual state may be inspected directly by the Decision Agent when it will not produce a context dump. Do not create an Observation Agent mechanically. This input-size exception affects only how references are consumed; it does not downgrade open-ended visual creation to Routine Interaction.

## Working modes: Routine Interaction and Creative Visual Authoring

### Mode selection

Choose by visual decision density and result openness rather than by the application being used:

- **Routine Interaction**: browsing, page/control localization, scrolling, form filling, menu operations, ordinary brush-parameter adjustment, and bounded edits performed from an already-clear plan. When the intended result is largely predetermined by the user or Contract, the Observation Agent may maintain the continuous observe/act loop itself.
- **Creative Visual Authoring**: drawing, illustration, image editing, compositing, layout, visual design, canvas creation, stylization, and work that requires deciding or iterating composition, hierarchy, color/light, material, whitespace, or overall visual quality. If the next step may change the core visual intent, use Creative mode.

A task may switch from Routine Interaction to Creative Visual Authoring. After switching, create the Creative Brief/Visual Plan before continuing; “the tool is already open” or “only details remain” is not a reason to skip it. Conversely, ordinary tool localization, menu use, scrolling, and brush parameter changes inside Creative mode may remain within the Observation Agent and do not require per-action escalation.

### Decision-led Visual Authoring loop

Creative mode is neither click-by-click remote control nor “Observation designs everything, Decision approves at the end.” The Decision Agent owns the main visual direction; the Observation Agent materializes one bounded visual stage; then the Decision Agent uses curated evidence to perform design analysis and choose the next high-level direction.

1. **Create the Brief/Plan**: the Decision Agent directly inspects a small set of key references or first receives an Observation screening summary, then creates a short `Creative Brief/Visual Plan`. At minimum, stabilize the final goal, composition/layout, focal point and hierarchy, color/light or visual language, stage order, expected checkpoint count (default 3–6, adaptive to complexity), and acceptance conditions. The plan is a visual extension of the Semantic Contract, not a replacement for images or a replay of Observation history.
2. **Dispatch one bounded visual pass**: approve only one limited stage at a time—for example structural block-in, color/value establishment, material/detail, or final unification/output preparation. The pass contract states what regions or properties may change, what core composition/style must remain stable, completion conditions, and which checkpoint requires a pause.
3. **Return a curated checkpoint**: at a material visual milestone, the Observation Agent must pause and return a small number of current-canvas screenshots/crops that best support directional judgment, with reference comparison when needed and an extremely short status. Default milestones include structure/composition, color/lighting, detail/material, and final review. Milestones may be merged or split by task complexity, but one unreviewed pass must not cross several material milestones.
4. **Decision personally reviews and amends**: the Decision Agent must inspect the curated visual evidence itself and actively analyze composition, hierarchy, color/light, style consistency, and overall quality against the Brief. It must not rely only on the Observation Agent's text conclusion or merely formalize design choices already made by Observation. Then issue a short amendment containing `Keep`, `Change`, `Next pass`, updated acceptance conditions, and `Approved to continue`. If direction is substantially wrong, redirect at the current checkpoint and pause rather than allowing Observation to invent its own recovery direction.
5. **No crossing unapproved milestones**: the Observation Agent may enter the next stage only after receiving approval or an amendment for the current checkpoint. It may not cross an unapproved material milestone, redefine core composition/style/hierarchy, or expand a local fix into a new creative direction. Ordinary mechanical operations remain autonomous.

Curated checkpoints are a narrow exception to the Observation Firewall. Pass only selected screenshots/crops, necessary reference comparison, and minimal status. Do not pass continuous screenshots, click/coordinate sequences, complete GUI history, full layer state, or repeated intermediate evidence.

If the host cannot actually provide curated screenshots/crops or equivalent visual evidence to the Decision Agent, open-ended Creative Visual Authoring must stop and report a capability block. Do not fall back to Routine Interaction and let the Observation Agent independently finish the creative work. Routine Interaction may continue normally when Creative review is not required.

Recommended minimum message form:

```text
Creative Plan: goal; composition/hierarchy; color/light; stages; checkpoint=4; acceptance
Pass 1: establish silhouette and large shapes only; preserve viewpoint and focal point; pause at structure checkpoint
Checkpoint: structure complete; Evidence: curated current-canvas screenshot + necessary crop
Decision amendment: Keep subject placement; Change background whitespace; Next pass establish warm/cool lighting; Approved to continue
```

## Visual Progressive Disclosure

For large image/screenshot collections, increase analysis density progressively instead of starting with maximum-detail inspection of every input:

1. `Inventory`: count, file names/IDs, dimensions, formats, ordering, or other low-cost metadata;
2. `Screening`: use the lowest reasonable detail sufficient for coarse relevance filtering;
3. `Dedup / Group`: remove obvious duplicates and group by scene, state, or visual similarity;
4. `Candidate Selection`: choose the inputs that actually require deeper judgment;
5. `Focused Inspection`: increase detail only for candidates;
6. `Local Evidence`: use crops, zoom, OCR, or other targeted methods only where needed.

Thumbnail strategy, detail level, clustering method, and image tools are chosen by the Primary Observation Agent according to host capability. This Skill does not prescribe a particular implementation.

Do not high-detail summarize an entire large image set to the Decision Agent merely for “complete analysis.”

## Video / Temporal Progressive Disclosure

Use the same principle for video and large temporal visual streams:

```text
video / frame stream
→ temporal sampling
→ scene / segment localization
→ key-frame selection
→ repeated-frame elimination
→ focused inspection
→ Temporal Digest
```

Locate potentially relevant time ranges and key changes first, then increase analysis density for candidate segments. Do not send every frame through high-detail reasoning unless the task genuinely requires frame-by-frame inspection.

This Skill does not prescribe a fixed frame rate, sampling interval, or segmentation algorithm. When correctness requires denser analysis, increase density around relevant local time ranges before increasing frame consumption for the entire video.

## Session Affinity and Ephemeral State Ownership

A continuous Multimodal workflow maintains one Primary Observation Agent by default. Its Session Affinity preserves visual/temporal working context, screened candidates, navigation history, and current ephemeral world state, reducing repeated Observation and relocation.

The following is ephemeral execution state and normally remains only in the Primary Observation Agent:

- screen coordinates;
- current scroll position;
- dynamic page layout;
- popup, control, or temporary UI state;
- current window/page/video position;
- visual localization valid only for the latest Observation.

Do not make this state a core long-lived Semantic Contract or periodically synchronize it to the Decision Agent.

The Decision Agent states semantic goals, such as “open account security settings and inspect two-factor authentication status.” The Primary Observation Agent uses the latest Observation to choose concrete coordinates, controls, and ordinary navigation steps.

The Primary Observation Agent is sticky but not immortal. Rebuild it when context is clearly stale, visual history is severely contradictory, truly independent verification is required, or isolation benefits are concrete.

## Computer Use Observe / Act Loop (Routine Interaction)

Routine Interaction keeps its ordinary execution loop inside the Primary Observation Agent:

```text
observe
→ ordinary action
→ observe
→ ordinary action
→ observe
```

Within an approved Semantic Contract, scrolling, ordinary navigation, opening no-side-effect pages, locating controls, and filling not-yet-submitted fields do not require step-by-step return to the Decision Agent. Screenshot changes, element localization, and the next execution step remain inside Observation context. When these actions serve Creative Visual Authoring, they may still stay local, but they do not replace Creative checkpoints.

Do not mechanically decompose Routine work into:

```text
Observation Agent → Decision Agent → Output Agent → Observation Agent
```

That pattern creates synchronization cost, visual information loss, and stale-state risk. Creative mode instead uses bounded visual pass → curated checkpoint → Decision critique/amendment without escalating every click.

Every action still follows the host tool's own confirmation, permission, and safety requirements; this Skill does not override them.

## Semantic Checkpoints

Escalate Routine Computer Use based on semantic side effects, not whether the action is technically only one click or keystroke. Creative mode additionally has material visual milestones that require curated evidence and Decision review even when no external side effect exists.

Typical Semantic Checkpoints include:

- sending external messages or email;
- submitting, publishing, or making content public;
- payment, purchase, transfer, or other financial actions;
- deletion, merge, approval, or other hard-to-reverse actions;
- permission, access-control, or account-security changes;
- creating or modifying real external resources;
- actions the user explicitly requested to confirm before execution.

If the Semantic Contract explicitly authorizes the specific side effect and the host tool requires no additional confirmation, the Primary Observation Agent may proceed. Otherwise pause before the action and escalate only the current state, expected effect, and decision needed.

Do not skip a semantic boundary because the interaction is mechanically simple, and do not request approval for every ordinary navigation action merely because Semantic Checkpoints exist.

## Visual / State Digest

The Primary Observation Agent returns an elastic, high-density summary. Use only fields that add information:

- `State`: current page, visual collection, or temporal-analysis progress;
- `Findings`: discoveries relevant to the next decision;
- `Evidence`: necessary image/frame/time-range/local evidence references;
- `Issue`: anomaly, conflict, or risk;
- `Need`: decision required from the Decision Agent.

Examples:

```text
State: screened 184 screenshots
Findings: 7 relevant; 4 show the same login redirect error
Evidence: IMG_034, IMG_039, IMG_042, IMG_087
Issue: error occurs only after OAuth redirect
```

```text
State: reached payment confirmation page
Finding: address and payment information are complete
Issue: next action will submit a real order
Need: whether to submit
```

Do not narrate the full observation history image by image, frame by frame, screenshot by screenshot, or action by action. Compress further when the parent only needs a binary conclusion or a few facts.

A Creative checkpoint Digest may additionally include curated screenshots/crops while remaining minimal: current pass and milestone, one directional status, a few `Evidence` references, and the `Need` for Decision review. Long prose is not a substitute when the host cannot provide actual visual evidence.

## Multimodal Verification Boundary

The Primary Observation Agent owns high-volume visual/temporal mechanical verification, including:

- whether the page reached the target state;
- whether a target control appeared, disappeared, or entered the expected state;
- whether the UI has obvious layout breakage or key differences from a reference;
- whether image-processing output satisfies explicit visual conditions;
- whether a target video event occurred and where;
- whether final Computer Use state satisfies mechanically checkable Contract conditions.

The Decision Agent owns semantic acceptance: whether the visual result truly satisfies the user goal, business/risk constraints remain intact, and remaining deviation is acceptable. In Creative mode it also owns visual acceptance, design analysis, and direction revision at each material milestone; the Observation Agent's “done” statement or design suggestion does not replace direct inspection and independent Decision judgment.

The Decision Agent does not reread all screenshots, references, or video frames by default. Use Evidence-on-Demand for specific conclusions and a fresh verifier only when high risk or independent-review value justifies it.

## Multimodal → Coding narrow Handoff

When Multimodal analysis requires code, repository, configuration changes, or Coding verification, end the current visual-analysis stage. The Decision Agent creates a narrow Handoff Contract and then enters Coding Flow.

The Handoff contains only:

- `Goal`: what Coding must accomplish;
- `Required changes`: confirmed changes to materialize;
- `Constraints`: compatibility, business, safety, or do-not-break boundaries;
- `Evidence`: references to necessary design frames, screenshots, or time ranges without copying the full visual content;
- `Acceptance`: visual/business acceptance conditions after Coding completes.

Do not include complete image sets, all video frames, Computer Use observation history, full OCR text, or the Primary Observation Agent's full analysis history.

Typical design workflow:

```text
Multimodal Flow
→ visual comparison
→ Visual Digest
→ Decision
→ narrow Handoff Contract
→ Coding Flow
→ implementation / tests
→ Multimodal Flow visual verification
→ semantic acceptance
```

If visual verification is needed after Coding, reuse the original Primary Observation Agent rather than making the Coding Primary Output role re-ingest the full visual reference set.

## Optional Output Agent inside Multimodal Flow

If the task does not involve Coding but requires expanding already-determined visual/temporal conclusions into a long report, large document, or other large artifact, the Decision Agent may create an Optional Primary Output Agent.

That Agent materializes output only. It does not take ownership of world state or reanalyze the complete visual input. If the Digest or Contract is insufficient for safe materialization, it asks the Decision Agent for targeted supplementation rather than requesting the full visual history.
