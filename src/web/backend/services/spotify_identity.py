"""Which Spotify user a bearer token belongs to (SY1).

Sync rows are keyed by Spotify user id, so this is the access check: a client
can only ever reach the row of the account its token is for. Cached by a hash
of the token (the raw token is never stored or logged).

The TTL also bounds how long an *expired* token keeps working for sync, because
sync routes never call Spotify again once the id is cached. Spotify doesn't
expose a token's expiry, so keep it short (review W1: 50 minutes let a token
outlive its own expiry by about that much).
"""
import hashlib
import time

import requests
from fastapi import Depends, HTTPException
from spotipy import SpotifyException

from services.spotify_auth import get_spotify_token
from services.spotify_client import user_client

_TTL = 5 * 60
_MAX = 1000
_cache: dict[str, tuple[str, float]] = {}


def user_id(token: str) -> str:
    key = hashlib.sha256(token.encode()).hexdigest()
    hit = _cache.get(key)
    if hit and hit[1] > time.monotonic():
        return hit[0]
    try:
        uid = user_client(token).me()['id']
    except SpotifyException as e:
        if e.http_status == 401:
            raise HTTPException(status_code=401, detail='Spotify session expired. Log in again.')
        raise HTTPException(status_code=503, detail="Couldn't reach Spotify. Try again in a moment.")
    except (requests.exceptions.RequestException, TimeoutError, ConnectionError):
        # Not SpotifyExceptions: without this a slow /me escaped dj_status and
        # failed the whole player poll (review W2).
        raise HTTPException(status_code=503, detail="Couldn't reach Spotify. Try again in a moment.")
    if len(_cache) >= _MAX:
        _cache.clear()
    _cache[key] = (uid, time.monotonic() + _TTL)
    return uid


def current_user(token: str = Depends(get_spotify_token)) -> str:
    return user_id(token)
