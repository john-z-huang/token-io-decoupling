"""One declarative registration template for every MCP tool."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from inspect import Parameter, Signature, signature
from typing import Annotated, Any, cast, get_type_hints

from mcp.server import MCPServer
from mcp.server.mcpserver import Context as MCPContext
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, TypeAdapter, ValidationError, WithJsonSchema

from token_io_decoupling_core.binding import BindingError, BindingProvider
from token_io_decoupling_core.codex_context import CodexCallerBoundProvider
from token_io_decoupling_transport.payloads import inline_schema


@dataclass(frozen=True)
class ToolDefinition:
    """Describe an operation without registering it or executing its callback.

    Native signatures retain flat arguments and SDK validation. A payload model
    retains the existing JSON envelope, strict validation and bounded errors.
    Role and caller-context guards are operation requirements, not workflow steps.
    """

    name: str
    callback: Callable[..., Any]
    payload_type: type[BaseModel] | None = None
    annotations: ToolAnnotations | None = None
    structured_output: bool | None = False
    parameter_descriptions: Mapping[str, str] | None = None
    bounded_errors: bool = False
    role: str | None = None
    codex_guard: bool = False


class ToolRegistrar:
    """Register a complete fixed inventory through one SDK registration call."""

    def __init__(
        self,
        server: MCPServer[Any],
        *,
        provider: BindingProvider,
        state_provider: BindingProvider,
        allowed_tools: frozenset[str],
        require_codex_context: bool,
        bound_role_for: Callable[[BindingProvider], str | None],
        description_for: Callable[[str], str],
    ) -> None:
        self.server = server
        self.provider = provider
        self.state_provider = state_provider
        self.allowed_tools = allowed_tools
        self.require_codex_context = require_codex_context
        self._bound_role_for = bound_role_for
        self.description_for = description_for

    def register_all(self, definitions: Sequence[ToolDefinition]) -> None:
        names = [definition.name for definition in definitions]
        if len(names) != len(set(names)) or set(names) != self.allowed_tools:
            raise ValueError("tool definitions differ from the server manifest")
        for definition in definitions:
            handler = self._handler(definition)
            self.server.tool(
                name=definition.name,
                description=self.description_for(definition.name),
                annotations=(
                    definition.annotations.model_copy(deep=True)
                    if definition.annotations is not None
                    else None
                ),
                structured_output=definition.structured_output,
            )(handler)

    def check_operation_role(self, expected: str | None, callback: Callable[[], Any]) -> Any:
        if expected is None:
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
            value = callback()
            return _jsonable(value)
        except BindingError as exc:
            raise ToolError(
                "session binding, role, scope or required authorization is unavailable"
            ) from exc
        except (ValidationError, ValueError, TypeError) as exc:
            raise ToolError("request violates the typed operation contract") from exc

    def _handler(self, definition: ToolDefinition) -> Callable[..., Any]:
        input_signature = _signature(definition)
        public_signature = input_signature
        payload_adapter = (
            TypeAdapter(definition.payload_type) if definition.payload_type is not None else None
        )
        needs_context = definition.codex_guard and self.require_codex_context

        def handler(*args: Any, **kwargs: Any) -> Any:
            context = kwargs.pop("context", None) if needs_context else None

            def invoke() -> Any:
                if payload_adapter is not None:
                    payload = input_signature.bind(*args, **kwargs).arguments["payload"]
                    return definition.callback(
                        payload_adapter.validate_json(json.dumps(payload, ensure_ascii=False))
                    )
                return definition.callback(*args, **kwargs)

            def call() -> Any:
                def operation() -> Any:
                    return self.check_operation_role(definition.role, invoke)

                if payload_adapter is not None or definition.bounded_errors:
                    return self._call_safely(operation)
                return operation()

            return self.with_codex_context(context, call) if needs_context else call()

        if needs_context:
            public_signature = public_signature.replace(
                parameters=[
                    *public_signature.parameters.values(),
                    Parameter("context", kind=Parameter.KEYWORD_ONLY, annotation=MCPContext),
                ]
            )
        callback_name = getattr(definition.callback, "__name__", definition.name)
        handler.__name__ = (
            definition.name
            if definition.payload_type is not None or callback_name == "<lambda>"
            else callback_name
        )
        handler.__doc__ = self.description_for(definition.name)
        handler.__annotations__ = {
            parameter.name: parameter.annotation
            for parameter in public_signature.parameters.values()
        }
        handler.__annotations__["return"] = public_signature.return_annotation
        cast(Any, handler).__signature__ = public_signature
        return handler


def _signature(definition: ToolDefinition) -> Signature:
    if definition.payload_type is not None:
        return Signature(
            parameters=[
                Parameter(
                    "payload",
                    kind=Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Annotated[
                        dict[str, Any], WithJsonSchema(inline_schema(definition.payload_type))
                    ],
                )
            ],
            return_annotation=dict[str, Any],
        )
    native = signature(definition.callback, follow_wrapped=False)
    hints = get_type_hints(definition.callback, include_extras=True)
    descriptions = definition.parameter_descriptions
    if descriptions is not None and set(descriptions) != set(native.parameters):
        raise ValueError(f"MCP parameter descriptions do not match {definition.name} signature")
    parameters = []
    for parameter in native.parameters.values():
        annotation = hints.get(parameter.name, parameter.annotation)
        if descriptions is not None:
            annotation = Annotated[annotation, Field(description=descriptions[parameter.name])]
        parameters.append(parameter.replace(annotation=annotation))
    return native.replace(
        parameters=parameters, return_annotation=hints.get("return", native.return_annotation)
    )


def _jsonable(value: Any) -> Any:
    from pydantic import BaseModel as PydanticBaseModel

    if isinstance(value, PydanticBaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
