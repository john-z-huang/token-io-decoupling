"""Bounded, deterministic templates and optional fact-ID-only Responses ordering."""

from __future__ import annotations

import json
import math
import os
from typing import Any, cast

from token_io_decoupling_core.materialization_models import (
    MAX_MATERIALIZATION_TEXT_CHARS,
    FactMarkdownTemplate,
    FactOrderingPlan,
    JsonDocumentTemplate,
    LiteralTextTemplate,
    MaterializationTemplate,
    OutputMaterializationGrant,
)

MODEL = "gpt-6-luna"
TIMEOUT_SECONDS = 30.0
MAX_INPUT_CHARS = 48_000
MAX_OUTPUT_TOKENS = 4_000
_SYSTEM_INSTRUCTIONS = (
    "Order only the supplied fact IDs within their existing heading. "
    "Return every supplied fact ID exactly once, grouped by file_index. "
    "Do not add, omit, rename, or explain any ID or produce source text."
)


class MaterializationTemplateError(Exception):
    """Sanitized rendering or provider failure with a stable reason code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MaterializationTemplateRenderer:
    def render_all(
        self,
        templates: list[tuple[int, MaterializationTemplate]],
        *,
        grant: OutputMaterializationGrant,
        outbound_data_permitted: bool,
    ) -> dict[int, str]:
        response_templates = [
            (index, template)
            for index, template in templates
            if isinstance(template, FactMarkdownTemplate) and template.ordering == "responses"
        ]
        # Heading validation must happen before any optional provider request.
        if any(
            "\n" in heading.title or "\r" in heading.title
            for _, template in response_templates
            for heading in template.headings
        ):
            raise MaterializationTemplateError("fact_markdown_heading_invalid")
        ordering: dict[int, list[str]] = {}
        if response_templates:
            if not outbound_data_permitted:
                raise MaterializationTemplateError("outbound_data_not_permitted")
            if not grant.allow_responses_ordering:
                raise MaterializationTemplateError("responses_ordering_not_granted")
            ordering = self._order_facts(response_templates)
        rendered: dict[int, str] = {}
        for index, template in templates:
            if isinstance(template, FactMarkdownTemplate):
                result = self._render_fact_markdown(template, ordering.get(index))
            elif isinstance(template, JsonDocumentTemplate):
                value = self._parse_bounded_json(template.json_text)
                result = (
                    json.dumps(
                        value,
                        ensure_ascii=False,
                        allow_nan=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
            elif isinstance(template, LiteralTextTemplate):
                result = template.text
            else:
                raise MaterializationTemplateError("materialization_template_invalid")
            if len(result) > MAX_MATERIALIZATION_TEXT_CHARS:
                raise MaterializationTemplateError("candidate_file_char_limit_exceeded")
            try:
                result.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise MaterializationTemplateError("candidate_content_not_valid_utf8") from exc
            rendered[index] = result
        return rendered

    def _order_facts(
        self, templates: list[tuple[int, FactMarkdownTemplate]]
    ) -> dict[int, list[str]]:
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not api_key or not api_key.strip() or not base_url or not base_url.strip():
            raise MaterializationTemplateError("openai_environment_unavailable")
        payload = {
            "files": [
                {
                    "file_index": index,
                    "headings": [item.model_dump(mode="json") for item in template.headings],
                    "facts": [item.model_dump(mode="json") for item in template.facts],
                }
                for index, template in templates
            ]
        }
        input_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(input_text) + len(_SYSTEM_INSTRUCTIONS) > MAX_INPUT_CHARS:
            raise MaterializationTemplateError("responses_input_budget_exceeded")
        client: object | None = None
        response: object | None = None
        provider_failure: str | None = None
        try:
            client = self._make_client(api_key, base_url)
            response = cast(Any, client).responses.parse(
                model=MODEL,
                input=[
                    {
                        "role": "system",
                        "content": _SYSTEM_INSTRUCTIONS,
                    },
                    {"role": "user", "content": input_text},
                ],
                text_format=FactOrderingPlan,
                store=False,
                reasoning={"effort": "medium"},
                max_output_tokens=MAX_OUTPUT_TOKENS,
                truncation="disabled",
                tools=[],
            )
        except Exception as exc:
            provider_failure = (
                "responses_timeout" if isinstance(exc, TimeoutError) else "responses_provider_error"
            )
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        if provider_failure is not None:
            # Raise outside the exception handler so no provider exception is
            # available through caller-visible cause or context attributes.
            raise MaterializationTemplateError(provider_failure)
        assert response is not None
        if (
            getattr(response, "status", None) != "completed"
            or getattr(response, "error", None) is not None
            or getattr(response, "incomplete_details", None) is not None
            or getattr(response, "model", None) != MODEL
            or self._is_refusal(response)
        ):
            raise MaterializationTemplateError("responses_invalid_or_incomplete")
        parsed = getattr(response, "output_parsed", None)
        if type(parsed) is not FactOrderingPlan:
            raise MaterializationTemplateError("responses_ordering_invalid")
        expected = {index: {fact.id for fact in template.facts} for index, template in templates}
        actual_indices = [item.file_index for item in parsed.files]
        if len(set(actual_indices)) != len(actual_indices) or set(actual_indices) != set(expected):
            raise MaterializationTemplateError("responses_ordering_invalid")
        result: dict[int, list[str]] = {}
        for item in parsed.files:
            if (
                len(set(item.fact_ids)) != len(item.fact_ids)
                or set(item.fact_ids) != expected[item.file_index]
            ):
                raise MaterializationTemplateError("responses_ordering_invalid")
            result[item.file_index] = item.fact_ids
        return result

    def _make_client(self, api_key: str, base_url: str) -> object:
        from openai import OpenAI

        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=TIMEOUT_SECONDS,
            max_retries=0,
        )

    @staticmethod
    def _render_fact_markdown(
        template: FactMarkdownTemplate, ordered_fact_ids: list[str] | None
    ) -> str:
        if any("\n" in item.title or "\r" in item.title for item in template.headings):
            raise MaterializationTemplateError("fact_markdown_heading_invalid")
        facts = {item.id: item for item in template.facts}
        fact_ids = ordered_fact_ids or [item.id for item in template.facts]
        if len(fact_ids) != len(facts) or set(fact_ids) != set(facts):
            raise MaterializationTemplateError("fact_ordering_ids_invalid")
        lines: list[str] = []
        for heading in template.headings:
            lines.extend([f"## {heading.title}", ""])
            for fact_id in fact_ids:
                fact = facts[fact_id]
                if fact.heading_id == heading.id:
                    lines.extend([f"- {fact.text}", ""])
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _parse_bounded_json(raw: str) -> Any:
        def pairs_to_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise MaterializationTemplateError("json_duplicate_key")
                result[key] = value
            return result

        def reject_constant(_value: str) -> None:
            raise MaterializationTemplateError("json_non_finite_number")

        try:
            value = json.loads(
                raw, object_pairs_hook=pairs_to_object, parse_constant=reject_constant
            )
        except MaterializationTemplateError:
            raise
        except (json.JSONDecodeError, RecursionError, ValueError) as exc:
            raise MaterializationTemplateError("json_document_invalid") from exc
        count = 0

        def inspect(node: Any, depth: int) -> None:
            nonlocal count
            count += 1
            if count > 4_096:
                raise MaterializationTemplateError("json_node_limit_exceeded")
            if depth > 16:
                raise MaterializationTemplateError("json_depth_limit_exceeded")
            if isinstance(node, dict):
                for child in node.values():
                    inspect(child, depth + 1)
            elif isinstance(node, list):
                for child in node:
                    inspect(child, depth + 1)
            elif isinstance(node, float) and not math.isfinite(node):
                raise MaterializationTemplateError("json_non_finite_number")

        inspect(value, 0)
        return value

    @staticmethod
    def _is_refusal(response: object) -> bool:
        output = getattr(response, "output", None)
        if not isinstance(output, list):
            return False
        return any(
            isinstance(content, list)
            and any(getattr(part, "type", None) == "refusal" for part in content)
            for item in output
            if (content := getattr(item, "content", None)) is not None
        )
