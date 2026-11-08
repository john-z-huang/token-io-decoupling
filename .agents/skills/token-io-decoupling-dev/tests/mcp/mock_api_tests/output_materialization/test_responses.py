"""模拟 Responses 排序、响应校验与授权新鲜度。"""

from __future__ import annotations

from types import SimpleNamespace

from support.materialization_workspace import (
    _apply,
    _workspace,
)

from token_io_decoupling_core.materialization_models import (
    AbsentBaseline,
    FactHeading,
    FactMarkdownTemplate,
    FactOrderingItem,
    FactOrderingPlan,
    MaterializationFileSpec,
    MaterializationPrepareRequest,
    SourceFact,
)
from token_io_decoupling_tools.output_materialization import (
    OutputMaterializerConfig,
)


def test_api_grant_revision_change_prevents_candidate_persistence(tmp_path, monkeypatch) -> None:
    path = "src/output.md"
    _project, artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )

    class _Client:
        responses = None

        def __init__(self) -> None:
            self.responses = self

        def parse(self, **_kwargs):
            assert grant_provider.grant is not None
            grant_provider.grant = grant_provider.grant.model_copy(update={"revision": 2})
            return SimpleNamespace(
                status="completed",
                model="gpt-6-luna",
                error=None,
                incomplete_details=None,
                output_parsed=FactOrderingPlan(
                    files=[FactOrderingItem(file_index=0, fact_ids=["fact-1"])]
                ),
                output=[],
            )

        def close(self) -> None:
            pass

    try:
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
        monkeypatch.setattr(materializer._renderer, "_make_client", lambda *_args: _Client())
        request = MaterializationPrepareRequest(
            action="prepare",
            outbound_data_permitted=True,
            files=[
                MaterializationFileSpec(
                    path=path,
                    operation="create",
                    baseline=AbsentBaseline(state="absent"),
                    template=FactMarkdownTemplate(
                        kind="fact_markdown",
                        headings=[FactHeading(id="h", title="Facts")],
                        facts=[SourceFact(id="fact-1", heading_id="h", text="source fact")],
                        ordering="responses",
                    ),
                )
            ],
        )
        result = materializer.execute(request)
        assert result["status"] == "blocked"
        assert result["reason_code"] == "worker_or_operator_grant_changed"
        assert not list(artifacts.iterdir())
    finally:
        materializer.close()
        preflight.close()


def test_responses_ordering_is_fake_api_only_and_materializes_source_facts(
    tmp_path, monkeypatch
) -> None:
    path = "src/result.md"
    project, _artifacts, _state, _provider, preflight, grant_provider, config, materializer = (
        _workspace(tmp_path, [path])
    )
    client = SimpleNamespace()
    client.closed = False
    client.calls = []
    client.responses = client

    def parse(**kwargs):
        client.calls.append(kwargs)
        return SimpleNamespace(
            status="completed",
            model="gpt-6-luna",
            error=None,
            incomplete_details=None,
            output_parsed=FactOrderingPlan(
                files=[FactOrderingItem(file_index=0, fact_ids=["second", "first"])]
            ),
            output=[],
        )

    def close():
        client.closed = True

    client.parse = parse
    client.close = close
    factory_calls = []

    def factory(key: str, base_url: str) -> object:
        factory_calls.append((key, base_url))
        return client

    try:
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
        config = OutputMaterializerConfig(
            config.project_root,
            config.artifact_root,
            config.grant_provider,
            config.authorization_provider,
        )
        materializer.close()
        from token_io_decoupling_tools.output_materialization import (
            OutputMaterializationService as Service,
        )

        materializer = Service(
            authorization_provider=config.authorization_provider,
            compliance_service=preflight,
            config=config,
        )
        monkeypatch.setattr(materializer._renderer, "_make_client", factory)
        grant_provider.grant = grant_provider.grant.model_copy(
            update={"allow_responses_ordering": True}
        )
        request = MaterializationPrepareRequest(
            action="prepare",
            outbound_data_permitted=True,
            files=[
                MaterializationFileSpec(
                    path=path,
                    operation="create",
                    baseline=AbsentBaseline(state="absent"),
                    template=FactMarkdownTemplate(
                        kind="fact_markdown",
                        headings=[FactHeading(id="h", title="Facts")],
                        facts=[
                            SourceFact(id="first", heading_id="h", text="first source"),
                            SourceFact(id="second", heading_id="h", text="second source"),
                        ],
                        ordering="responses",
                    ),
                )
            ],
        )
        prepared = materializer.execute(request, expected_binding=_state)
        assert prepared["status"] == "prepared"
        assert factory_calls == [("fake-key", "https://mock.invalid/v1")]
        assert client.closed
        assert client.calls[0]["model"] == "gpt-6-luna"
        assert client.calls[0]["max_output_tokens"] == 4_000
        assert client.calls[0]["tools"] == []
        apply = _apply(materializer, prepared, expected_binding=_state)
        assert apply["status"] == "applied"
        result = (project / path).read_text()
        assert result.index("second source") < result.index("first source")
    finally:
        materializer.close()
        preflight.close()


def test_invalid_responses_result_creates_no_candidate_artifact(tmp_path, monkeypatch) -> None:
    path = "src/result.md"
    project, artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    refusal = SimpleNamespace(
        status="completed",
        model="gpt-6-luna",
        error=None,
        incomplete_details=None,
        output_parsed=None,
        output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])],
    )

    class _Client:
        responses = None

        def __init__(self):
            self.responses = self

        def parse(self, **_kwargs):
            return refusal

        def close(self):
            pass

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
    monkeypatch.setattr(materializer._renderer, "_make_client", lambda *_args: _Client())
    request = MaterializationPrepareRequest(
        action="prepare",
        outbound_data_permitted=True,
        files=[
            MaterializationFileSpec(
                path=path,
                operation="create",
                baseline=AbsentBaseline(state="absent"),
                template=FactMarkdownTemplate(
                    kind="fact_markdown",
                    headings=[FactHeading(id="h", title="Facts")],
                    facts=[SourceFact(id="f", heading_id="h", text="source fact")],
                    ordering="responses",
                ),
            )
        ],
    )
    try:
        result = materializer.execute(request)
        assert result["status"] == "blocked"
        assert not list(artifacts.iterdir())
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()
