# MCP development guide

[English](DEVELOPMENT.md) | [简体中文](DEVELOPMENT_zh_cn.md)

This guide owns local development and package checks for the optional Python subsystem. Workflow policies remain in the [Skill entry](../SKILL.md) and its linked owners; the [architecture contract](../ENHANCED_ARCHITECTURE.md) describes component boundaries.

## Environment and checks

Run these commands from `mcp/`. The project declares Python 3.11 or newer and commits its dependency lockfile. Use a uv-managed interpreter and the locked development dependencies:

```sh
uv sync --managed-python --locked --group dev
uv run --managed-python --locked -- pytest
uv run --managed-python --locked -- ruff check .
uv run --managed-python --locked -- ruff format --check .
uv run --managed-python --locked -- ty check
```

Set `UV_PROJECT_ENVIRONMENT` to an absolute temporary directory before these commands when the virtual environment must stay outside the checkout. Tests use temporary databases and mocked bindings. They do not establish operating-system isolation or actual host-client compatibility. No API key or real API request is needed for the test suite.

Repository documentation checks are separate. Run the checks required by [repository instructions](../AGENTS.md) from the repository root, including the existing workflow-map and context-exchange regression tests.

## Stdio server and trusted embeddings

The `token-io-mcp` entry point starts a stdio server for an MCP client and accepts no command-line arguments. From this directory, its development launch command is:

```sh
uv run --managed-python --locked -- token-io-mcp
```

The production CLI has no trusted host binding and exposes only `workflow_capabilities`, `rules_get_context`, and `database_schema_status`. Its schema diagnostic returns unavailable without inspecting or creating state paths. It remains in Native mode; an environment variable, client name, requested role, or filesystem path cannot supply identity or permission.

An embedding can supply a verified `BindingProvider` to `token_io_mcp.server.create_server`. A fully capable Root binding exposes 15 tools, a Worker binding 10, and an unbound server 3. Protected calls recheck the binding and required guards every time. The current package has no verified Codex or ChatGPT Desktop host adapter; the test providers and subprocess harnesses do not establish one. Do not copy a synthetic provider into production or infer operating-system isolation from these tests.

The protocol target is `2026-07-28`. Tests use SDK automatic negotiation and real subprocess stdio calls, including typed enum/UTC values and role rejection. This verifies the package protocol connection; actual host-client compatibility remains a separate check.

## Required configuration for real API requests

Root and every delegated Agent must follow this constraint in both project functionality and test/smoke code: immediately before any real API request, read both `OPENAI_API_KEY` and `OPENAI_BASE_URL` from the local process environment. Both values must be present and nonempty; whitespace-only values are invalid too. If either is missing or invalid, do not create the SDK client or send a real request; return to the documented fallback instead.

Do not substitute a hardcoded key or endpoint, caller-supplied replacement, or the SDK's default endpoint. Read the two local values at invocation time and pass them explicitly to the SDK. Never print or persist their values. Synthetic configuration is permitted only for mocks that send no network requests.

The API remains disabled by default. Real requests additionally require explicit enablement and authorization for outbound data; this document alone grants neither. The ordinary test suite uses mocks, while a real smoke test requires a separate explicit opt-in and must obey the same two-variable requirement.

An authorized embedding enables advice with `DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True)` through the factory's `decisions_config` argument. Optional `semantic_input` on the two evaluation tools is limited to task intent, output class, Contract change, verification impact, and Control. The response keeps the Core result separate from advice. With no semantic input, the original Core response is retained. Advice never selects or confirms a Gate branch; stale, invalid, refused, unavailable, or replayed advice returns to document judgment.

After explicit authorization for a real synthetic request, run this separately from ordinary tests, from `mcp/`, with both local environment variables already configured:

```sh
TOKEN_IO_RUN_REAL_DECISIONS=1 uv run --managed-python --locked -- python tests/decisions_real_smoke.py
```

Without the opt-in, the script makes no request. It uses a temporary Root database and a synthetic trusted provider, calls `DecisionsAdvisor` directly, and reports only safe status, reason, classification metadata, choice, and usage. It does not prove a real host binding or a real API call through the MCP handler. MCP handler/protocol tests instead use mocked API transport. The advisor reads both required local variables at invocation time; neither the script nor the project supplies replacement credentials or a default endpoint.

## Build and rule resources

From `mcp/`, build a wheel and source distribution into a temporary output directory:

```sh
uv build --managed-python . --out-dir /tmp/token-io-mcp-dist
```

The build hook generates read-only rule resources from the registry and the referenced Markdown owners. These generated excerpts are package resources, not a second manually maintained policy source. The source distribution includes its own rule sources so a later wheel build does not borrow an unrelated sibling checkout. The build-artifact test exercises a detached source distribution and checks both languages and migration resources.

When testing rule edits in a checkout, construct `RuleLoader` with the explicit repository root. A default loader reads the installed package resources. Rebuild and reinstall the distribution to update those resources; editing a different checkout does not update an installed wheel.

Migration modules are versioned package resources. Preserve released files and add a new migration for schema changes. Exercise upgrade and recovery tests as well as a fresh database; initialization alone does not verify historical compatibility.

## CI and isolated installation

The [MCP package workflow](../.github/workflows/mcp.yml) runs the complete mocked test suite, Ruff lint/format checks, and ty with locked dependencies on managed Python 3.11 and 3.14. A separate Python 3.14 job builds the wheel and source distribution, installs the wheel into temporary uv tool directories, and calls the installed executable through the SDK from outside the checkout. These jobs do not enable Decisions or need API credentials.

For an isolated local installation, first export the lockfile with `uv export --locked --all-groups --no-emit-project --no-hashes --no-header --no-annotate` and pass that output to `uv build --build-constraints`. Export runtime constraints separately with `--no-dev` instead of `--all-groups`, then pass them to `uv tool install --constraints` when installing the wheel. Use `--managed-python --python 3.14` for the build and installation. Set command-local `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` to absolute temporary directories and invoke the resulting `token-io-mcp` by its absolute path. The workflow contains the complete commands; no shell configuration change is needed.

Run `tests/installed_stdio_smoke.py --cli /absolute/temporary/bin/token-io-mcp` with the locked project interpreter to check that installation. It launches the service outside the checkout with an empty `PYTHONPATH`, checks automatic protocol negotiation, the three public Native tools, both packaged rule languages, and unavailable schema diagnostics. This is package/stdio evidence, not proof of a Codex or ChatGPT Desktop binding. Local execution does not establish that GitHub Actions has run.

The [documentation workflow](../.github/workflows/multilingual-docs.yml) retains the repository validators and workflow-map/context regressions and adds scanner regressions. Shared discovery prunes generated resources, virtual environments, caches, vendor directories, and symlinks before traversal; authored MCP documentation remains checked for language mirrors and valid links.

## Native recovery development checks

The [Native Authority Transfer](../references/coding/layer-01-fundamental-concepts/native-authority-transfer.md) and [Native Reconciliation](../references/coding/layer-01-fundamental-concepts/native-reconciliation.md) owners define the workflow boundaries. The checks below verify the implemented service cases; they do not establish a full export or host-stop capability.

Use temporary databases and synthetic bindings for recovery development. The focused state-service cases exercise explicit full-set adjudication, preserved comparison history, recovery Revision/Epoch freshness, outstanding evidence requests, and blocked dispatch side effects. They also cover exact confirmation without hiding older conflicts, fresh Control before the first post-recovery Slice, effect-free confirmed dispatch replay, and bounded readback of oversized legacy snapshots. Migration tests distinguish proven legacy confirmation pairs from malformed or nonadjacent records. Run them from `mcp/` before the complete suite:

```sh
uv run --managed-python --locked -- pytest tests/test_state_service.py -k native
uv run --managed-python --locked -- pytest tests/test_migrations.py
```

These checks do not prove a host can stop a Worker. The supported material-recovery path has existing Root control state and no bound Worker, active Worker Slice, or pending dispatch. It adjudicates the Contract source and semantic-reference pair; it does not reconstruct missing identity, dispatch, lifecycle, or acceptance history. Keep unsupported states blocked and preserve their records. Evidence references and request hashes provide review pointers and integrity binding; neither authenticates a caller or independently establishes freshness or quiescence.
