import hmac
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import ALLOWED_ORIGINS, DEVICE_KEY
from routers import search, profile
from routers import llm_connect, llm_playlist, spotify_actions, song_profile

log = logging.getLogger(__name__)

app = FastAPI(title="Boomin Beats API")

# No SessionMiddleware: LLM credentials travel per request as
# X-LLM-Provider / X-LLM-Key headers (services/llm_auth.py).

# Paths reachable without a device key, so a host's uptime probe still works.
_UNGUARDED_PATHS = {'/'}


# Registered BEFORE CORSMiddleware on purpose. add_middleware() inserts at the
# front and the stack is built outermost-first, so the LAST middleware added is
# the outermost — adding CORS last keeps it wrapping this one, and a 401 from
# here still carries CORS headers. Registering it the other way round reproduces
# the "CORS error masking the real status" problem from the 2026-06-05 reflect.
@app.middleware("http")
async def require_device_key(request: Request, call_next):
    """Guard the hosted instance with a shared secret.

    No-op when DEVICE_KEY is unset, which is the local instance's configuration.
    Not user authentication — it exists so a public URL can't be used by anyone
    who finds it to burn the Spotify client-credentials quota.
    """
    if not DEVICE_KEY:
        return await call_next(request)

    # Preflight carries no custom headers; CORSMiddleware answers it upstream.
    if request.method == 'OPTIONS' or request.url.path in _UNGUARDED_PATHS:
        return await call_next(request)

    presented = request.headers.get('x-device-key', '')
    if not hmac.compare_digest(presented, DEVICE_KEY):
        log.warning(
            '[device-key] rejected %s %s from %s',
            request.method, request.url.path,
            request.client.host if request.client else 'unknown',
        )
        return JSONResponse(status_code=401, content={'detail': 'Missing or invalid X-Device-Key.'})

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # No cookies cross the boundary any more, so credentialed CORS is not needed.
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Keep CORS headers on 500s so the browser reports the real error instead of
    # a misleading CORS failure (2026-06-05 reflect). Credentials flag dropped
    # along with SessionMiddleware — no cookies are involved any more.
    origin = request.headers.get("origin", "")
    log.exception('[unhandled] %s %s', request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": origin},
    )


app.include_router(search.router)
app.include_router(profile.router)
app.include_router(llm_connect.router)
app.include_router(llm_playlist.router)
app.include_router(spotify_actions.router)
app.include_router(song_profile.router)
