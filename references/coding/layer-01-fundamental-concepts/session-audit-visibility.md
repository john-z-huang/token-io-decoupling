# Coding Session Audit Visibility

[English](session-audit-visibility.md) | [简体中文](session-audit-visibility_zh_cn.md)

This module defines session audit-visibility presets, reasoning-summary cadence, and Worker-log visibility. It defines configuration values and their display semantics; it does not own how a workflow asks for, times, resumes, or migrates configuration records.

## General rules

### Configuration values

The root parent owns the session configuration. Users may select `audit_mode`, `root_reasoning_cadence`, and `worker_reasoning_cadence`; each field has its own source. These are Skill policies, not native product switches.

```yaml
audit_mode: balanced
root_reasoning_cadence: milestone_only
worker_reasoning_cadence: full
source: {audit_mode: default, root_reasoning_cadence: default, worker_reasoning_cadence: default}
revision: session-audit/v2
```

| Field | Legal values | Default | Meaning |
| --- | --- | --- | --- |
| `audit_mode` | `economy`, `balanced`, `full` | `balanced` | Selects the Root visible-copy preset. |
| `root_reasoning_cadence` | `full`, `milestone_only`, `off` | `milestone_only` | Selects optional Root summary cadence. |
| `worker_reasoning_cadence` | `full`, `milestone_only`, `off` | `full` | Selects optional Worker summary cadence independently. |
| `source.<field>` | `explicit`, `default` per selectable field | `default` | `explicit` means the user selected that field; `default` means the policy supplied it. |
| `revision` | `session-audit/v2` | `session-audit/v2` | Schema and policy-semantics revision; prose-only edits do not change it. |

The task-record shape and configuration-prompt fields are defined by the [delegation state record](delegation-state-record.md). The selected route owns collecting and updating that record.

### Visible-copy presets

The complete actual safe task and return bodies remain available in every preset. Root reads the complete actual Worker return before relying on it. A preset controls only Root's visible copy; it does not reduce evidence requirements or Worker visibility. For Worker message handling and safe-body rules, follow [Child Message Visibility](delegation-child-message-visibility.md).

| Preset | Root outbound visible copy | Root inbound visible copy |
| --- | --- | --- |
| `economy` | Preview with at most 3 items: objective, allowed changes, return conditions. | Decision-relevant summary. |
| `balanced` | Complete related safe message only for a defined trigger below; otherwise the `economy` preview. | Complete related safe message only for a defined trigger below; otherwise the `economy` summary. |
| `full` | Complete safe message body. | Complete safe message body. |

For an `economy`/`balanced` preview, count displayed Markdown source including whitespace and link text/destinations: at most 3 items and 600 Unicode code points. For an inbound summary, the corresponding limits are 5 items and 800 Unicode code points; fields, in order, are conclusion, evidence pointers, key basis, risks/blockers, and next step, omitting fields without a value. Count characters, not tokens; no per-message counting-tool call is needed. Keep the complete body separately available. If a higher-priority instruction or material authorization/failure evidence cannot fit, exceed only as far as necessary and state why; never silently truncate or split a copy to evade the budget. The budget does not constrain full display or Worker visibility. Summaries must not reveal private reasoning.

`economy` still allows and requires necessary user-facing progress, authorization, failure, verification, stage-acceptance, and final reports. Those reports do not replace the complete actual body or its review.

### `balanced` full-display triggers

Display the complete related safe message only when an observable event occurs: an approved Contract goal, acceptance condition, path, or allowed effect changes; authorization is explicitly granted or withdrawn; an executed check fails or evidence directly conflicts/is disputed; or the user requests precise audit of this exchange. A new slice wholly within the existing Contract is not a trigger. If trigger status is uncertain, preserve the facts for the Root's decision. Do not automatically escalate all messages to `full`.

### Worker-log visibility

`worker_log_visibility` describes current-Session access to the complete safe Worker inbound/outbound conversation record, not just Root's returned final body or original encrypted runtime logs. `available` requires direct evidence locating the complete record; tool existence alone is insufficient. `unverified` means no affirmative success/failure evidence, including not yet checked. `unavailable` requires explicit missing capability, access failure, or equivalent negative evidence. `Not applicable` is valid only when no Worker was created, with that reason in the evidence field.

Check once when Worker-log evidence is first needed; update only on new actual access/capability evidence or failure, never per message. If a task explicitly depends on this log evidence, unavailable/unverified status blocks that audit dependency. Otherwise report the limitation and continue; the complete actual return body remains required.

### Summary cadence

Root and Worker cadence values apply independently. For summary turn boundaries and content format, follow [Reasoning Summary Visibility](reasoning-summary-visibility.md). `full` emits the required safe summary at each completed boundary. `milestone_only` emits on these observable events:

| Event | Emit when |
| --- | --- |
| Material decision | A new/changed confirmed choice changes how the next slice is performed or what counts as acceptance; routine reads or command choices do not qualify. |
| Authorization change | Permission for an allowed effect is explicitly granted or withdrawn. |
| Verification failure | An executed check fails, or current acceptance criteria have direct failing evidence. |
| Blocker | The authorized next action cannot continue because required permission, capability, or evidence is actually missing. |
| Stage acceptance | Root finally accepts declared stage evidence and releases the next stage; ordinary progress is not acceptance. |

Deduplicate by event category plus related decision/evidence epoch. Emit each fact once, merge multiple triggers in one turn, and emit again only when the relevant fact or epoch materially changes. Do not infer materiality from elapsed time or repeated activity. `off` suppresses optional summaries only; required reports, evidence, Control updates, Progress Signals, and higher-level periodic updates remain required. No cadence permits private-reasoning disclosure.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization is defined for this concept. Follow the general rules using only capabilities and evidence available to the current Session.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization is defined for this concept. Follow the general rules using only capabilities and evidence available to the current Session.

## Related concepts

- [Coding Child Message Visibility](delegation-child-message-visibility.md) — apply safe message visibility rules.
- [Coding Reasoning Summary Visibility](reasoning-summary-visibility.md) — apply summary boundaries and format.
- [Coding Delegation State Record](delegation-state-record.md) — locate session-configuration record fields.
