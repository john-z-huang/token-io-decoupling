# Repository instructions

Multilingual documentation requirements are maintained in [`MULTI_LINGUAL.md`](MULTI_LINGUAL.md).

Any Agent or contributor that creates, edits, renames, moves, or deletes documentation in this repository must load and follow that file before making documentation changes.

## Documentation ownership and atomicity

- Every maintained Markdown document must have one clear, reusable responsibility. Its filename, title, opening ownership statement, sections, and links must describe the same responsibility.
- If a document combines independently reusable concepts, split it into separate English and `_zh_cn.md` owner pairs. Do not preserve a complex reverse-concept combination merely to avoid creating files.
- Do not leave duplicated former sections or an old tail after a split. The original document must retain only its declared owner responsibility; moved content belongs only to the new owner.
- Layer-01 documents own fundamental concepts. Layer-02 documents own individual workflow checkpoints or narrowly scoped checkpoint owners. Layer-03 documents compose lower-layer owners into an executable route with explicit checks, but must not redefine their policies.
- A route-composition document may order owners and restate their operational checks and required evidence; it must not become a second owner for mode gates, delegation lifecycle, environment capability rules, repair execution, verification independence/reporting/epochs, or other lower-layer concepts.
- New owner files and any composition entries that consume them must be updated in the same change set. Keep English and Simplified Chinese files semantically mirrored with equivalent constraints and action strength.

## Layer-01 three-module structure

Every existing or new Layer-01 Markdown owner and its Chinese mirror must have these three top-level content sections, exactly once and in this order, after the opening ownership statement:

1. `## General rules` / `## 通用规范`: provider-independent requirements and the concept's existing subtopics.
2. `## Codex CLI / ChatGPT Desktop optimizations` / `## Codex CLI / ChatGPT Desktop 特别优化指令`: only the applicable Codex or ChatGPT Desktop instructions for this concept.
3. `## Claude Code CLI / Claude Desktop optimizations` / `## Claude Code CLI / Claude Desktop 特别优化指令`: only the applicable Claude Code or Claude Desktop instructions for this concept.

Keep concept subtopics under these sections as level-three headings. When a provider has no special optimization for this concept, retain its section and state explicitly that there is currently none and that the Agent follows the general rules. Keep `Related concepts` / `相关概念` as a separate navigation section after the three modules. Run `python3 scripts/check-layer-01-sections.py` after every Layer-01 edit or addition; a missing, duplicate, reordered, or empty module is not complete.

## Layer-02 and Layer-03 provider neutrality

- Layer-02 owns only provider-independent workflow checkpoints; Layer-03 owns only the provider-independent composition and ordered description of complete routes. Neither layer may name a model vendor, an Agent product, a provider-specific model, tool, parameter, command, configuration path, or launch procedure, or introduce a provider-specific optimization.
- Put every provider-specific instruction in the applicable Layer-01 owner and its Codex or Claude section. Layer-02 and Layer-03 may link to that owner and require a generic capability or result, but must not restate the provider-specific operation, even as an example or parenthetical list.
- When moving a provider detail out of Layer-02 or Layer-03, preserve the generic action, evidence, and failure boundary there. Update both language mirrors and the relevant Layer-01 provider sections in the same change set.
- Run `python3 scripts/check-layer-02-03-provider-neutrality.py` for every change to either layer. Any vendor or Agent-product term reported by the script blocks completion; do not hide the term in code fences, links, or altered spelling to evade the check.

## Layer-03 route completeness

- Each final Layer-03 workflow must contain one primary numbered execution checklist. Start with evidence that Contract, Environment, capability inventory, and Mode have passed before route entry; then order every Layer-02 checkpoint and Layer-01 concept that the route actually consumes, including concepts reached through operational checkpoint requirements. A `Related concepts` navigation link alone does not make an owner an execution dependency.
- For every consumed owner, link its same-language file at the step where it applies and state the concrete action to confirm, the required result or evidence, and what to do when it fails or is unavailable. For conditional owners, state the trigger and require an explicit `Not applicable` reason when the trigger is absent. Do not replace a check with a bare link or a collective phrase such as “apply all references.”
- Make the order executable: pre-route gates; Session/role and capability boundaries; bounded context; Decision and planning; slice release; child creation/dispatch only when authorized; Implementation and Control; current-state Verification; conditional Repair and re-verification; Documentation; Git; final Acceptance. Include the applicable return loop and changed-epoch checks so a smaller model cannot skip a required boundary.
- Before changing a route, compare its checklist against all operationally consumed lower-layer owners and their pass conditions. Update the checklist and both language mirrors in the same change set whenever a consumed owner or its execution requirement changes. Keep lower-layer files authoritative; route checklists summarize and sequence their requirements without inventing new policy.

## Layer-03 workflow maps

- Each final Single-Agent and Multi-Agent Layer-03 route and its Simplified Chinese mirror must have exactly one `## Workflow map` / `## 工作流路线图` section above its sole ordered execution checklist, containing one fenced `mermaid` flowchart. The map is an executable navigation and selective concept-loading guide, **not** a new policy owner; lower-layer references in the checklist remain authoritative for actions, evidence, and failure boundaries.
- Every numbered checklist step must correspond to a stable, ordered map checkpoint ID (`S01`… for Single-Agent, `M01`… for Multi-Agent). Use equivalent IDs and directed edges in each language mirror, with equivalent conditional decisions. The Single-Agent map excludes child creation, dispatch, child lifecycle, Worker memo, and cross-Worker exchange branches; the Multi-Agent map includes gated role allocation, context/Bootstrap and memo decisions, slice release before creation/dispatch, verification, conditional repair and changed-epoch re-verification, documentation, Git, and acceptance.
- Show explicit skip/`Not applicable`, block, and return paths rather than suggesting that every conditional concept must run. Never draw a shortcut around mode/capability authorization or current-state verification. A map node may summarize a checkpoint but may not redefine the lower-layer owner’s policy. When any consumed owner, route order, branch, or checklist requirement changes, update **both** diagrams and **both** checklists in the same change set.
- Run `python3 scripts/check-layer-03-workflow-maps.py` on every Layer-03 route or rule change. This script enforces map presence/order, fixed checkpoint identity and checklist sequence, required branches/edges, language-mirror graph equivalence, mode isolation, and CI integration. The structural validator does not prove that translated prose or every policy interpretation is semantically equivalent; review those manually as well.

## Codex and Claude Code tool parity

Keep each concept's provider-specific optimization and tool correspondence in that Layer-01 owner's provider section. Keep only cross-cutting runtime identification and model/effort bindings in the single [Runtime and Model Provider Support](references/coding/layer-01-fundamental-concepts/runtime-provider-support.md) owner and its Chinese mirror; other owners link to those bindings instead of repeating them. Whenever a change tunes this Skill for a tool or instruction found in Codex source, inspect the corresponding Claude Code capability in its current official documentation or exposed runtime controls. Whenever a change tunes this Skill for Claude Code, perform the same check for Codex. Do this before treating either runtime's behavior as shared.

For each such change, complete this sequence in both language mirrors:

1. Name the source runtime's exact tool, instruction, or control and the behavior the Skill relies on; retain a verifiable source-code or official-documentation pointer, or a runtime observation.
2. Identify and verify the other runtime's corresponding tool or control. When it exists, specify its concrete invocation, capability limits, and any different lifecycle or parameter behavior.
3. When no corresponding capability exists, explicitly say so in the other runtime's section and state whether its Agent must use the runtime default, maintain equivalent evidence through an available mechanism, or mark that optimization `Not applicable`. Do not imply feature parity or block unrelated work solely because an optional optimization is absent.
4. Update the affected Layer-01 concept owner's provider sections and, when their generic outcomes change, the workflow checkpoints and Layer-03 route checks in the same change set. Keep cross-cutting runtime/model bindings in the runtime owner, keep Layer-02/03 provider-neutral, and confirm the English and Chinese instructions remain equivalent before completing the documentation checks.

## Markdown references and layer direction

- Use real relative Markdown links for document references. Never replace a valid Markdown link with HTML, a bare path, or backticked pseudo-link text to evade validation.
- Valid Markdown references are encouraged. Validators must reject unresolved, cross-language, or layer-violating references; they must not reintroduce a blanket ban on legitimate Markdown links.
- Every new or materially processed bilingual owner document should contain a visible language-switch link near the top and a `Related concepts`/`相关概念` section with same-language Markdown links where related owners exist.
- English documents link to English targets; Simplified Chinese documents link to `_zh_cn.md` targets. Cross-language links are reserved for the visible language switch.
- Follow the current `scripts/check-doc-layer-links.py` direction rules: ordinary Layer-01 references target Layer-01; ordinary Layer-02 references target `references/` or Layer-01; ordinary Layer-03 references target shared protocols, Layer-01, or Layer-02. Do not use link formatting to bypass these rules.
- Every local Markdown target must exist, and links must point to the current owner filename rather than an obsolete pre-split name.

## Worktree and delegated documentation workflow

- For documentation atomicization or restructuring, use an isolated worktree when the task requests worktree development. Do not modify the main worktree from the delegated worker.
- Work in small document slices. The subagent first reads only the named worktree files and returns an analysis; the parent reviews the boundaries and sends the final edit instruction; the subagent then edits only the approved slice.
- Subagents must follow minimum-reading scope: do not scan all documents repeatedly, and do not read unchanged Skill documents from the main workspace. Read only the current worktree files needed for the slice and their direct link targets.
- After each approved slice, the parent reviews filenames, ownership boundaries, mirrors, and links before allowing a local commit. Keep commits small and use Chinese commit messages. Do not push to GitHub unless explicitly requested.
- Use an independent read-only verification agent when a batch is ready for final review. It must not repair, stage, commit, or push; it reports filename/content mismatches, relationship violations, stale owner names, and broken links.
- Preserve unrelated user changes and never stage repository-generated or pre-existing untracked state such as `.serena/` unless explicitly requested.

## Iterative Skill clarity-review directive

When the root directive explicitly requests an iterative Skill-document clarity review, use this reusable sequence in a new isolated Git worktree:

1. Create one child Agent with low reasoning effort and assign it only the named Skill worktree. The child first reads the current worktree's Skill entry, workflow, and only the direct reference documents needed for the review; it does not modify files in the first pass.
2. Require the child to return evidence-backed ambiguities, contradictions, missing execution boundaries, or confusing passages, including exact file paths, headings, consequences, and minimal repair directions. The child must not create recursive agents or contact unrelated Sessions.
3. The parent reviews the findings, defines a Semantic Contract and one narrow approved document slice, then dispatches explicit paths, allowed mutations, return conditions, and the unreleased boundary. The child edits only that slice and returns the changed paths, diff summary, checks, and any remaining uncertainty.
4. The parent reviews the child’s proposed result against the Contract, ownership boundaries, English/Chinese mirrors, links, and scope. If the result is not approved, do not commit it; send only a narrow repair instruction and repeat the review. If it is approved, require the child to run the applicable documentation checks, stage only the approved files, and create one local commit with a Chinese commit message. Never push to a remote unless the root directive separately authorizes it.
5. After every approved commit, require the child to reread the current worktree Skill documents and report whether any material ambiguity or improvement remains. Continue the parent-review/child-repair/approval/commit cycle until the child reports no remaining material confusion or actionable improvement and the parent independently accepts that conclusion.
6. At completion, verify the final worktree, commit scope, bilingual mirrors, required checks, and absence of remote effects. Preserve unrelated changes and leave the worktree available unless cleanup is explicitly requested.

This directive controls the review loop only; it does not authorize unrelated implementation, history rewriting, remote operations, or changes outside the approved document slices.

## Required validation

Before completing any documentation slice, run all of the following from the repository root:

```bash
python3 scripts/check-multilingual-docs.py
python3 scripts/check-doc-layer-links.py
python3 scripts/check-layer-01-sections.py
python3 scripts/check-layer-02-03-provider-neutrality.py
python3 scripts/check-layer-03-workflow-maps.py
python3 -m unittest discover -s tests -p 'test_check_layer_03_workflow_maps.py'
git diff --check
```

Also manually review changed local Markdown targets, language mirrors, owner names, and the absence of HTML or pseudo-links. If a validator conflicts with the current documentation rules, update the validator and the affected documentation together; do not bypass the check.
