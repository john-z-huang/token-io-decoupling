from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from typing import Any

import httpx2
import pytest
from openai import APIConnectionError, OpenAI
from token_io_decoupling_workflow import (
    child_effort,
    decision_context,
    decisions,
    delegation_decisions,
    materialization_templates,
    workflow_routing,
)
from token_io_decoupling_workflow.openai_client import make_openai_client

_FACTORIES = (
    (child_effort.ChildEffortSelector, child_effort.DECISIONS_TIMEOUT_SECONDS, True),
    (decision_context.DecisionContextGenerator, decision_context.GENERATION_TIMEOUT_SECONDS, True),
    (decisions.DecisionsAdvisor, decisions.DECISIONS_TIMEOUT_SECONDS, True),
    (
        delegation_decisions.DelegationDecisionSelector,
        delegation_decisions.DECISIONS_TIMEOUT_SECONDS,
        True,
    ),
    (
        materialization_templates.MaterializationTemplateRenderer,
        materialization_templates.TIMEOUT_SECONDS,
        False,
    ),
    (workflow_routing.WorkflowRouter, workflow_routing.DECISIONS_TIMEOUT_SECONDS, True),
)
_PROXY_ENV_NAMES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)


def _clear_proxy_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _PROXY_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


@contextmanager
def _http_server() -> Generator[tuple[str, list[str]], None, None]:
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *_args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


@contextmanager
def _proxy_server() -> Generator[tuple[str, list[tuple[str, str]]], None, None]:
    requests: list[tuple[str, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(("GET", self.path))
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_CONNECT(self) -> None:
            requests.append(("CONNECT", self.path))
            self.send_response(502)
            self.end_headers()

        def log_message(self, format: str, *_args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def _get(client: OpenAI) -> httpx2.Response:
    return client.get("/probe", cast_to=httpx2.Response)


@pytest.mark.parametrize(("factory", "timeout", "injectable"), _FACTORIES)
def test_each_default_factory_uses_httpx2_and_preserves_sdk_options(
    factory, timeout: float, injectable: bool
) -> None:
    client = factory._make_client(
        SimpleNamespace(_client_factory=None), "synthetic", "http://example.invalid/v1"
    )
    assert isinstance(client, OpenAI)
    assert isinstance(client._client, httpx2.Client)
    assert client._client._trust_env is True
    assert client._client.follow_redirects is True
    assert client.timeout == timeout
    assert client._client.timeout.as_dict() == {
        "connect": timeout,
        "read": timeout,
        "write": timeout,
        "pool": timeout,
    }
    assert client.max_retries == 0
    client.close()
    assert client._client.is_closed

    if injectable:
        injected = object()
        proxy = SimpleNamespace(_client_factory=lambda *_args: injected)
        assert factory._make_client(proxy, "synthetic", "http://unused") is injected


def test_openai_constructor_failure_closes_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    import token_io_decoupling_workflow.openai_client as client_module

    class TrackedClient:
        closed = False

        def close(self) -> None:
            self.closed = True

    http_client = TrackedClient()
    monkeypatch.setattr(client_module, "DefaultHttpx2Client", lambda **_kwargs: http_client)

    def fail_constructor(**_kwargs):
        raise RuntimeError("synthetic constructor error")

    monkeypatch.setattr(client_module, "OpenAI", fail_constructor)
    with pytest.raises(RuntimeError, match="synthetic constructor error"):
        make_openai_client("synthetic", "http://unused", timeout=3)
    assert http_client.closed


@pytest.mark.parametrize("proxy_name", ("HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"))
def test_sdk_http_request_uses_uppercase_and_lowercase_proxy_variables(
    monkeypatch: pytest.MonkeyPatch, proxy_name: str
) -> None:
    _clear_proxy_environment(monkeypatch)
    with _proxy_server() as (proxy_url, requests):
        monkeypatch.setenv(proxy_name, proxy_url)
        client = make_openai_client("synthetic", "http://example.invalid/v1", timeout=2)
        try:
            assert _get(client).status_code == 200
        finally:
            client.close()
    assert requests and requests[0][0] == "GET"
    assert requests[0][1].startswith("http://example.invalid/")


@pytest.mark.parametrize("proxy_name", ("HTTPS_PROXY", "https_proxy"))
def test_sdk_https_request_uses_proxy_connect(
    monkeypatch: pytest.MonkeyPatch, proxy_name: str
) -> None:
    _clear_proxy_environment(monkeypatch)
    with _proxy_server() as (proxy_url, requests):
        monkeypatch.setenv(proxy_name, proxy_url)
        client = make_openai_client("synthetic", "https://example.invalid/v1", timeout=2)
        try:
            with pytest.raises(APIConnectionError):
                _get(client)
        finally:
            client.close()
    assert requests == [("CONNECT", "example.invalid:443")]


def test_no_proxy_bypasses_proxy_and_default_without_proxy_is_direct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_proxy_environment(monkeypatch)
    with _http_server() as (base_url, direct_requests):
        with _proxy_server() as (proxy_url, proxy_requests):
            monkeypatch.setenv("HTTP_PROXY", proxy_url)
            monkeypatch.setenv("NO_PROXY", "127.0.0.1")
            client = make_openai_client("synthetic", base_url, timeout=2)
            try:
                assert _get(client).status_code == 200
            finally:
                client.close()
            assert direct_requests
            assert proxy_requests == []

            _clear_proxy_environment(monkeypatch)
            client = make_openai_client("synthetic", base_url, timeout=2)
            try:
                assert _get(client).status_code == 200
            finally:
                client.close()
            assert len(direct_requests) == 2
            assert proxy_requests == []


def test_unreachable_proxy_fails_without_direct_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_proxy_environment(monkeypatch)
    with _http_server() as (base_url, direct_requests):
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
        client = make_openai_client("synthetic", base_url, timeout=0.2)
        try:
            with pytest.raises(APIConnectionError):
                _get(client)
        finally:
            client.close()
    assert direct_requests == []
