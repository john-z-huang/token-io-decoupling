"""Strict wire payload models and their inline JSON schemas."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StrictInt, StringConstraints, create_model, model_validator
from token_io_decoupling_core.models import StrictModel
from token_io_decoupling_core.workflow_models import ActiveCheckpointNode


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


class RuleContextPayload(ToolPayload):
    node_id: ActiveCheckpointNode
    language: Literal["en", "zh_cn"] = "en"
    context_version: Literal[1] | None = None
    fragment_ids: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]]
        | None,
        Field(max_length=128),
    ] = None
    max_chars: Annotated[StrictInt, Field(ge=256, le=60_000)] | None = None

    @model_validator(mode="before")
    @classmethod
    def require_strict_context_version(cls, value: Any) -> Any:
        if isinstance(value, dict):
            version = value.get("context_version")
            if version is not None and (type(version) is not int or version != 1):
                raise ValueError("context_version must be the integer 1")
        return value

    @model_validator(mode="after")
    def require_explicit_context_version(self) -> RuleContextPayload:
        if self.context_version is None and (
            self.fragment_ids is not None or self.max_chars is not None
        ):
            raise ValueError("fragment_ids and max_chars require context_version=1")
        if self.fragment_ids is not None and len(self.fragment_ids) != len(set(self.fragment_ids)):
            raise ValueError("fragment_ids must not contain duplicates")
        return self


_RULE_CONTEXT = RuleContextPayload
