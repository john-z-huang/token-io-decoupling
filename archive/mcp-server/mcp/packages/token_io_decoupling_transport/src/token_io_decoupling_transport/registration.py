"""One registration mechanism for fixed-manifest flat and payload tools."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import wraps
from typing import Annotated, Any, get_type_hints

from mcp.server import MCPServer
from mcp.server.mcpserver import Context as MCPContext
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, ValidationError, WithJsonSchema
from token_io_decoupling_core.binding import BindingError, BindingProvider
from token_io_decoupling_core.codex_context import CodexCallerBoundProvider
from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS

from token_io_decoupling_transport.payloads import inline_schema


@dataclass(frozen=True)
class ToolDefinition:
    """Explicit public contract and callback; payload tools retain their nested wire shape."""

    name: str
    callback: Callable[..., Any]
    description: str
    annotations: ToolAnnotations | None = None
    parameter_descriptions: Mapping[str, str] | None = None
    payload_type: type[BaseModel] | None = None
    enhanced: bool = False
    role: str | None = None
    structured_output: bool | None = None


class ToolRegistrar:
    """Apply manifest checks and preserve each tool's original invocation semantics."""

    def __init__(
        self,
        server: MCPServer[Any],
        *,
        provider: BindingProvider,
        state_provider: BindingProvider,
        allowed_tools: frozenset[str],
        require_codex_context: bool,
        bound_role_for: Callable[[BindingProvider], str | None],
    ) -> None:
        if not allowed_tools <= TOOLS_SERVER_TOOLS:
            raise ValueError("unknown tools in allowed manifest")
        self.server = server
        self.provider = provider
        self.state_provider = state_provider
        self.allowed_tools = allowed_tools
        self.require_codex_context = require_codex_context
        self._bound_role_for = bound_role_for
        self._registered: set[str] = set()

    def validate_definitions(self, definitions: Sequence[ToolDefinition]) -> None:
        names = [definition.name for definition in definitions]
        if len(names) != len(set(names)) or set(names) != self.allowed_tools:
            raise ValueError("tool definitions differ from allowed manifest or contain duplicates")
        for definition in definitions:
            self._validate_definition(definition)

    @staticmethod
    def _validate_definition(definition: ToolDefinition) -> None:
        if definition.name not in TOOLS_SERVER_TOOLS:
            raise ValueError("unknown tool definition")
        if definition.parameter_descriptions is not None:
            parameters = (
                {"payload"}
                if definition.payload_type is not None
                else set(inspect.signature(definition.callback, follow_wrapped=False).parameters)
            )
            if set(definition.parameter_descriptions) != parameters:
                raise ValueError(
                    f"MCP parameter descriptions do not match {definition.name} signature"
                )
        if definition.payload_type is None and (definition.enhanced or definition.role):
            raise ValueError("flat tools cannot introduce payload role/context guards")

    def check_operation_role(
        self, expected: str | None, callback: Callable[[], Any], *, enforce: bool = True
    ) -> Any:
        if not enforce or expected is None:
            return callback()
        actual = self._bound_role_for(self.provider)
        if actual is None:
            raise BindingError("session role is unavailable")
        if actual != expected:
            raise BindingError("session role does not match this operation")
        return callback()

    def with_codex_context(self, context: MCPContext | None, callback: Callable[[], Any]) -> Any:
        if not self.require_codex_context:
            return callback()
        try:
            meta = context.request_context.meta if context is not None else None
            if not isinstance(self.state_provider, CodexCallerBoundProvider):
                raise BindingError("Codex caller provider is unavailable")
            with self.state_provider.request_scope(meta):
                return callback()
        except (BindingError, ValueError) as exc:
            raise ToolError("Codex request context is unavailable or mismatched") from exc

    @staticmethod
    def _call_safely(callback: Callable[[], Any]) -> Any:
        try:
            return _jsonable(callback())
        except BindingError as exc:
            raise ToolError(
                "session binding, role, scope or required authorization is unavailable"
            ) from exc
        except (ValidationError, ValueError, TypeError) as exc:
            raise ToolError("request violates the typed operation contract") from exc

    def register(self, definition: ToolDefinition) -> None:
        self._validate_definition(definition)
        name = definition.name
        existing = {tool.name for tool in self.server._tool_manager.list_tools()}
        if name not in self.allowed_tools or name in self._registered or name in existing:
            raise ValueError("tool is not allowed or already registered")
        callback = definition.callback
        payload_type = definition.payload_type
        if payload_type is not None:
            needs_context = definition.enhanced and self.require_codex_context

            def invoke(payload: dict[str, Any]) -> Any:
                return self._call_safely(
                    lambda: self.check_operation_role(
                        definition.role,
                        lambda: callback(
                            payload_type.model_validate_json(
                                json.dumps(payload, ensure_ascii=False)
                            )
                        ),
                        enforce=definition.enhanced,
                    )
                )

            if needs_context:

                def handler(payload: dict[str, Any], context: MCPContext) -> Any:
                    return self.with_codex_context(context, lambda: invoke(payload))
            else:

                def handler(payload: dict[str, Any]) -> Any:
                    return invoke(payload)

            handler.__name__ = name
            handler.__doc__ = definition.description
            handler.__annotations__ = {
                "payload": Annotated[dict[str, Any], WithJsonSchema(inline_schema(payload_type))],
                "return": dict[str, Any],
            }
            if needs_context:
                handler.__annotations__["context"] = MCPContext
        else:

            @wraps(callback)
            def handler(*args: Any, **kwargs: Any) -> Any:
                return callback(*args, **kwargs)

            if definition.parameter_descriptions is not None:
                signature = inspect.signature(callback, follow_wrapped=False)
                hints = get_type_hints(callback, include_extras=True)
                parameters = [
                    parameter.replace(
                        annotation=Annotated[
                            hints[parameter.name],
                            Field(description=definition.parameter_descriptions[parameter.name]),
                        ]
                    )
                    for parameter in signature.parameters.values()
                ]
                handler.__signature__ = signature.replace(  # type: ignore[attr-defined]
                    parameters=parameters,
                    return_annotation=hints.get("return", signature.return_annotation),
                )
        self.server.tool(
            name=name,
            description=definition.description,
            annotations=definition.annotations,
            structured_output=definition.structured_output,
        )(handler)
        self._registered.add(name)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
