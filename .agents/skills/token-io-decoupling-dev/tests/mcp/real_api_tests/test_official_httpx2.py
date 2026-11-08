"""Explicit opt-in smoke test for the official HTTPX2 client path."""

from __future__ import annotations

import logging
import os

import httpx2
import pytest
from support.official_api_smoke import (
    official_client,
    official_environment,
    validate_official_client,
)

_OPT_IN_NAME = "TOKEN_IO_RUN_OFFICIAL_API"
_OPTED_IN = os.environ.get(_OPT_IN_NAME) == "1"

pytestmark = [
    pytest.mark.real_api,
    pytest.mark.skipif(
        not _OPTED_IN,
        reason=f"set {_OPT_IN_NAME}=1 to enable the official API smoke test",
    ),
]


@pytest.fixture(autouse=True)
def suppress_provider_logs():
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(previous_disable)


def test_official_openai_api_uses_httpx2_environment_proxy() -> None:
    api_key, base_url = official_environment()
    with official_client(api_key, base_url) as client:
        validate_official_client(client)
        base_url_for_route = httpx2.URL(str(client.base_url))
        proxy_selected = (
            client._client._transport_for_url(base_url_for_route) is not client._client._transport
        )
        response = client.responses.create(
            model="gpt-6-luna",
            input="Reply with OK.",
            reasoning={"effort": "none"},
            max_output_tokens=64,
            store=False,
        )
        if response.status != "completed":
            pytest.fail(
                "the official API response did not complete",
                pytrace=False,
            )
        if not response.output_text.strip():
            pytest.fail(
                "the official API response contained no output text",
                pytrace=False,
            )
    print(
        "Official API smoke test: model=gpt-6-luna status=completed "
        f"proxy_selected={proxy_selected}"
    )
