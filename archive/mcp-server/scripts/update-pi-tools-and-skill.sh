#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf '用法：%s [--name SKILL_NAME]\n' "${0##*/}"
}

skill_name="token-io-decoupling-skill"
case "$#" in
  0) ;;
  1)
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
      usage
      exit 0
    fi
    usage >&2
    exit 2
    ;;
  2)
    if [[ "$1" != "--name" ]]; then
      usage >&2
      exit 2
    fi
    skill_name="$2"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

if [[ ! "$skill_name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ || "$skill_name" == "token-io-decoupling" ]]; then
  printf '%s\n' '请选择合法的小写 Skill 名称，旧名称 token-io-decoupling 受保护。' >&2
  exit 2
fi
if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' '找不到 uv，请先安装 uv。' >&2
  exit 1
fi

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_path="${HOME:?}/.pi/agent/skills/$skill_name"
cd "$repo"

printf '%s\n' '从 rules 构建 skill'
uv run --locked --script scripts/compile-reference-dsl.py

/bin/bash scripts/install-pi-mcp.sh

tool_bin="$(uv tool dir --bin)"
action=install
if [[ -e "$skill_path" || -L "$skill_path" ]]; then
  action=update
fi
printf '同步本地 Skill（%s）\n' "$action"
"$tool_bin/token-io-decoupling-tools" skills "$action" --name "$skill_name"
