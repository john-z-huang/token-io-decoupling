"""不发送真实请求的官方 smoke 配置守卫和安全资源清理回归。"""

from __future__ import annotations

import httpx2
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from support import official_api_smoke as smoke


@pytest.mark.parametrize("name", ["OPENAI_API_KEY_OFFICAL", "OPENAI_BASE_URL_OFFICAL"])
@pytest.mark.parametrize("value", [None, "", "   "], ids=["missing", "empty", "blank"])
def test_official_environment_requires_explicit_nonblank_values(monkeypatch, name, value):
    monkeypatch.setenv("OPENAI_API_KEY_OFFICAL", "synthetic-key")
    monkeypatch.setenv("OPENAI_BASE_URL_OFFICAL", "https://official.invalid/v1")
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)

    with pytest.raises(pytest.fail.Exception, match=name):
        smoke.official_environment()


@pytest.mark.parametrize(
    ("trust_env", "max_retries", "reason"),
    [
        pytest.param(True, 0, None, id="valid"),
        pytest.param(False, 0, "environment-aware HTTPX2", id="environment-disabled"),
        pytest.param(True, 2, "zero automatic retries", id="automatic-retries"),
    ],
)
def test_official_client_preserves_transport_and_retry_guards(trust_env, max_retries, reason):
    with httpx2.Client(
        transport=httpx2.MockTransport(lambda _: httpx2.Response(200)), trust_env=trust_env
    ) as transport:
        client = OpenAI(
            api_key="synthetic-key",
            base_url="https://official.invalid/v1",
            http_client=transport,
            max_retries=max_retries,
        )
        if reason is None:
            assert smoke.validate_official_client(client) is None
        else:
            with pytest.raises(pytest.fail.Exception, match=reason):
                smoke.validate_official_client(client)


_REQUEST = httpx2.Request("GET", "https://official.invalid/v1")


@pytest.mark.parametrize("phase", ["creation", "request"])
@pytest.mark.parametrize(
    ("error", "reason"),
    [
        pytest.param(ValueError("private diagnostic"), "failed with ValueError", id="unexpected"),
        pytest.param(
            APIStatusError(
                "private diagnostic", response=httpx2.Response(429, request=_REQUEST), body=None
            ),
            "HTTP status 429",
            id="status",
        ),
        pytest.param(APITimeoutError(request=_REQUEST), "request timed out", id="timeout"),
        pytest.param(
            APIConnectionError(message="private diagnostic", request=_REQUEST),
            "connection failed",
            id="connection",
        ),
    ],
)
def test_official_client_reports_safe_failures_and_closes_created_clients(
    monkeypatch, phase, error, reason
):
    with httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(200))) as transport:
        client = OpenAI(
            api_key="synthetic-key", base_url="https://official.invalid/v1", http_client=transport
        )

        def factory(*args, **kwargs):
            if phase == "creation":
                raise error
            return client

        monkeypatch.setattr(smoke, "make_openai_client", factory)

        with pytest.raises(pytest.fail.Exception, match=reason) as failure:
            with smoke.official_client("synthetic-key", "https://official.invalid/v1"):
                raise error

        assert "private diagnostic" not in str(failure.value)
        assert transport.is_closed is (phase == "request")
