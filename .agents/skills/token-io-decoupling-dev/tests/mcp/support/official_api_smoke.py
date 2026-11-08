"""真实 API smoke 的环境前置条件、客户端契约与安全错误边界。"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import httpx2
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from token_io_decoupling_workflow.openai_client import make_openai_client


def official_environment() -> tuple[str, str]:
    """仅由已获 opt-in 的测试调用，不在导入或测试收集时读取凭据。"""
    missing = [
        name
        for name in ("OPENAI_API_KEY_OFFICAL", "OPENAI_BASE_URL_OFFICAL")
        if not os.environ.get(name, "").strip()
    ]
    if missing:
        pytest.fail(
            f"required environment variable(s) are missing: {', '.join(missing)}",
            pytrace=False,
        )

    api_key = os.environ["OPENAI_API_KEY_OFFICAL"]
    base_url = os.environ["OPENAI_BASE_URL_OFFICAL"]
    return api_key, base_url


@contextmanager
def official_client(api_key: str, base_url: str) -> Iterator[OpenAI]:
    """只报告安全的错误类别，并关闭已成功创建的客户端。"""
    client = None
    try:
        client = make_openai_client(api_key, base_url, timeout=60.0)
        yield client
    except APIStatusError as exc:
        pytest.fail(f"the official API returned HTTP status {exc.status_code}", pytrace=False)
    except APITimeoutError:
        pytest.fail("the official API request timed out", pytrace=False)
    except APIConnectionError:
        pytest.fail("the official API connection failed", pytrace=False)
    except Exception as exc:
        pytest.fail(f"the official API smoke test failed with {type(exc).__name__}", pytrace=False)
    finally:
        if client is not None:
            client.close()


def validate_official_client(client: OpenAI) -> None:
    """检查客户端保持 HTTPX2 环境代理和零自动重试约束。"""
    if not isinstance(client._client, httpx2.Client) or client._client._trust_env is not True:
        pytest.fail(
            "the configured OpenAI client is not an environment-aware HTTPX2 client",
            pytrace=False,
        )
    if client.max_retries != 0:
        pytest.fail(
            "the configured OpenAI client does not have zero automatic retries",
            pytrace=False,
        )
