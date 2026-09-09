# Alibaba Qwen Coding Model Profile

This file owns the concrete Alibaba Qwen model bindings and reasoning-effort policy for the Qwen Code deployment. It is deployment policy, not the Token I/O Decoupling architecture. Host-specific mechanics are supplied by [`../hosts/qwen-code.md`](../hosts/qwen-code.md); generic Session semantics come from [`../../coding/session-model.md`](../../coding/session-model.md) and [`../../coding/runtime.md`](../../coding/runtime.md).

## Deployment intent

This Profile is deliberately asymmetric:

- **Input-side Reasoning** uses `qwen3.8-max` for high-value semantic decisions.
- **Primary Output** uses `qwen3.8-flash` for high-volume repository exploration, implementation/materialization, raw tool interaction, debugging, and mechanical verification.

The split is intentional. `qwen3.8-flash` is the cost-sensitive execution runtime; it must not be silently replaced by the parent Max Session simply because Max is technically capable of implementation.

## Role bindings and topology

At Coding Flow startup, confirm the current Session's actual model through the Host Adapter before applying this Profile.

- **Input-side Reasoning**: the preferred parent binding is `qwen3.8-max`.
- **Primary Output**: the required execution binding is `qwen3.8-flash`.
- **Normal two-Session mapping**: when the current Session is explicitly `qwen3.8-max`, keep semantic decisions in that parent and create/reuse an independent regular Qwen Code subagent explicitly bound to `qwen3.8-flash` for Primary Output.
- **Dual-role eligibility**: when the current Session explicitly confirms itself as `qwen3.8-flash`, this Profile allows the generic Runtime to use Single-Session Coding Mode if the required effort can be satisfied and no structural reason requires another Session. Do not create another Flash Worker merely to preserve a nominal Max/Flash topology.
- **Unexpected parent runtime**: if the current Session is neither an explicitly confirmed `qwen3.8-max` parent nor an explicitly confirmed dual-role `qwen3.8-flash` Session, do not infer eligibility from model-family similarity or aliases. Follow the unavailable rule.

The normal optimized deployment is therefore:

```text
qwen3.8-max parent
    -> Input-side Reasoning

qwen3.8-flash regular subagent
    -> sticky Primary Output / Primary Execution Session
```

## Qwen3.8 reasoning-effort ladder

Alibaba Cloud currently exposes the effective Qwen3.8 reasoning ladder as `low`, `medium`, and `xhigh`. Other generic effort names may be mapped by the provider: `minimal` maps to `low`, while `high` and `max` map to `xhigh`. This Profile uses only the native effective tiers and does not pretend that Qwen3.8 has a distinct effective `high` or `max` tier.

Use the tiers as follows:

- **`qwen3.8-max` parent**: prefer `xhigh` for substantive architecture, product, cross-module, schema/API, security/permission, or difficult debugging decisions. The input-side context is intentionally low-volume enough that high reasoning intensity is appropriate.
- **`qwen3.8-flash` Primary Output — default `medium`**: use `medium` for ordinary implementation, repository exploration, iterative debugging, routine refactoring, build/test loops, and most mechanically verifiable coding stages. This is the default cost/capability balance for the high-volume execution role.
- **Flash `xhigh`**: use `xhigh` only when the assigned output-side stage genuinely requires substantial local implementation judgment: non-trivial cross-module refactors, difficult debugging, complex test design, migration logic, concurrency behavior, or a bounded stage that repeatedly fails at `medium` despite a stable Semantic Contract.
- **Flash `low`**: use `low` only for strictly bounded, low-semantic-risk, easy-to-verify work such as exact search/extraction, formatter/linter/test execution, file/path metadata collection, literal replacements, simple generated tables, or other deterministic transformations.

Output length or repository size alone does not justify `xhigh`. Conversely, a task should not be forced to `low` merely because Flash is cheap.

## Effort-control limitation in Qwen Code

The Profile defines desired effective effort, but the Qwen Code Host Adapter is responsible for whether that effort can be applied independently to a particular regular subagent. A subagent's model selector does not itself prove an isolated per-subagent effort setting.

Therefore:

- exact `qwen3.8-flash` model identity is a hard requirement for Primary Output;
- when the Host can independently set and confirm the requested effort for that Worker, use the tier policy above;
- when the Host cannot independently vary a Worker's effort but can confirm the exact Flash model, use the deployment's explicitly configured Flash effort and report that limitation at the first relevant checkpoint if it materially differs from the requested tier;
- do not silently claim `medium`, `low`, or `xhigh` when the effective value is unknown;
- if a task specifically requires stronger reasoning than the confirmed Flash configuration can provide, escalate the bounded stage rather than pretending the control succeeded.

## Escalation

Qwen3.8 does not have a distinct effective `max` tier in this deployment. Targeted escalation therefore means one of two things:

1. raise a bounded Flash task from `medium` to confirmed `xhigh`; or
2. return a semantic blocker/evidence package to the `qwen3.8-max` parent for a new decision, then continue materialization in the established Flash Primary Execution Session.

Do not route routine Primary Output to Max as a generic escalation shortcut. Max owns high-value reasoning; Flash remains the default stateful execution owner.

When replacing a blocked Flash Worker is genuinely necessary, preserve reusable state through [`../../coding/context-exchange.md`](../../coding/context-exchange.md) before creating the replacement when possible.

## Cost-sensitive execution discipline

The economic value of this deployment depends on keeping high-volume work on Flash without weakening semantic ownership.

Current Alibaba Cloud public pricing varies by region, so this Profile does not encode prices as normative runtime constants. The important invariant is architectural rather than monetary: `qwen3.8-flash` is the Primary Output binding, while `qwen3.8-max` is reserved for high-value input-side reasoning. Price changes may justify revisiting this Profile but must not silently rewrite Core semantics.

Prompt/context caching should be used when the active provider supports it, but cache hits do not change role ownership. Historical reasoning content can itself become billable input; avoid redundant context retransmission and let Qwen Code/provider-native continuation preserve state where possible.

## Profile constraints

- Do not silently substitute another Qwen model, a generic `fast` fallback, or inherited parent model for the required `qwen3.8-flash` Primary Output binding.
- If `fast` is used operationally, confirm that it actually resolves to `qwen3.8-flash`; otherwise treat the binding as unavailable.
- Do not treat a `qwen3.8-max` parent as Primary Output merely because Flash launch or continuation failed.
- Do not use provider aliases whose concrete resolution cannot be confirmed when exact role binding matters.
- If the Host cannot create/reuse a regular Flash subagent for a required independent Primary Output Session, stop the corresponding substantive work and report the block.
- Purely read-only bounded diagnosis may continue when exact model identity is confirmed but effort cannot be controlled, provided the task does not depend on a stronger reasoning tier.

## Validation status

This Profile is based on current Alibaba Cloud Model Studio and Qwen Code public documentation for Qwen3.8 models, effort mapping, Skills, subagents, model selection, continuation, and provider configuration. Until a real Qwen Code CLI run validates the complete Max-parent/Flash-subagent mapping, the Runtime Registry must not label this deployment as locally smoke-tested.
