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

import requests
from requests.adapters import HTTPAdapter
from spotipy import Spotify
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


def app_client() -> Spotify:
    """Client-credentials client, for catalog reads that need no user context.

    The client secret lives here and must never reach a client app — which is
    why search and validation stay server-side (see the brainstorm).
    """
    return Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        ),
        requests_session=_session(),
        requests_timeout=REQUEST_TIMEOUT,
    )
