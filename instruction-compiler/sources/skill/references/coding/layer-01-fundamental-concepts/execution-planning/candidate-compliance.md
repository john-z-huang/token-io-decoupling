# Candidate Compliance Preflight

[English](candidate-compliance.md) | [简体中文](candidate-compliance_zh_cn.md)

This owner defines optional read-only structural preflight for proposed repository changes. It does not own authorization to write, full verification, or final acceptance.

## General rules

### Review candidates against trusted current state

When an authorized workflow needs early candidate feedback, assess the bounded paths, operations, content envelope and baseline facts against a trusted checkout. A baseline records the observed file state; it is not a lock, write grant, or guarantee that the state remains unchanged.

The product preflight provides generic candidate path and baseline checks only. It does not select a project-specific authoring policy from the task label. The candidate payload must not choose its own trusted root or policy source; missing required trusted-reader or baseline evidence remains unknown rather than passing. Static envelope validity cannot replace current disk evidence.

Interpret each result separately as pass, fail, unknown, or not applicable. Treat unknown, failed, omitted due to a limit, and stale-baseline results as unresolved. Correct the cause or supply the missing evidence and repeat against current candidates. A successful preflight covers only the checks actually returned for that overlay and reader observation.

Preflight does not validate language-mirror presence, Markdown links or layer structure, prove semantic equivalence, execute repository code, authorize applying files, or replace current-state Verification and Acceptance. Run the target repository's own required documentation, language and other checks through actually available authorized capabilities. This project's author-document validators belong to its private development workflow, not the installed product; using the product on another repository never requires access to that private directory. Complete applicable authoritative target checks after applying changes.

## Codex CLI / ChatGPT Desktop optimizations

When exposed and authorized, call `validate_decoupling_compliance` with `payload.request.policy_scope: generic_project` and the exact candidate paths, operations, content and baselines. This is the product's sole supported policy scope. The trusted root, enabled service scope and read-only baseline reader come from operator startup configuration; neither the request nor current directory chooses them. Inspect the returned `policy_scope` and `policy_version: 2`. The tool does not write files, run subprocesses, execute candidate code or call an API.

For every task, including Skill maintenance, inspect only the generic path/baseline findings actually returned and review `not_evaluated`. Do not expect this tool to perform bilingual, Markdown, layer or target-project semantic checks. Resolve `unknown`, `fail`, truncation or budget findings before proceeding. A passing result is not authorization; obtain write authority independently, recheck current state before applying, and retain the target repository's separate required checks.

## Claude Code CLI / Claude Desktop optimizations

This repository's MCP Server supports local Codex CLI only; generic Claude MCP support does not authorize direct use of this server. No Claude-specific direct-tool optimization is maintained here. Follow general rules using only capabilities actually exposed and authorized in the current Session; if a trusted reader is unavailable, mark disk-dependent checks unknown and use the applicable established verification route.

## Related concepts

- [Session Role Ownership](../session-runtime/session-role-ownership.md) — owns trusted identity and per-call guards.
- [Workflow Routing Advice](workflow-routing-advice.md) — owns optional stage suggestions.
- [Output Materialization](output-materialization.md) — owns controlled output preparation and application.
