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

## Layer-03 route completeness

- Each final Layer-03 workflow must contain one primary numbered execution checklist. Start with evidence that Contract, Environment, capability inventory, and Mode have passed before route entry; then order every Layer-02 checkpoint and Layer-01 concept that the route actually consumes, including concepts reached through operational checkpoint requirements. A `Related concepts` navigation link alone does not make an owner an execution dependency.
- For every consumed owner, link its same-language file at the step where it applies and state the concrete action to confirm, the required result or evidence, and what to do when it fails or is unavailable. For conditional owners, state the trigger and require an explicit `Not applicable` reason when the trigger is absent. Do not replace a check with a bare link or a collective phrase such as “apply all references.”
- Make the order executable: pre-route gates; Session/role and capability boundaries; bounded context; Decision and planning; slice release; child creation/dispatch only when authorized; Implementation and Control; current-state Verification; conditional Repair and re-verification; Documentation; Git; final Acceptance. Include the applicable return loop and changed-epoch checks so a smaller model cannot skip a required boundary.
- Before changing a route, compare its checklist against all operationally consumed lower-layer owners and their pass conditions. Update the checklist and both language mirrors in the same change set whenever a consumed owner or its execution requirement changes. Keep lower-layer files authoritative; route checklists summarize and sequence their requirements without inventing new policy.

## Codex and Claude Code tool parity

Keep provider-specific tool and instruction optimizations in the single [Runtime and Model Provider Support](references/coding/layer-01-fundamental-concepts/runtime-provider-support.md) owner and its Chinese mirror. Whenever a change tunes this Skill for a tool or instruction found in Codex source, inspect the corresponding Claude Code capability in its current official documentation or exposed runtime controls. Whenever a change tunes this Skill for Claude Code, perform the same check for Codex. Do this before treating either runtime's behavior as shared.

For each such change, complete this sequence in both language mirrors:

1. Name the source runtime's exact tool, instruction, or control and the behavior the Skill relies on; retain a verifiable source-code or official-documentation pointer, or a runtime observation.
2. Identify and verify the other runtime's corresponding tool or control. When it exists, specify its concrete invocation, capability limits, and any different lifecycle or parameter behavior.
3. When no corresponding capability exists, explicitly say so in the other runtime's section and state whether its Agent must use the runtime default, maintain equivalent evidence through an available mechanism, or mark that optimization `Not applicable`. Do not imply feature parity or block unrelated work solely because an optional optimization is absent.
4. Update affected workflow checkpoints and Layer-03 route checks in the same change set, keeping provider-specific details in the single owner document. Confirm the English and Chinese instructions remain equivalent before completing the documentation checks.

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
git diff --check
```

Also manually review changed local Markdown targets, language mirrors, owner names, and the absence of HTML or pseudo-links. If a validator conflicts with the current documentation rules, update the validator and the affected documentation together; do not bypass the check.
