"""Strict wire payload models and their inline JSON schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, create_model

from token_io_decoupling_core.models import StrictModel


class ToolPayload(StrictModel):
    """Shared base for strict, extra-forbidden wire payload containers."""


def payload_model(name: str, **fields: Any) -> type[BaseModel]:
    return create_model(name, __base__=ToolPayload, **fields)


def inline_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def expand(value: Any) -> Any:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                target = definitions[reference.rsplit("/", 1)[1]]
                siblings = {key: item for key, item in value.items() if key != "$ref"}
                return {**expand(target), **expand(siblings)}
            return {key: expand(item) for key, item in value.items()}
        if isinstance(value, list):
            return [expand(item) for item in value]
        return value

    return expand(schema)


_inline_schema = inline_schema


_NO_ARGUMENTS = payload_model("NoArguments")
