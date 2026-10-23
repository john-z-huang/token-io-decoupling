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

## Build and rule resources

From `mcp/`, build a wheel and source distribution into a temporary output directory:

```sh
uv build --managed-python . --out-dir /tmp/token-io-mcp-dist
```

The build hook generates read-only rule resources from the registry and the referenced Markdown owners. These generated excerpts are package resources, not a second manually maintained policy source. The source distribution includes its own rule sources so a later wheel build does not borrow an unrelated sibling checkout. The build-artifact test exercises a detached source distribution and checks both languages and migration resources.

When testing rule edits in a checkout, construct `RuleLoader` with the explicit repository root. A default loader reads the installed package resources. Rebuild and reinstall the distribution to update those resources; editing a different checkout does not update an installed wheel.

Migration modules are versioned package resources. Preserve released files and add a new migration for schema changes. Exercise upgrade and recovery tests as well as a fresh database; initialization alone does not verify historical compatibility.
