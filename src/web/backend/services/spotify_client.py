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

from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from config import CLIENT_ID, CLIENT_SECRET

log = logging.getLogger(__name__)

# Longer than spotipy's 5s default: several routes paginate (all playlists) or
# fan out across timeframes, and a slow-but-alive Spotify shouldn't fail the
# whole request. Retries cover transient resets, including the stale-socket case.
REQUEST_TIMEOUT = 10
RETRIES = 3
def user_client(token: str) -> Spotify:
    """Client acting as the signed-in user."""
    return Spotify(
        auth=token,
        requests_timeout=REQUEST_TIMEOUT,
        retries=RETRIES,
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
        requests_timeout=REQUEST_TIMEOUT,
        retries=RETRIES,
    )
