from __future__ import annotations

from types import SimpleNamespace
from typing import Literal

import pytest
from token_io_decoupling_core.materialization_models import (
    DirectoryIdentity,
    FactHeading,
    FactMarkdownTemplate,
    FactOrderingItem,
    FactOrderingPlan,
    JsonDocumentTemplate,
    OutputMaterializationGrant,
    SourceFact,
)
from token_io_decoupling_tools.materialization_templates import (
    MODEL,
    MaterializationTemplateError,
    MaterializationTemplateRenderer,
)


def _grant(*, allow_responses: bool = False) -> OutputMaterializationGrant:
    return OutputMaterializationGrant(
        grant_id="grant-1",
        revision=1,
        active=True,
        policy_version=1,
        project_id="project-1",
        root_session_id="root-1",
        worker_session_id="worker-1",
        allocation_id="allocation-1",
        role="Primary Output",
        output_class="code_configuration",
        slice_id="slice-1",
        assignment_hash="a" * 64,
        project_root=DirectoryIdentity(device=1, inode=2),
        artifact_root=DirectoryIdentity(device=1, inode=3),
        policy_scope="generic_project",
        allowed_paths=["src/result.md"],
        allowed_operations=["create"],
        allowed_templates=["fact_markdown"],
        allow_responses_ordering=allow_responses,
    )


class _FakeClient:
    def __init__(
        self,
        parsed,
        *,
        model: str = MODEL,
        status: str = "completed",
        error=None,
        incomplete=None,
        output=None,
    ) -> None:
        self.responses = self
        self.parsed = parsed
        self.model = model
        self.status = status
        self.error = error
        self.incomplete = incomplete
        self.output = [] if output is None else output
        self.calls = []
        self.closed = False

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            status=self.status,
            model=self.model,
            error=self.error,
            incomplete_details=self.incomplete,
            output_parsed=self.parsed,
            output=self.output,
        )

    def close(self):
        self.closed = True


def _fact_template(ordering: Literal["source", "responses"] = "source") -> FactMarkdownTemplate:
    return FactMarkdownTemplate(
        kind="fact_markdown",
        headings=[FactHeading(id="h1", title="Findings"), FactHeading(id="h2", title="Limits")],
        facts=[
            SourceFact(id="f1", heading_id="h1", text="first source fact"),
            SourceFact(id="f2", heading_id="h1", text="second source fact"),
            SourceFact(id="f3", heading_id="h2", text="bounded scope"),
        ],
        ordering=ordering,
    )


def test_json_document_is_canonical_and_rejects_duplicate_nonfinite_and_limits() -> None:
    renderer = MaterializationTemplateRenderer()
    grant = _grant()
    canonical = renderer.render_all(
        [(0, JsonDocumentTemplate(kind="json_document", json_text='{"z":"é", "a":1}'))],
        grant=grant,
        outbound_data_permitted=False,
    )
    assert canonical[0] == '{"a":1,"z":"é"}\n'

    for raw, reason in [
        ('{"a":1,"a":2}', "json_duplicate_key"),
        ('{"value":NaN}', "json_non_finite_number"),
        ("[" * 17 + "0" + "]" * 17, "json_depth_limit_exceeded"),
        ("[" + ",".join(["0"] * 4_096) + "]", "json_node_limit_exceeded"),
    ]:
        with pytest.raises(MaterializationTemplateError, match=reason):
            renderer.render_all(
                [(0, JsonDocumentTemplate(kind="json_document", json_text=raw))],
                grant=grant,
                outbound_data_permitted=False,
            )


def test_fact_markdown_renders_original_source_order_without_api() -> None:
    renderer = MaterializationTemplateRenderer()
    rendered = renderer.render_all(
        [(0, _fact_template())], grant=_grant(), outbound_data_permitted=False
    )
    assert rendered[0] == (
        "## Findings\n\n"
        "- first source fact\n\n"
        "- second source fact\n\n"
        "## Limits\n\n"
        "- bounded scope\n"
    )


def test_responses_orders_only_given_fact_ids_with_fixed_model_and_explicit_env(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
    parsed = FactOrderingPlan(files=[FactOrderingItem(file_index=0, fact_ids=["f2", "f1", "f3"])])
    client = _FakeClient(parsed)
    factory_args = []
    monkeypatch.setattr(
        MaterializationTemplateRenderer,
        "_make_client",
        lambda _self, api_key, base_url: factory_args.append((api_key, base_url)) or client,
    )
    rendered = MaterializationTemplateRenderer().render_all(
        [(0, _fact_template("responses"))],
        grant=_grant(allow_responses=True),
        outbound_data_permitted=True,
    )
    assert factory_args == [("test-key", "https://mock.invalid/v1")]
    assert client.closed is True
    call = client.calls[0]
    assert call["model"] == "gpt-6-luna"
    assert call["text_format"] is FactOrderingPlan
    assert call["store"] is False
    assert call["max_output_tokens"] == 4_000
    assert call["truncation"] == "disabled"
    assert call["tools"] == []
    user_input = call["input"][1]["content"]
    assert "first source fact" in user_input
    assert "second source fact" in user_input
    assert rendered[0].index("second source fact") < rendered[0].index("first source fact")
    assert "bounded scope" in rendered[0]


def test_responses_path_requires_per_call_and_grant_permission(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")

    def never_called(*_args):
        raise AssertionError("factory should not be called")

    template = _fact_template("responses")
    renderer = MaterializationTemplateRenderer()
    monkeypatch.setattr(renderer, "_make_client", never_called)
    with pytest.raises(MaterializationTemplateError, match="outbound_data_not_permitted"):
        renderer.render_all(
            [(0, template)], grant=_grant(allow_responses=True), outbound_data_permitted=False
        )
    with pytest.raises(MaterializationTemplateError, match="responses_ordering_not_granted"):
        renderer.render_all([(0, template)], grant=_grant(), outbound_data_permitted=True)


def test_response_heading_newline_and_combined_character_budget_fail_before_api(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
    renderer = MaterializationTemplateRenderer()
    calls = []
    monkeypatch.setattr(renderer, "_make_client", lambda *_args: calls.append(True))
    template = _fact_template("responses").model_copy(
        update={"headings": [FactHeading(id="h1", title="Bad\rTitle")]}
    )
    with pytest.raises(MaterializationTemplateError, match="fact_markdown_heading_invalid"):
        renderer.render_all(
            [(0, template)], grant=_grant(allow_responses=True), outbound_data_permitted=True
        )
    assert calls == []

    facts = [SourceFact(id=f"f{i}", heading_id="h1", text="x" * 900) for i in range(64)]
    oversized = FactMarkdownTemplate(
        kind="fact_markdown",
        headings=[FactHeading(id="h1", title="Facts")],
        facts=facts,
        ordering="responses",
    )
    with pytest.raises(MaterializationTemplateError, match="responses_input_budget_exceeded"):
        renderer.render_all(
            [(0, oversized)], grant=_grant(allow_responses=True), outbound_data_permitted=True
        )
    assert calls == []


def test_responses_missing_env_invalid_model_or_ids_fail_closed(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    renderer = MaterializationTemplateRenderer()

    def no_client(*_args):
        raise AssertionError("no env")

    monkeypatch.setattr(renderer, "_make_client", no_client)
    with pytest.raises(MaterializationTemplateError, match="openai_environment_unavailable"):
        renderer.render_all(
            [(0, _fact_template("responses"))],
            grant=_grant(allow_responses=True),
            outbound_data_permitted=True,
        )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
    for parsed, model in [
        (
            FactOrderingPlan(files=[FactOrderingItem(file_index=0, fact_ids=["f1", "f2", "f3"])]),
            "other-model",
        ),
        (
            FactOrderingPlan(files=[FactOrderingItem(file_index=0, fact_ids=["f1", "f1", "f3"])]),
            MODEL,
        ),
    ]:
        client = _FakeClient(parsed, model=model)
        renderer = MaterializationTemplateRenderer()
        monkeypatch.setattr(renderer, "_make_client", lambda *_args, client=client: client)
        with pytest.raises(
            MaterializationTemplateError,
            match="responses_invalid_or_incomplete|responses_ordering_invalid",
        ):
            renderer.render_all(
                [(0, _fact_template("responses"))],
                grant=_grant(allow_responses=True),
                outbound_data_permitted=True,
            )


def test_responses_refusal_status_error_incomplete_and_provider_throw_are_sanitized(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
    parsed = FactOrderingPlan(files=[FactOrderingItem(file_index=0, fact_ids=["f1", "f2", "f3"])])
    responses = [
        _FakeClient(parsed, output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])]),
        _FakeClient(parsed, status="failed"),
        _FakeClient(parsed, error={"provider": "private error"}),
        _FakeClient(parsed, incomplete={"reason": "private detail"}),
    ]
    for client in responses:
        renderer = MaterializationTemplateRenderer()
        monkeypatch.setattr(renderer, "_make_client", lambda *_args, client=client: client)
        with pytest.raises(MaterializationTemplateError, match="responses_invalid_or_incomplete"):
            renderer.render_all(
                [(0, _fact_template("responses"))],
                grant=_grant(allow_responses=True),
                outbound_data_permitted=True,
            )
        assert client.closed

    renderer = MaterializationTemplateRenderer()
    throwing_client = _ThrowingClient()
    monkeypatch.setattr(renderer, "_make_client", lambda *_args: throwing_client)
    with pytest.raises(MaterializationTemplateError, match="responses_provider_error") as caught:
        renderer.render_all(
            [(0, _fact_template("responses"))],
            grant=_grant(allow_responses=True),
            outbound_data_permitted=True,
        )
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert throwing_client.closed


class _ThrowingClient:
    def __init__(self):
        self.responses = self
        self.closed = False

    def parse(self, **_kwargs):
        raise RuntimeError("secret provider payload")

    def close(self):
        self.closed = True
