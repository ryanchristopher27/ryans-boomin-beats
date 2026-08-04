"""Per-request LLM credentials, read from headers.

Replaces the previous server-side session storage. Starlette's SessionMiddleware
signs its cookie but does not encrypt it, so the BYOK key was base64-readable to
anything holding the cookie; it also required `credentials: 'include'` plus a
single-origin CORS allowlist, which a native client cannot satisfy (no origin,
no cookie jar). Headers work identically for the web app and for iOS.
"""
from dataclasses import dataclass

from fastapi import Header, HTTPException

SUPPORTED_PROVIDERS = ('claude', 'openai', 'groq')

_NOT_CONNECTED = (
    'LLM not connected. Send X-LLM-Provider and X-LLM-Key headers '
    '(connect an AI account in the app first).'
)


@dataclass(frozen=True)
class LLMCredentials:
    provider: str
    api_key: str


def _normalize(provider: str | None, api_key: str | None) -> LLMCredentials:
    name = (provider or '').strip().lower()
    key = (api_key or '').strip()
    if name not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f'Unknown provider {name!r}. Expected one of: {", ".join(SUPPORTED_PROVIDERS)}.',
        )
    return LLMCredentials(provider=name, api_key=key)


def get_llm_credentials(
    x_llm_provider: str | None = Header(default=None),
    x_llm_key: str | None = Header(default=None),
) -> LLMCredentials:
    """Required credentials — 401 when absent. Use on LLM-only endpoints."""
    if not x_llm_provider or not x_llm_key:
        raise HTTPException(status_code=401, detail=_NOT_CONNECTED)
    return _normalize(x_llm_provider, x_llm_key)


def get_optional_llm_credentials(
    x_llm_provider: str | None = Header(default=None),
    x_llm_key: str | None = Header(default=None),
) -> LLMCredentials | None:
    """Optional credentials — None when absent, for endpoints that degrade
    gracefully without an LLM (the song profile still returns Last.fm data)."""
    if not x_llm_provider or not x_llm_key:
        return None
    return _normalize(x_llm_provider, x_llm_key)
