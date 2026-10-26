"""Compatibility imports for the former server module."""

from token_io_decoupling_core.profiles import PROFILE_ROLES, PROFILE_TOOLS

from token_io_decoupling.server import create_server

__all__ = ["create_server", "PROFILE_ROLES", "PROFILE_TOOLS"]
