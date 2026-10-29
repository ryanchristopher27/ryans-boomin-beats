"""Per-request LLM credentials, read from headers.

Replaces the previous server-side session storage. Starlette's SessionMiddleware
signs its cookie but does not encrypt it, so the BYOK key was base64-readable to
anything holding the cookie; it also required `credentials: 'include'` plus a
single-origin CORS allowlist, which a native client cannot satisfy (no origin,
no cookie jar). Headers work identically for the web app and for iOS.
"""
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request

SUPPORTED_PROVIDERS = ('claude', 'openai', 'groq', 'claude-code', 'helper')
# 'claude-code' runs the backend machine's CLI login (services/claude_code.py);
# 'helper' relays through the page to the user's own trip-fairy-helper
# (services/llm_client.NeedsLLM). Neither has a key.
KEYLESS = ('claude-code', 'helper')
# The relay's replies ride in the JSON body as `llm_replies`; a route makes at most a few calls.
MAX_REPLIES = 8
MAX_REPLY_CHARS = 64_000

_NOT_CONNECTED = (
    'LLM not connected. Send X-LLM-Provider and X-LLM-Key headers '
    '(connect an AI account in the app first).'
)


@dataclass(frozen=True)
class LLMCredentials:
    provider: str
    api_key: str
    replies: tuple[str, ...] = ()
    relay_error: str | None = None

    def client(self):
        from services.llm_client import LLMClient
        return LLMClient(self.provider, self.api_key, self.replies, self.relay_error)


def _normalize(provider: str | None, api_key: str | None) -> LLMCredentials:
    name = (provider or '').strip().lower()
    key = (api_key or '').strip()
    if name not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f'Unknown provider {name!r}. Expected one of: {", ".join(SUPPORTED_PROVIDERS)}.',
        )
    if name == 'claude-code':
        from services import claude_code
        if not claude_code.available():
            raise HTTPException(status_code=400, detail='Your Claude Code only works when the backend runs on your own Mac.')
    return LLMCredentials(provider=name, api_key=key)


def _present(provider: str | None, key: str | None) -> bool:
    return bool(provider) and (bool(key) or (provider or '').strip().lower() in KEYLESS)


async def _with_relay(request: Request, creds: LLMCredentials) -> LLMCredentials:
    """The relay's `llm_replies` (and `llm_error`, when the helper failed) from the JSON body."""
    if creds.provider != 'helper' or request.method != 'POST':
        return creds
    try:
        body = await request.json()  # cached: FastAPI already read it for the route's model
    except ValueError:
        return creds
    if not isinstance(body, dict):
        return creds
    replies = body.get('llm_replies') or []
    error = body.get('llm_error')
    if not isinstance(replies, list) or len(replies) > MAX_REPLIES or not all(isinstance(r, str) and len(r) <= MAX_REPLY_CHARS for r in replies):
        raise HTTPException(status_code=400, detail='llm_replies must be a short list of strings.')
    if error is not None and not (isinstance(error, str) and len(error) <= 500):
        raise HTTPException(status_code=400, detail='llm_error must be a short string.')
    return LLMCredentials(creds.provider, creds.api_key, tuple(replies), error or None)


async def get_llm_credentials(
    request: Request,
    x_llm_provider: str | None = Header(default=None),
    x_llm_key: str | None = Header(default=None),
) -> LLMCredentials:
    """Required credentials — 401 when absent. Use on LLM-only endpoints."""
    if not _present(x_llm_provider, x_llm_key):
        raise HTTPException(status_code=401, detail=_NOT_CONNECTED)
    return await _with_relay(request, _normalize(x_llm_provider, x_llm_key))


async def get_optional_llm_credentials(
    request: Request,
    x_llm_provider: str | None = Header(default=None),
    x_llm_key: str | None = Header(default=None),
) -> LLMCredentials | None:
    """Optional credentials — None when absent, for endpoints that degrade
    gracefully without an LLM (the song profile still returns Last.fm data)."""
    if not _present(x_llm_provider, x_llm_key):
        return None
    return await _with_relay(request, _normalize(x_llm_provider, x_llm_key))
