# Coding Delegation Mode Confirmation

[English](delegation-mode-confirmation.md) | [简体中文](delegation-mode-confirmation_zh_cn.md)

This module owns the conversation's initial mode selection, default, pre-selection restrictions, and Single-Agent route restrictions. It consumes and updates the state record; it does not define count locking, re-entry, child creation, or lifecycle.

## General rules

### Session mode selection

On the first Coding directive of a conversation, the root parent must:

1. Honor an explicit valid mode/count choice in the directive without asking again.
2. If no valid choice is present, present this numbered menu. Only when the Mode gate must be released and there is still no valid user choice, use the stated default; an unanswered prompt by itself does not require releasing the gate. Explicit no-preference also selects the default:
   1. Multi-Agent Coding, 1 child (recommended and default).
   2. Single-Agent Coding, 0 children.
   3. Multi-Agent Coding, custom positive child count (enter the integer as free text).
   4. Custom instruction (enter it as free text; map it to a maintained mode and valid count).
3. For option 3, require an explicit positive integer. If it is missing or invalid, ask one focused follow-up and keep the Mode gate unreleased; never substitute one. For option 4, use the text only to derive a maintained Single-Agent or Multi-Agent route and valid count, while recording other task constraints. If it is missing, invalid, ambiguous, conflicting, or requests an unmaintained route, ask one focused clarification and keep the gate unreleased. Custom text cannot override higher-priority permissions, safety, repository, authorization, or capability boundaries, and cannot create a route or capability.
4. Record a valid user selection as `mode_source: explicit`. Record the no-reply or explicit no-preference default as `mode_source: default`, `mode: Multi-Agent Coding`, and `child_count: 1`. Apply the count owner before route release. Keep the mode and count fixed for the current conversation.
5. Treat the released Multi-Agent count as reserved capacity only. Displaying the menu, selecting a mode, or locking the count never creates or initializes a child. Creation remains subject to the role, output-type, and released-slice gates.

The default selects a workflow mode and reserved count only; it does not bypass a task-level prohibition or create a capability. If a higher-priority restriction forbids children, it controls. If the required record capability is absent, block the dependent route rather than pretending it exists.

No child may be created until the count gate has released a valid positive count, the relevant role and concrete slice are released, and the output is code/configuration implementation or authorship/editing of this Skill's instructions or reference documents. Ordinary non-Skill documentation is authored by the root parent, including in tasks that also contain code changes. If the conversation is already locked to Single-Agent Coding, apply the Re-entry owner before considering any conflicting later instruction.

### Single-Agent Coding

After confirmation, keep all work in the current Session. Do not create, fork, hand off to, message, replace, or otherwise manage a child Agent or additional Session. Structural benefit, verification, documentation/Git needs, bootstrap, recovery, or runtime convenience are not exceptions. Independent verification remains a semantic requirement, but is unavailable on this route.

## Codex CLI / ChatGPT Desktop optimizations

### ChatGPT Desktop

When the active runtime actually exposes `request_user_input_async`, one question may present the menu with a free-text entry path, for example: `request_user_input_async({questions: [{title: "Select a Coding mode", options: ["1. Multi-Agent Coding, 1 child (recommended/default)", "2. Single-Agent Coding, 0 children", "3. Multi-Agent Coding, custom positive child count", "4. Custom instruction"]}]})`. The tool accepts at most 1–3 questions; options do not disable free-text answers, and the answer arrives asynchronously as a new user message. A preselected first option is not a submitted user choice. The tool cannot show a text field conditionally only for options 3 or 4, so state in the same prompt that option 3 requires a positive integer and option 4 requires the complete instruction; use the focused follow-up from the general rules for missing or invalid input. Do not infer a choice while the response is pending. If no valid choice arrives and the Mode gate must be released to proceed, apply the default; do not introduce a timer. If the tool is not exposed, send the numbered menu as ordinary text and receive the response through the normal conversation channel. Never use GUI or Computer Use to present or operate the menu.

### Codex CLI

In Codex CLI, present the four-option numbered menu as plain text, for example `1. Multi-Agent Coding, 1 child (recommended/default); 2. Single-Agent Coding, 0 children; 3. Multi-Agent Coding, custom positive child count; 4. Custom instruction`. Receive a later text reply such as `3: 4` or `4: ...` for the custom instruction; this does not assume a structured form. If no valid choice arrives and the Mode gate must be released to proceed, apply the default; do not introduce a timer. No structured form/input tool is assumed in this Session, so do not claim a conditional input field exists. If the terminal cannot surface a reply, keep the gate unreleased unless it must be released to proceed; then follow the general default or focused follow-up rules without adding a time limit.

## Claude Code CLI / Claude Desktop optimizations

When `AskUserQuestion` is available and authorized in the active Claude Code Session, call it with a `questions` array; each question supplies `question`, `header`, and `options` (each option has `label` and `description`), with `multiSelect: false` for this single mode choice. For example: `AskUserQuestion({questions: [{question: "Which Coding mode should this conversation use?", header: "Mode", options: [{label: "1. Multi-Agent Coding", description: "Reserve 1 child (recommended/default)."}, {label: "2. Single-Agent Coding", description: "Use 0 children."}, {label: "3. Multi-Agent Coding", description: "Enter a custom positive child count."}, {label: "4. Custom instruction", description: "Map the instruction to a maintained mode and count."}], multiSelect: false}]})`. The user can select an option or provide free text through `Other` or the notes field; apply the general validation and clarification rules to that text. Questions wait for an answer by default. Only a user-configured `askUserQuestionTimeout` setting of `60s`, `5m`, or `10m` can enable auto-continue; do not change that setting or add an implicit timeout. If the result reports a timeout, follow the returned result and do not invent a user selection; apply the general missing-choice/default rule only if the Mode gate must be released. If the tool is unavailable, ask the same numbered question in ordinary text.

## Related concepts

- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate count locking ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate gate re-entry ownership.
- [Coding Delegation State Record](delegation-state-record.md) — locate state record ownership.
- [Coding Child Creation](delegation-child-creation.md) — locate child creation ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle ownership.
