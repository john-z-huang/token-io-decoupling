"""Production stdio entry point with an optional authenticated host channel."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from token_io_mcp.binding import BindingError
from token_io_mcp.host_binding import HostChannelBindingProvider
from token_io_mcp.server import create_server


def _trusted_state_root() -> Path:
    """Resolve canonical state under the CLI process's OS account, never caller HOME."""
    try:
        import pwd

        effective_uid = getattr(os, "geteuid", None)
        if effective_uid is None:
            raise ValueError("effective UID is unavailable")
        home = Path(pwd.getpwuid(effective_uid()).pw_dir)
        if not home.is_absolute():
            raise ValueError("OS account home is not absolute")
        return home / ".local" / "state" / "token-io-decoupling"
    except (AttributeError, ImportError, KeyError, OSError, TypeError, ValueError) as exc:
        raise BindingError("trusted OS account state location is unavailable") from exc


def main() -> int:
    parser = argparse.ArgumentParser(prog="token-io-mcp")
    parser.add_argument("--host-fd", type=int, metavar="INTEGER")
    parser.add_argument("--codex-context", action="store_true")
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    if args.codex_context and args.host_fd is None:
        print("token-io-mcp: --codex-context requires --host-fd", file=sys.stderr)
        return 2
    provider = None
    if args.host_fd is not None:
        try:
            provider = HostChannelBindingProvider.from_fd(args.host_fd)
        except (BindingError, OSError, ValueError):
            print("token-io-mcp: authenticated host channel unavailable", file=sys.stderr)
            return 2
    try:
        if provider is None:
            server = create_server()
        else:
            server = create_server(
                provider,
                require_bound=True,
                require_codex_context=args.codex_context,
                state_root=_trusted_state_root(),
            )
        server.run(transport="stdio")
    except Exception:
        print("token-io-mcp: server startup failed", file=sys.stderr)
        return 2
    finally:
        if provider is not None:
            provider.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
