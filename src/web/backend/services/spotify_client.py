"""Spotify client construction, in one place.

Previously every route built `Spotify(auth=token)` inline — twelve sites — so
there was nowhere to set a timeout, tune retries, or add a header without
editing all of them.

The concrete failure that motivated this: a uvicorn process left running for
three days accumulated dead pooled TCP connections (laptop sleep / network
change). Reads against them hung until spotipy's 5s default expired, and the
resulting bare `TimeoutError` is NOT a SpotifyException, so it sailed past every
`except SpotifyException` handler and became a 500 with a raw traceback.
"""
import logging
import time

import requests
from requests.adapters import HTTPAdapter
from spotipy import Spotify, SpotifyException
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyClientCredentials
from urllib3.util.retry import Retry

from config import CLIENT_ID, CLIENT_SECRET

log = logging.getLogger(__name__)

# Longer than spotipy's 5s default: several routes paginate (all playlists) or
# fan out across timeframes, and a slow-but-alive Spotify shouldn't fail the
# whole request. Retries cover transient resets, including the stale-socket case.
REQUEST_TIMEOUT = 10
RETRIES = 3
# Retry real 5xx only. Spotify answered a dev-mode search burst with 429 +
# Retry-After: 82363 (~23h, DJ4 result), and urllib3 sleeps for Retry-After on
# 429 even when 429 is NOT in status_forcelist (Retry.is_retry honours the
# header independently). That parked worker threads for hours and hung every
# request that searched. spotipy doesn't expose respect_retry_after_header, so
# we hand it our own session: spotipy's policy, minus Retry-After.
STATUS_FORCELIST = (500, 502, 503, 504)


def _session() -> requests.Session:
    retry = Retry(
        total=RETRIES,
        connect=None,
        read=False,
        allowed_methods=frozenset(['GET', 'POST', 'PUT', 'DELETE']),
        status=RETRIES,
        backoff_factor=0.3,
        status_forcelist=STATUS_FORCELIST,
        respect_retry_after_header=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def user_client(token: str) -> Spotify:
    """Client acting as the signed-in user."""
    return Spotify(
        auth=token,
        requests_session=_session(),
        requests_timeout=REQUEST_TIMEOUT,
    )


# Shared across calls so the client-credentials token is reused until it
# expires instead of fetched per request. Process-lifetime, like any cache here.
_APP_TOKEN_CACHE = MemoryCacheHandler()


def app_client() -> Spotify:
    """Client-credentials client, for catalog reads that need no user context.

    The client secret lives here and must never reach a client app — which is
    why search and validation stay server-side (see the brainstorm).
    """
    return Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            # spotipy's default writes the app token to ./.cache. Vercel's
            # filesystem is read-only (SY2), and the file kept ending up in git.
            cache_handler=_APP_TOKEN_CACHE,
        ),
        requests_session=_session(),
        requests_timeout=REQUEST_TIMEOUT,
    )


# --- Search lockout -----------------------------------------------------------
# Spotify's search quota for Development Mode apps is daily and app-wide; once
# it's spent, every search 429s (reason QUOTA_EXCEEDED) until a reset hours
# away. Without this, each /dj/suggest/ still fired ~20 doomed searches while
# locked (seen in production 2026-10-25), and failed calls may count against
# the quota too. Per process: each serverless instance learns the lockout from
# its first 429. Capped so a bogus Retry-After can't lock search for days.
_MAX_LOCKOUT = 24 * 60 * 60
_search_locked_until = 0.0


def search_lockout_remaining() -> int:
    """Seconds until search is worth trying again (0 = not locked)."""
    return max(0, int(_search_locked_until - time.monotonic()))


# Real Spotify searches this process has made (plan Q4 measures quota use with
# it; each is also logged, so Vercel's logs count across instances).
searches_made = 0


def search(spotify: Spotify, purpose: str = '', **kwargs) -> dict:
    """spotify.search(), but skipped entirely while Spotify has us locked out.

    Raises the same SpotifyException 429 a real lockout does, so callers and
    main.py's 429 -> 503 handler behave identically either way."""
    global _search_locked_until
    remaining = search_lockout_remaining()
    if remaining:
        raise SpotifyException(429, -1, 'Spotify search is rate-limited',
                               reason='LOCAL_LOCKOUT', headers={'Retry-After': str(remaining)})
    global searches_made
    searches_made += 1
    log.info('[spotify] search #%d %s', searches_made, purpose or '-')
    try:
        return spotify.search(**kwargs)
    except SpotifyException as e:
        if e.http_status == 429:
            try:
                retry_after = int((e.headers or {}).get('Retry-After', 60))
            except (TypeError, ValueError):
                retry_after = 60
            _search_locked_until = time.monotonic() + min(max(retry_after, 1), _MAX_LOCKOUT)
            log.warning('[spotify] search locked out for %ss (%s)', retry_after, e.reason)
        raise
