# Product and Development Responsibility Map

[English](responsibility-migration.md) | [简体中文](responsibility-migration_zh_cn.md)

This reference records current product ownership and planned development migrations. It does not claim that future stages have shipped. Use the [development Skill](../SKILL.md) for the entry point; its MCP server currently exposes discovery only.

## Ownership and staged path inventory

| Concern and current path | Ownership and destination | Stage and boundary |
| --- | --- | --- |
| Canonical policy content in product Skill and reference Markdown | Remains product-owned source of policy | Source text stays authoritative; development tooling may validate or derive artifacts but cannot silently replace policy. |
| Mapping registry: `mcp/rule-registry.json`, `mcp/rule-context-index.json`, and `mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/owner_paths.py` | Mapping ownership moves into `mcp-project-dev`; product runtime consumes generated resources | #193 defines the compiler contract and mapping model. #196 changes runtime packaging to consume derived resources. Stable generic IDs and runtime contracts remain product-owned. |
| Runtime resource build hooks: `mcp/packages/token_io_decoupling_core/hatch_build.py` and `mcp/hatch_build.py` | Product packaging remains responsible for shipping runtime resources; development project owns compiler outputs | #196 integrates generated resources and removes development-only attachments from the product package. |
| Project-specific checks: `mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/compliance_preflight.py` and `mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/compliance_core.py` | Bilingual, layer-boundary, structure, and project-specific compliance checks move to `mcp-project-dev` | #194 migrates the project-specific checks. Generic `generic_project` safety path and baseline enforcement stay product-owned and continue to guard runtime operations. |
| Output materialization support: `mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/output_materialization.py`, `mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/materialization_templates.py`, and `mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/materialization_models.py` | Project-side Skill-instruction maintenance moves to development tooling; runtime Worker authorization and application remain product-owned | #194 separates the development Skill maintenance branch from the product Worker path. A development write does not enlarge authority; reuse product safety foundations rather than duplicating or weakening their policies. |
| Worker implementation: `mcp/packages/token_io_decoupling_worker/src/token_io_decoupling_worker/tools.py` | Product Worker `code_configuration` retains trusted-root and exact-path checks, baseline/overlay validation, assignment binding, independent operator grant and artifact-hash checks, and prepare → inspect → fresh preflight → exact apply → receipt/readback | Stays product-owned. Moving Skill-instruction maintenance does not move or bypass this runtime operation. |
| Existing project validators and helpers listed below | Move to `.agents/skills/token-io-decoupling-dev/scripts/` | #195 migrates the script entry points and updates their calls. None move in #192. |
| CI, tests, `AGENTS.md`, `MULTI_LINGUAL.md`, root locating, `.agents` discovery, and snapshot calls | Migrate or redirect development-only checks to `mcp-project-dev` while keeping product runtime contracts and user-facing instructions in product ownership | #195. Preserve product user-side installation/configuration scripts, including `scripts/install-codex-mcp.sh` and `scripts/configure-codex-mcp-env.py`. |
| Product package resource attachments | Product package contains only runtime-consumed resources | #196 removes development-only attachments after the new runtime resource path is verified. |
| Isolated package and runtime regression | Both projects retain their own dependency boundary and tests | #197 verifies standalone installation, no reverse product dependency, and regression behavior across the split. |

The 11 existing validators and helpers planned for the development Skill scripts directory are:

- `check-multilingual-docs.py`
- `check-doc-layer-links.py`
- `check-layer-01-sections.py`
- `check-layer-02-04-provider-neutrality.py`
- `check-layer-04-workflow-maps.py`
- `check-workflow-checkpoints.py`
- `check-context-exchange.py`
- `check_coding_document_migration.py`
- `markdown_discovery.py`
- `workflow_module_contracts.py`
- `compliance_core_loader.py`

## One-way dependency and authority boundary

The development project is a standalone MCP server for local Codex CLI. Its current skeleton has no product-package dependency and reports compiler, project-compliance, and materialization capabilities as unavailable. In a later stage, development code may use a narrow product-core dependency when needed; product runtime packages must never import or depend on `mcp-project-dev`.

Canonical policy, stable IDs, runtime state, permissions, and generic safety checks remain product-owned. Development compiler/check/Skill-maintenance writes cannot create product permissions or weaken runtime guards. Preserve frozen migration sources and historical baselines through every stage. Installation and Codex configuration remain product/user-side work.

## Current #192 boundary

#192 adds the independent project, its truthful read-only `dev_capabilities` discovery tool, and this responsibility map. It does not implement the compiler or compliance checks, move scripts or CI, switch runtime loaders, move the Worker `code_configuration` path, or claim future development writes are available.
