# ChatGPT Standard Chat + OpenAI Coding Deployment

This file registers the OpenAI Coding deployment for the **standard ChatGPT chat environment**. Here, ChatGPT means a normal conversation in the ChatGPT product and **explicitly excludes ChatGPT Work**. Do not infer Work-only capabilities such as a cloud computer, long-running task execution, cross-application workflows, or other Work features as capabilities of standard chat.

This deployment covers both deployment concerns:

- **Host Adapter**: how standard ChatGPT chat exposes the current conversation, tools/connectors, file or code-execution capabilities, and whether any independent execution context exists.
- **Model Profile**: how OpenAI runtimes may perform Coding responsibilities only within the model identity and control capabilities actually exposed by the current chat.

Coding role definitions, checkpoints, the Context Firewall, verification boundaries, and Context Exchange remain defined by [`../../coding/runtime.md`](../../coding/runtime.md), [`../../coding/session-model.md`](../../coding/session-model.md), and the other Core documents. This file does not change those semantics.

## Host identity and scope

Use this deployment only when the active host is actually a standard ChatGPT chat environment. Do not use this Host Adapter for:

- ChatGPT Work;
- Codex CLI or the Codex app;
- Claude Code, Qwen Code, or another Code Agent;
- a prompt, repository document, or Skill installation path that merely mentions `ChatGPT`.

Host identity must be resolved from facts actually exposed by the current product environment.

## Capability-first rule

Standard ChatGPT capabilities may vary by product version, account configuration, conversation type, and connected tools. This deployment therefore does not treat any tool or execution capability as guaranteed merely by the ChatGPT product name.

At the start of each task conversation, resolve the runtime only from capabilities actually exposed by the current chat, including:

- whether the current model identity can be confirmed;
- whether later execution models can be explicitly selected or controlled;
- whether the host can create a genuinely independent execution Session with separate context ownership;
- whether code execution, filesystem, repository, or connector tools are available;
- whether those tools support the reads, writes, validation, and delivery operations required by the task;
- whether a provable isolation boundary exists rather than only a logical phase inside one conversation.

Treat every capability that is not exposed as unavailable. Do not fill gaps from product knowledge, prior conversations, or guesses about future functionality.

## Standard chat is not ChatGPT Work

This deployment must preserve that boundary in both documentation and runtime decisions:

- do not use Work's cloud computer or long-running execution as evidence of a standard-chat capability;
- do not map multi-step execution, application navigation, or persistent workspace behavior that may exist in Work to standard-chat Sessions;
- if the user requests Work, use a separate Work deployment design rather than expanding the meaning of this Adapter.

## Role mapping

### Input-side Reasoning

The current ChatGPT parent conversation owns high-value semantic analysis, problem definition, solution selection, authorization boundaries, checkpoints, and final acceptance ownership.

### Primary Output

If the current standard chat explicitly exposes creation of an independent execution Session and can satisfy the model and parameter controls required by the active Model Profile, Primary Output may map to that independent execution context.

If it does not, Primary Output may be performed as a logical responsibility by the current conversation, but this is only **Single-Session responsibility isolation**:

- preserve approved scope, output boundaries, checkpoints, and handoff rules;
- do not claim that an independent Worker was created;
- do not claim that output tokens were transferred to another model or Session;
- do not describe phased reasoning within one conversation as delivering the full economic benefit of Token I/O decoupling.

### Change Verification

Independent final verification of substantive functional changes still requires the independence defined by Core. If the current standard chat does not expose a genuinely independent verifier Session or an equivalent isolated execution context:

- the current conversation may run provisional feedback checks, test commands, or evidence collection;
- those results must not be labeled independent Change Verification;
- rereading the diff or “switching roles” inside the same conversation does not create independent verification evidence;
- when independent verification is required but unavailable, report that boundary through unavailable handling.

### Documentation/Comments & Git Operations

Standard chat may perform documentation, code-comment, Git, and GitHub delivery responsibilities when the user has authorized the operation and the available tools provide sufficient capability. If those operations are performed through GitHub, Google Drive, or another connector, the connector is only a tool channel and does not constitute an independent Agent or Session.

All writes remain subject to project workflow rules, user authorization, and connector permissions. Tool availability is not automatic authorization.

## Tool and connector mapping

Standard ChatGPT chat may expose GitHub, Google Drive, code execution, file-processing, or other tools. They can be capabilities used by the active responsibility, subject to these rules:

1. A tool call belongs to the context of the Session that invoked it; unless the host explicitly proves a separate context, one tool call does not count as a subagent.
2. Large connector results should follow Core Evidence-on-Demand and Context Exchange rules rather than being copied wholesale.
3. When a tool lacks permission, write support, or filesystem isolation, do not bypass that limitation through another unauthorized channel.
4. Multiple logical responsibilities may use the same connector, but changing responsibility does not create new verification independence.

## Model Profile

This deployment does not hard-code that standard ChatGPT always runs a particular model. Model bindings may use only facts the current conversation can confirm.

- **Input-side Reasoning**: use the ChatGPT model selected by the user and actually running for the current parent conversation.
- **Primary Output / auxiliary Worker**: bind a concrete OpenAI model only when the host exposes an independent execution context and permits explicit selection of the target model.
- **Reasoning effort**: apply a concrete effort level only when the host explicitly exposes that control; otherwise record it as host-managed rather than guessing a level.
- Do not infer that another cheaper model has performed output work merely because the parent conversation uses a higher-capability model.

Accordingly, when standard chat has no independent model-routing capability, this deployment mainly provides **Core compatibility / responsibility isolation**, not a claim of full cross-model Token I/O decoupling.

## Session and context ownership

When only one Session can be confirmed in the current standard chat:

- use that Session for multiple logical responsibilities;
- keep each responsibility within its Approved scope, Return conditions, Unreleased boundary, and checkpoint rules;
- use summaries, files, or stable evidence references to reduce unnecessary raw-context repetition;
- do not invent worker IDs, session IDs, independent model identities, or independent verdicts.

Only when the host actually provides independent execution contexts should Core multi-Session topology and Context Exchange isolation rules be applied.

## Dispatch Preview

Describe an action as dispatch/delegation only when a real independent execution context is being used, and then follow the shared Dispatch Preview rule for a short user-visible preview.

A responsibility or slice change inside the same ChatGPT conversation should be described as a phase or slice transition. Do not use wording such as “created a subagent” or “delegated to Luna” when no such independent Session exists.

## Unavailable handling

Downgrade or block rather than inventing capabilities in these cases:

- Current model cannot be confirmed: describe it as host-managed and do not claim an exact model binding.
- Independent Session creation is unavailable: enter Single-Session responsibility isolation; independent Change Verification must not be fabricated.
- Worker model selection is unavailable: do not claim cross-model output displacement.
- Repository or file write capability is unavailable: return only plans, patch suggestions, or other artifacts the current tools really support.
- User authorization is absent: stop the corresponding write operation.

If acceptance criteria require an independent verifier, an explicitly lower-cost Worker, or real Session isolation and standard chat cannot provide those capabilities, state that the current Host does not satisfy that runtime requirement.

## Validation status

This deployment registers a **limited, capability-driven mapping for standard ChatGPT chat**. Its confirmed design target is to preserve Coding Core responsibilities and boundaries when independent subagent capability is absent while refusing to fabricate multi-Session or cross-model benefits.

Until standard ChatGPT chat actually exposes and exercises independent Session creation, model routing, and isolated verification, those paths must remain marked unverified. Real use of ChatGPT Work must not be counted as validation evidence for this deployment.
