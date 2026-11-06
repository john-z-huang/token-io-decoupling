#!/bin/bash
set -euo pipefail

entry_path=${BASH_SOURCE[0]}
[[ "$entry_path" == /* ]] || entry_path="$PWD/$entry_path"
symlink_hops=0
while :; do
  entry_dir=$(CDPATH= cd -P -- "${entry_path%/*}" && pwd -P)
  entry_path="$entry_dir/${entry_path##*/}"
  [[ -L "$entry_path" ]] || break
  if ((symlink_hops >= 40)); then
    printf '%s\n' 'installer symlink chain exceeded 40 links' >&2
    exit 1
  fi
  if [[ -x /usr/bin/readlink ]]; then
    link_target=$(/usr/bin/readlink "$entry_path")
  else
    link_target=$(/bin/readlink "$entry_path")
  fi
  if [[ "$link_target" == /* ]]; then
    entry_path=$link_target
  else
    entry_path="$entry_dir/$link_target"
  fi
  symlink_hops=$((symlink_hops + 1))
done
repo_root=$(CDPATH= cd -P -- "$entry_dir/.." && pwd -P)
exec /bin/bash "$repo_root/.agents/skills/token-io-decoupling-dev/scripts/install-codex-mcp.sh" "$@"
