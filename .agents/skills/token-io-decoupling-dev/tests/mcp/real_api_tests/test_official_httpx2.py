"""Explicit opt-in smoke test for the official HTTPX2 client path."""

from __future__ import annotations

import logging
import os
from typing import Any, cast

import httpx2
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError

from token_io_decoupling_workflow.openai_client import make_openai_client

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
    missing = [
        name
        for name in ("OPENAI_API_KEY_OFFICAL", "OPENAI_BASE_URL_OFFICAL")
        if not os.environ.get(name, "").strip()
    ]
    if missing:
        cast(Any, pytest).fail(
            f"required environment variable(s) are missing: {', '.join(missing)}",
            pytrace=False,
        )

    api_key = os.environ["OPENAI_API_KEY_OFFICAL"]
    base_url = os.environ["OPENAI_BASE_URL_OFFICAL"]
    client = None
    try:
        client = make_openai_client(api_key, base_url, timeout=60.0)
        if not isinstance(client._client, httpx2.Client) or client._client._trust_env is not True:
            cast(Any, pytest).fail(
                "the configured OpenAI client is not an environment-aware HTTPX2 client",
                pytrace=False,
            )
        if client.max_retries != 0:
            cast(Any, pytest).fail(
                "the configured OpenAI client does not have zero automatic retries",
                pytrace=False,
            )

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
            cast(Any, pytest).fail(
                "the official API response did not complete",
                pytrace=False,
            )
        if not response.output_text.strip():
            cast(Any, pytest).fail(
                "the official API response contained no output text",
                pytrace=False,
            )
    except APIStatusError as exc:
        cast(Any, pytest).fail(
            f"the official API returned HTTP status {exc.status_code}",
            pytrace=False,
        )
    except APITimeoutError:
        cast(Any, pytest).fail("the official API request timed out", pytrace=False)
    except APIConnectionError:
        cast(Any, pytest).fail("the official API connection failed", pytrace=False)
    except Exception as exc:
        cast(Any, pytest).fail(
            f"the official API smoke test failed with {type(exc).__name__}",
            pytrace=False,
        )
    finally:
        if client is not None:
            client.close()

    print(
        "Official API smoke test: model=gpt-6-luna status=completed "
        f"proxy_selected={proxy_selected}"
    )
