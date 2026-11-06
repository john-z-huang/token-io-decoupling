#!/bin/bash
# Install or refresh both local MCP executables and their management CLI, then register them.

set -euo pipefail

usage() {
  printf '%s\n' \
    'Usage: bash install-codex-mcp.sh [options]' \
    '' \
    "Install or update this repository's Token I/O MCP commands and configure Codex." \
    '' \
    'Options:' \
    '  --python VERSION     Python version for uv (default: 3.14)' \
    '  --dry-run            Print the ordered plan without checking prerequisites' \
    '  -h, --help           Show this help'
}

fail() {
  printf 'install-codex-mcp: %s\n' "$1" >&2
}

resolve_repo_root() {
  local script_path script_dir script_name link_target readlink_path symlink_hops
  script_path=${BASH_SOURCE[0]}
  if [[ "$script_path" != /* ]]; then
    script_path="$PWD/$script_path"
  fi
  symlink_hops=0
  while :; do
    script_dir=${script_path%/*}
    script_name=${script_path##*/}
    [[ -n "$script_dir" ]] || script_dir='/'
    if ! script_dir=$(CDPATH= cd -P -- "$script_dir" && pwd -P); then
      fail 'could not resolve the installer directory'
      return 1
    fi
    script_path="$script_dir/$script_name"
    [[ -L "$script_path" ]] || break
    if ((symlink_hops >= 40)); then
      fail 'installer symlink chain exceeded 40 links'
      return 1
    fi
    if [[ -x /usr/bin/readlink ]]; then
      readlink_path=/usr/bin/readlink
    elif [[ -x /bin/readlink ]]; then
      readlink_path=/bin/readlink
    else
      fail 'readlink is required to resolve a symlinked installer'
      return 1
    fi
    if ! link_target=$("$readlink_path" "$script_path"); then
      fail 'could not resolve the installer symlink'
      return 1
    fi
    if [[ "$link_target" == /* ]]; then
      script_path=$link_target
    else
      script_path="$script_dir/$link_target"
    fi
    symlink_hops=$((symlink_hops + 1))
  done
  if ! CDPATH= cd -P -- "$script_dir/../../../.."; then
    fail 'could not resolve the repository directory'
    return 1
  fi
  pwd -P
}

dry_run=0
python_version='3.14'
python_seen=0

while (($# > 0)); do
  case "$1" in
    -h|--help)
      if (($# != 1)); then
        fail '--help does not accept additional arguments'
        exit 2
      fi
      usage
      exit 0
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --python)
      if (($# < 2)) || [[ -z "$2" || "$2" == -* ]]; then
        fail '--python requires a non-empty version that does not start with -'
        exit 2
      fi
      if ((python_seen != 0)); then
        fail '--python may be specified only once'
        exit 2
      fi
      python_version="$2"
      python_seen=1
      shift 2
      ;;
    *)
      fail "unknown argument: $1"
      exit 2
      ;;
  esac
done


setup_args=(setup codex)
if ((dry_run != 0)); then
  setup_args+=(--dry-run)
fi

if repo_root=$(resolve_repo_root); then
  :
else
  exit 1
fi
source_root="$repo_root/mcp"

if ((dry_run != 0)); then
  printf '%s\n' 'Dry run: no installation/setup commands or Codex configuration reads/writes were run.'
  printf '1. Install/update the admin, workflow, and tools commands: uv tool install --force --reinstall --managed-python --python %q %q\n' \
    "$python_version" "$source_root"
  printf '%s\n' '2. Resolve tool bin directory: uv tool dir --bin'
  printf '%s\n' '   Workflow MCP executable: <uv-tool-bin>/token-io-decoupling-workflow'
  printf '%s\n' '   Tools MCP executable: <uv-tool-bin>/token-io-decoupling-tools'
  printf '3. Configure both MCP registrations through <uv-tool-bin>/token-io-decoupling'
  for argument in "${setup_args[@]}"; do
    printf ' %q' "$argument"
  done
  printf '\n%s\n' '4. Reload affected MCP servers in Codex.'
  exit 0
fi

if ! uv_path=$(type -P uv); then
  fail 'uv was not found on PATH; no installation was attempted'
  exit 127
fi
if ! command -v codex >/dev/null 2>&1; then
  fail 'Codex CLI was not found on PATH; no installation was attempted'
  exit 127
fi

if ! python3_path=$(type -P python3); then
  fail 'Python 3.11+ is required to verify compiled resource freshness; no installation was attempted'
  exit 127
fi
compiler_entry="$repo_root/instruction-compiler/compile.py"
if [[ ! -f "$compiler_entry" ]]; then
  fail 'the private compiler entrypoint is missing; no installation was attempted'
  exit 1
fi
if "$python3_path" "$compiler_entry" compile --check; then
  :
else
  exit_code=$?
  fail "compiled resource freshness check failed (exit $exit_code); no installation was attempted"
  exit "$exit_code"
fi

if "$uv_path" tool install --force --reinstall --managed-python --python "$python_version" "$source_root"; then
  :
else
  exit_code=$?
  fail "uv tool installation/update failed (exit $exit_code)"
  exit "$exit_code"
fi

if bin_dir=$("$uv_path" tool dir --bin); then
  :
else
  exit_code=$?
  fail "installation succeeded, but uv could not locate its tool bin directory (exit $exit_code); Codex setup was not run"
  exit "$exit_code"
fi
if [[ -z "$bin_dir" ]]; then
  fail 'installation succeeded, but uv returned an empty tool bin directory; Codex setup was not run'
  exit 1
fi
for command_name in \
  token-io-decoupling \
  token-io-decoupling-workflow \
  token-io-decoupling-tools; do
  executable="$bin_dir/$command_name"
  if [[ ! -f "$executable" || ! -x "$executable" ]]; then
    printf 'install-codex-mcp: installation succeeded, but the installed command is missing or not executable at %q; Codex setup was not run\n' \
      "$executable" >&2
    exit 1
  fi
done
launcher="$bin_dir/token-io-decoupling"

if "$launcher" "${setup_args[@]}"; then
  printf '%s\n' 'Codex MCP setup completed. Reload the affected MCP servers in Codex to use the updated registrations.'
else
  exit_code=$?
  fail "tool installation succeeded, but Codex setup failed (exit $exit_code); the installed tool remains available, and no automatic rollback was attempted"
  exit "$exit_code"
fi
