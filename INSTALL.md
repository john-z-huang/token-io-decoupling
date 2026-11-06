# Installation and updates

[English](INSTALL.md) | [简体中文](INSTALL_zh_cn.md)

This guide owns end-user building, installation, updates and installation recovery. Development procedures belong to the [private development Skill](.agents/skills/token-io-decoupling-dev/SKILL.md).

## Prerequisites

For the source-checkout commands below, make `uv`, `git`, `python3` (Python 3.11 or later), Bash 3.2 or later, and local `codex` CLI available on `PATH`. Use a complete checkout containing the approved generated resources. uv selects managed Python 3.14 for the installed tool; the helper's `--python VERSION` changes that choice. The freshness check uses the existing `python3` command.

Initial installation may need network access to obtain Python, build dependencies and the pinned `dev-workflow-standards` dependency. Local rule lookup does not need an OpenAI key. Do not place the source checkout inside a Skill installation directory.

## First installation

Run from the checkout root:

```sh
bash scripts/install-codex-mcp.sh
"$(uv tool dir --bin)/token-io-decoupling" skills install
```

The helper verifies resource freshness, asks uv to build and install the root package and its three local workspace dependencies, then registers and inspects `token-io-decoupling-workflow` and `token-io-decoupling-tools`. It does not install the Skill. The second command validates the packaged Skill against installed core resources and publishes the managed snapshot to `~/.agents/skills/token-io-decoupling-skill`.

Invoke management commands through `uv tool dir --bin` as shown; this also works when uv's bin directory is not on `PATH`. No virtual-environment activation is needed.

## Update

After obtaining the desired checkout revision, run from its root:

```sh
bash scripts/install-codex-mcp.sh
"$(uv tool dir --bin)/token-io-decoupling" skills update
```

The helper reinstalls the tool and workspace dependencies, refreshes the approved compiled resources, and checks the two current MCP registrations. Then `skills update` replaces the managed snapshot. Run both commands after a product update. A successful update preserves unrelated Codex configuration and existing target settings that setup supports; it does not remove other registrations. An existing `enabled=false` setting also remains disabled.

The default Skill name is `token-io-decoupling-skill`. If you selected another name, use the same `--name my-coding-skill` with both Skill commands. An existing Skill requires `update`; a missing Skill requires `install`.

## Build distributable files only

From the checkout root:

```sh
uv build --project mcp --all-packages --out-dir mcp/dist
```

This produces four wheels and four sdists in `mcp/dist/`. Building does not install or register anything. It packages approved generated resources and never compiles author instructions. If author instructions changed, the maintainer must regenerate and validate resources using the private development workflow before delivering the build.

## Install a wheel set without the checkout

Put the four wheels from one build in a `dist/` directory containing only that wheel version. From its parent directory, run:

```sh
uv tool install --force --reinstall --managed-python --python 3.14 \
  --with dist/token_io_decoupling_core-*.whl \
  --with dist/token_io_decoupling_transport-*.whl \
  --with dist/token_io_decoupling_workflow-*.whl \
  dist/token_io_decoupling-*.whl
"$(uv tool dir --bin)/token-io-decoupling" setup codex
"$(uv tool dir --bin)/token-io-decoupling" skills install
```

For an existing managed Skill, use `skills update` on the last line. Supplying all four exact wheel matches prevents a same-version cached dependency from replacing a member of the intended build. Do not mix wheel sets. The installed core and Skill bundle must have matching build identities and file inventories; the Skill installer rejects a mismatch.

Document-only users of other Code Agents may omit `setup codex`; that does not make those Agents direct MCP clients. The Skill command reads installed package resources and does not need the checkout or compiler.

## Verification and activation

Successful setup has checked both MCP inventories: 17 workflow tools and 34 tools in the tools server. Successful Skill installation/update has checked the core/bundle batch and written `manifest.json` and `.token-io-skill.json` into the Skill directory; both record its `build_id`. The managed file hashes also reflect the selected installation name. Existing disabled entries must be enabled through your normal Codex configuration before use.

Reload both MCP servers and start a new Agent session after installation or update. Existing connections and already-loaded Skill instructions do not hot-reload. Load your selected Skill name (default: `token-io-decoupling-skill`) in the new session, then follow the Coding entry in its installed `~/.agents/skills/<selected-name>/SKILL.md`. This is necessary even when the package version number has not changed.

Optional API-backed operations require nonblank `OPENAI_API_KEY` and `OPENAI_BASE_URL` in the environment used to launch Codex. Setup forwards names, not secret values; it does not create credentials or supply an endpoint. MCP-issued OpenAI requests use `gpt-6-luna`. Configure environment values through your existing local environment mechanism, then restart the servers. Installation, discovery and static rule queries do not require an API request.

## Failure and recovery

| Result | Action |
|---|---|
| Freshness or build fails | Stop. Use approved resources or have the maintainer regenerate them; no source-document fallback is installed. |
| Tool installation succeeds but setup fails | The installed tool remains available. Resolve the reported configuration problem, then run `"$(uv tool dir --bin)/token-io-decoupling" setup codex`. |
| Skill is missing or already exists | Select the matching `install` or `update` command. Neither command silently changes the other operation. |
| Skill has local edits, unknown ownership, symlinks or a concurrent update | Preserve the current directory and resolve the reported condition. Do not edit the marker to bypass checks or force-copy files over it. |
| A mixed-batch bundle is rejected | Reinstall all four wheels from the intended build, then rerun the Skill command. |

The legacy `~/.agents/skills/token-io-decoupling` checkout is protected; these commands do not migrate, overwrite or delete it. Keep source checkouts outside Skill discovery directories. Custom names do not waive ownership or local-change protection.

For these installation steps, preview with `setup codex --dry-run` or `bash scripts/install-codex-mcp.sh --dry-run`. The helper preview prints its plan without installation or configuration reads; setup preview reads and preflights the two target sections without writing or starting servers. `skills install` and `skills update` have no `--dry-run` option.

## Related documents

- [Product overview](README.md).
- [Project development](.agents/skills/token-io-decoupling-dev/SKILL.md).
