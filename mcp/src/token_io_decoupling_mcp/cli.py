"""Compatibility entry point for the former module CLI."""

from token_io_decoupling.cli import legacy_main as main

if __name__ == "__main__":
    raise SystemExit(main())
