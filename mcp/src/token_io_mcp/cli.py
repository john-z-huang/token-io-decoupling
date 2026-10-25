"""Production command line entry point; no identity or state-path options exist."""

from __future__ import annotations

import sys

from token_io_mcp.server import create_server


def main() -> int:
    if len(sys.argv) != 1:
        print("token-io-mcp accepts no command-line arguments", file=sys.stderr)
        return 2
    create_server().run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
