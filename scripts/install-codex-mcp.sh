#!/bin/bash
# Install or refresh the local Token I/O MCP tool, then register it with Codex.

set -euo pipefail

usage() {
  printf '%s\n' \
    'Usage: bash install-codex-mcp.sh [options]' \
    '' \
    "Install or update this repository's Token I/O MCP tool and configure Codex." \
    '' \
    'Options:' \
    '  --profile NAME       Configure one profile: workflow, root, worker, or share' \
    '  --all                Configure all profiles (the default)' \
    '  --replace            Replace conflicting existing registrations' \
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
  if ! CDPATH= cd -P -- "$script_dir/.."; then
    fail 'could not resolve the repository directory'
    return 1
  fi
  pwd -P
}

profile=''
replace=0
dry_run=0
python_version='3.14'
python_seen=0
selection_seen=0

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
    --profile)
      if (($# < 2)) || [[ -z "$2" || "$2" == --* ]]; then
        fail '--profile requires a non-empty profile name'
        exit 2
      fi
      if ((selection_seen != 0)); then
        fail '--profile cannot be combined with --all or another profile'
        exit 2
      fi
      case "$2" in
        workflow|root|worker|share) profile="$2" ;;
        *) fail "invalid profile: $2"; exit 2 ;;
      esac
      selection_seen=1
      shift 2
      ;;
    --all)
      if ((selection_seen != 0)); then
        fail '--all cannot be combined with --profile or another selection'
        exit 2
      fi
      selection_seen=1
      shift
      ;;
    --replace)
      replace=1
      shift
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
if [[ -n "$profile" ]]; then
  setup_args+=(--profile "$profile")
else
  setup_args+=(--all)
fi
if ((replace != 0)); then
  setup_args+=(--replace)
fi

if repo_root=$(resolve_repo_root); then
  :
else
  exit 1
fi
source_root="$repo_root/mcp"

if ((dry_run != 0)); then
  printf '%s\n' 'Dry run: no installation/setup commands or Codex configuration reads/writes were run.'
  printf '1. Install/update: uv tool install --force --reinstall --managed-python --python %q %q\n' \
    "$python_version" "$source_root"
  printf '%s\n' '2. Resolve tool bin directory: uv tool dir --bin'
  printf '3. Configure: <uv-tool-bin>/token-io-decoupling'
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
launcher="$bin_dir/token-io-decoupling"
if [[ ! -f "$launcher" || ! -x "$launcher" ]]; then
  printf 'install-codex-mcp: installation succeeded, but the installed command is missing or not executable at %q; Codex setup was not run\n' \
    "$launcher" >&2
  exit 1
fi

if "$launcher" "${setup_args[@]}"; then
  printf '%s\n' 'Codex MCP setup completed. Reload the affected MCP servers in Codex to use the updated registrations.'
else
  exit_code=$?
  fail "tool installation succeeded, but Codex setup failed (exit $exit_code); the installed tool remains available, and no automatic rollback was attempted"
  exit "$exit_code"
fi
