# Candidate Compliance Preflight

[English](candidate-compliance.md) | [简体中文](candidate-compliance_zh_cn.md)

This owner defines optional read-only structural preflight for proposed repository changes. It does not own authorization to write, full verification, or final acceptance.

## General rules

### Review candidates against trusted current state

When an authorized workflow needs early structural feedback, assess the proposed candidate set as an in-memory overlay against a trusted checkout. Candidate files may satisfy each other's direct mirror and local-link checks. A baseline records the observed file state; it is not a lock, write grant, or guarantee that the state remains unchanged.

Keep the policy scope explicit. Skill-maintenance rules apply only to a `skill_maintenance` request; a `generic_project` request must not silently apply this repository's Skill rules to another project. When a trusted service is configured, it additionally limits requests to its allowed scopes. Without a configured reader, static candidate checks may still run, while checks that depend on trusted disk state or baseline evidence are unknown rather than passing. The candidate payload must not choose its own trusted root or policy source.

Interpret each result separately as pass, fail, unknown, or not applicable. Treat unknown, failed, omitted due to a limit, and stale-baseline results as unresolved. Correct the cause or supply the missing evidence and repeat against current candidates. A successful preflight covers only the checks actually returned for that overlay and reader observation.

Preflight does not scan unchanged documents for inbound links, prove bilingual semantic equivalence, execute repository code, run all project checks, authorize applying files, or replace current-state Verification and Acceptance. Complete the applicable authoritative checks after changes are applied.

## Codex CLI / ChatGPT Desktop optimizations

When exposed and authorized, call `validate_decoupling_compliance` with `payload.request`, explicit `policy_scope`, candidate paths, operations, content, and baselines. The trusted root, enabled scopes, and read-only baseline/target reader come from operator code configured when the server starts; neither the payload nor current directory chooses them. The tool does not write files, run subprocesses, execute candidate code, or call an API.

For Skill maintenance, inspect returned checks for mirror presence, applicable link language/layer rules, direct local targets, and Layer-01 structure. Review `not_evaluated` because reverse inbound links, mirror meaning, and full CI are outside the preflight. Resolve `unknown`, `fail`, truncation, or budget findings before proceeding. A passing result is not authorization; obtain write authority independently and recheck current state before applying.

## Claude Code CLI / Claude Desktop optimizations

This repository's MCP Server supports local Codex CLI only; generic Claude MCP support does not authorize direct use of this server. No Claude-specific direct-tool optimization is maintained here. Follow general rules using only capabilities actually exposed and authorized in the current Session; if a trusted reader is unavailable, mark disk-dependent checks unknown and use the applicable established verification route.

## Related concepts

- [Enhanced Host Binding](../enhanced-native-state/enhanced-host-binding.md) — owns trusted identity and per-call guards.
- [Workflow Routing Advice](workflow-routing-advice.md) — owns optional stage suggestions.
- [Output Materialization](output-materialization.md) — owns controlled output preparation and application.
