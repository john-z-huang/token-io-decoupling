#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT
cd "$repo/mcp"
printf '%s\n' '构建 MCP workspace wheel'
uv build --all-packages --wheel --out-dir "$out"
printf '%s\n' '用 uv tool 安装或更新 MCP 工具'
uv tool install --reinstall --find-links "$out" "$out"/token_io_decoupling-*.whl
