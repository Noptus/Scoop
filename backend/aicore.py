"""
Scoop - SAP AI Core client

Handles OAuth2 authentication and provides async helpers
for calling models deployed on SAP AI Core (Perplexity Sonar,
GPT-4o-mini, Claude, etc.).
"""

from __future__ import annotations

import logging
import os
import time
from base64 import b64encode

import httpx

from exceptions import APIError, ConfigError

logger = logging.getLogger(__name__)

# ── Token cache ──────────────────────────────

_token_cache: dict = {}


async def _get_token() -> str:
    """Get a cached OAuth2 token, refreshing if expired."""
    now = time.time()
    if _token_cache.get("token") and now < _token_cache.get("expires_at", 0):
        return _token_cache["token"]

    auth_url = os.getenv("SAP_AICORE_AUTH_URL", "")
    client_id = os.getenv("SAP_AICORE_CLIENT_ID", "")
    client_secret = os.getenv("SAP_AICORE_CLIENT_SECRET", "")

    if not all([auth_url, client_id, client_secret]):
        raise ConfigError(
            "SAP AI Core credentials not set. "
            "Need SAP_AICORE_AUTH_URL, SAP_AICORE_CLIENT_ID, SAP_AICORE_CLIENT_SECRET"
        )

    credentials = b64encode(f"{client_id}:{client_secret}".encode()).decode()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            auth_url,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data="grant_type=client_credentials",
        )
        if resp.status_code != 200:
            raise ConfigError(f"AI Core token request failed: {resp.status_code} {resp.text[:200]}")
        data = resp.json()

    if "access_token" not in data:
        raise ConfigError(f"AI Core token response missing access_token: {str(data)[:200]}")
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + 11 * 3600  # 11-hour cache
    logger.info("AI Core token refreshed (expires in 11h)")
    return _token_cache["token"]


# ── API helpers ──────────────────────────────

BASE_URL = os.getenv(
    "SAP_AICORE_BASE_URL",
    "https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com",
)
RESOURCE_GROUP = os.getenv("SAP_AICORE_RESOURCE_GROUP", "default")


async def chat_completion(
    deployment_id: str,
    messages: list[dict],
    max_tokens: int = 700,
    temperature: float = 0.1,
    model: str | None = None,
) -> dict:
    """Call an OpenAI-compatible model via AI Core (Perplexity, GPT, etc.)."""
    token = await _get_token()
    url = f"{BASE_URL}/v2/inference/deployments/{deployment_id}/chat/completions"
    # OpenAI/Azure models need api-version param
    if model and model.startswith("gpt"):
        url += "?api-version=latest"

    body: dict = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    # Some AI Core deployments (Perplexity, GPT) require a model field
    if model:
        body["model"] = model

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "AI-Resource-Group": RESOURCE_GROUP,
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise APIError(
            f"AI Core deployment {deployment_id} returned {exc.response.status_code}: "
            f"{exc.response.text[:200]}"
        ) from exc
    except httpx.RequestError as exc:
        raise APIError(f"AI Core request failed: {exc}") from exc
