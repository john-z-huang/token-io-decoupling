"""Optional SDK client construction for bounded output templates."""

import httpx2
from openai import DefaultHttpx2Client, OpenAI


def make_openai_client(api_key: str, base_url: str, *, timeout: float) -> OpenAI:
    """Build an OpenAI client that honors the process HTTP proxy environment."""
    http_client: httpx2.Client = DefaultHttpx2Client(trust_env=True, timeout=timeout)
    try:
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,
            http_client=http_client,
        )
    except BaseException:
        http_client.close()
        raise
