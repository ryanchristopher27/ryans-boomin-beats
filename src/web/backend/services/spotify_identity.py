"""Which Spotify user a bearer token belongs to (SY1).

Sync rows are keyed by Spotify user id, so this is the access check: a client
can only ever reach the row of the account its token is for. Cached by a hash
of the token (the raw token is never stored or logged) for slightly less than
a token's one-hour lifetime.
"""
import hashlib
import time

from fastapi import Depends, HTTPException
from spotipy import SpotifyException

from services.spotify_auth import get_spotify_token
from services.spotify_client import user_client

_TTL = 50 * 60
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
    if len(_cache) >= _MAX:
        _cache.clear()
    _cache[key] = (uid, time.monotonic() + _TTL)
    return uid


def current_user(token: str = Depends(get_spotify_token)) -> str:
    return user_id(token)
