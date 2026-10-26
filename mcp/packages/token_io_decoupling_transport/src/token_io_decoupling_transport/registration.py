"""Role-aware MCP tool registration shared by profile registrars."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context as MCPContext
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, TypeAdapter, ValidationError, WithJsonSchema
from token_io_decoupling_core.binding import BindingError, BindingProvider
from token_io_decoupling_core.codex_context import CodexCallerBoundProvider
from token_io_decoupling_core.profiles import PROFILE_ROLES, PROFILE_TOOLS
from token_io_decoupling_state.service import StateServiceError

from token_io_decoupling_transport.payloads import inline_schema
from token_io_decoupling_transport.tool_metadata import tool_description


class ToolRegistrar:
    """Apply profile exposure, role checks, typed payloads, and Codex request scope."""

    def __init__(
        self,
        server: MCPServer[Any],
        *,
        provider: BindingProvider,
        state_provider: BindingProvider,
        profile: str | None,
        bound_role: str | None,
        embedded: bool,
        require_codex_context: bool,
        bound_role_for: Callable[[BindingProvider], str | None],
    ) -> None:
        self.server = server
        self.provider = provider
        self.state_provider = state_provider
        self.profile = profile
        self.bound_role = bound_role
        self.embedded = embedded
        self.require_codex_context = require_codex_context
        self._bound_role_for = bound_role_for

    def include(self, name: str) -> bool:
        return self.profile is None or name in PROFILE_TOOLS[self.profile]

    def check_profile_role(
        self, expected: str | None, callback: Callable[[], Any], *, enforce: bool = True
    ) -> Any:
        if self.profile is None or not enforce:
            return callback()
        actual = self._bound_role_for(self.provider)
        required = PROFILE_ROLES[self.profile]
        if actual is None or (required is not None and actual != required):
            raise BindingError("usable host binding for this profile is unavailable")
        if expected is not None and actual != expected:
            raise BindingError("host binding role does not match this operation")
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
            raise ToolError("verified Codex caller context is unavailable or mismatched") from exc

    @staticmethod
    def _call_safely(callback: Callable[[], Any]) -> Any:
        try:
            value = callback()
            return _jsonable(value)
        except BindingError as exc:
            raise ToolError("trusted host binding or required guard is unavailable") from exc
        except StateServiceError as exc:
            raise ToolError(str(exc)) from exc
        except (ValidationError, ValueError, TypeError) as exc:
            raise ToolError("request violates the typed operation contract") from exc

    def register(
        self,
        name: str,
        payload_type: type[BaseModel],
        callback: Callable[[Any], Any],
        *,
        enhanced: bool = True,
        role: str | None = None,
    ) -> None:
        if not self.include(name) or (
            self.profile is None and role is not None and role != self.bound_role
        ):
            return
        needs_context = enhanced and self.require_codex_context

        if needs_context:

            def handler(payload: dict[str, Any], context: MCPContext) -> Any:
                if enhanced and not self.embedded and self.profile is None:
                    raise ToolError("enhanced operations are unavailable in the unbound CLI")
                return self.with_codex_context(
                    context,
                    lambda: self._call_safely(
                        lambda: self.check_profile_role(
                            role,
                            lambda: callback(
                                TypeAdapter(payload_type).validate_json(
                                    json.dumps(payload, ensure_ascii=False)
                                )
                            ),
                            enforce=enhanced,
                        )
                    ),
                )
        else:

            def handler(payload: dict[str, Any]) -> Any:
                if enhanced and not self.embedded and self.profile is None:
                    raise ToolError("enhanced operations are unavailable in the unbound CLI")
                return self._call_safely(
                    lambda: self.check_profile_role(
                        role,
                        lambda: callback(
                            TypeAdapter(payload_type).validate_json(
                                json.dumps(payload, ensure_ascii=False)
                            )
                        ),
                        enforce=enhanced,
                    )
                )

        handler.__name__ = name
        handler.__doc__ = tool_description(name)
        annotations: dict[str, Any] = {
            "payload": Annotated[dict[str, Any], WithJsonSchema(inline_schema(payload_type))],
            "return": dict[str, Any],
        }
        if needs_context:
            annotations["context"] = MCPContext
        handler.__annotations__ = annotations
        self.server.tool(name=name, description=tool_description(name), structured_output=False)(
            handler
        )

    def register_no_args(
        self,
        name: str,
        callback: Callable[[], Any],
        *,
        codex_guard: bool = False,
        role: str | None = None,
    ) -> None:
        if not self.include(name):
            return
        if codex_guard:

            def handler(context: MCPContext) -> Any:
                enforce_role = name not in {"workflow_capabilities", "database_schema_status"}
                return self.with_codex_context(
                    context,
                    lambda: self._call_safely(
                        lambda: self.check_profile_role(role, callback, enforce=enforce_role)
                    ),
                )
        else:

            def handler() -> Any:
                enforce_role = name not in {"workflow_capabilities", "database_schema_status"}
                return self._call_safely(
                    lambda: self.check_profile_role(role, callback, enforce=enforce_role)
                )

        handler.__name__ = name
        handler.__doc__ = tool_description(name)
        annotations: dict[str, Any] = {"return": dict[str, Any]}
        if codex_guard:
            annotations["context"] = MCPContext
        handler.__annotations__ = annotations
        self.server.tool(name=name, description=tool_description(name), structured_output=False)(
            handler
        )

    def register_enhanced_no_args(
        self, name: str, callback: Callable[[], Any], *, role: str
    ) -> None:
        if not self.include(name) or (self.profile is None and role != self.bound_role):
            return
        if self.require_codex_context:

            def handler(context: MCPContext) -> Any:
                if not self.embedded and self.profile is None:
                    raise ToolError("enhanced operations are unavailable in the unbound CLI")
                return self.with_codex_context(
                    context,
                    lambda: self._call_safely(lambda: self.check_profile_role(role, callback)),
                )
        else:

            def handler() -> Any:
                if not self.embedded and self.profile is None:
                    raise ToolError("enhanced operations are unavailable in the unbound CLI")
                return self._call_safely(lambda: self.check_profile_role(role, callback))

        handler.__name__ = name
        handler.__doc__ = tool_description(name)
        annotations: dict[str, Any] = {"return": dict[str, Any]}
        if self.require_codex_context:
            annotations["context"] = MCPContext
        handler.__annotations__ = annotations
        self.server.tool(name=name, description=tool_description(name), structured_output=False)(
            handler
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
