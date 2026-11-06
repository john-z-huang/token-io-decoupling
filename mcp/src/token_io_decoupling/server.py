"""Lazy compatibility factories; each implementation is owned by its distribution."""

from typing import Any


def create_workflow_server(*args: Any, **kwargs: Any) -> Any:
    from token_io_decoupling_workflow.server import create_workflow_server as create

    return create(*args, **kwargs)


def create_tools_server(*args: Any, **kwargs: Any) -> Any:
    from token_io_decoupling_tools.server import create_tools_server as create

    return create(*args, **kwargs)
