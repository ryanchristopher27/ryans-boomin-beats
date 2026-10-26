"""Turn a chosen song into a playable Spotify track (plan Q1): the one place
Spotify search is spent once showing songs moves to Deezer.

By ISRC first: one exact search (`isrc:`), no title guessing, so no
wrong-artist matches. Title + artist search only when a song has no ISRC.
Searches run as the user with `market=from_token`, so Spotify returns the
version playable in their country without needing the user-read-private scope.
Ceiling: the shared cache doesn't key on country, so a small circle spread
across countries could get a version unplayable for one of them.
"""
import asyncio

from services import track_cache
from services.spotify_client import search, user_client
from services.spotify_validator import _format_track

_MAX_CONCURRENT = 4
_CACHE: dict[str, dict | None] = {}
_CACHE_MAX = 5000


def _pick(items: list[dict]) -> dict | None:
    """Of the tracks sharing an ISRC (album, single, compilation, deluxe),
    the first playable one, preferring the artist's own releases."""
    playable = [t for t in items if t.get('is_playable', True)]
    for wanted in (('album', 'single'), ('compilation',)):
        for t in playable:
            if (t.get('album') or {}).get('album_type') in wanted:
                return t
    return playable[0] if playable else None


def _lookup(spotify, song: dict) -> dict | None:
    if song.get('isrc'):
        items = search(spotify, purpose='resolve:isrc', q=f"isrc:{song['isrc']}", type='track', limit=10,
                       market='from_token')['tracks']['items']
        hit = _pick(items)
        if hit or not song.get('title'):
            return _format_track(hit) if hit else None
    # No ISRC (or none Spotify knows): one strict title + artist search.
    items = search(spotify, purpose='resolve:title', q=f"track:{song['title']} artist:{song['artist']}",
                   type='track', limit=5, market='from_token')['tracks']['items']
    hit = _pick(items)
    return _format_track(hit) if hit else None


def _key(song: dict) -> str:
    if song.get('isrc'):
        return track_cache.key('isrc', song['isrc'])
    return track_cache.key('resolve', song['title'], song['artist'])


async def resolve(token: str, songs: list[dict]) -> list[dict | None]:
    """Spotify tracks for `[{isrc?, title, artist}]`, in order (None = not on Spotify)."""
    keys = [_key(s) for s in songs]
    resolved = {k: _CACHE[k] for k in keys if k in _CACHE}
    missing = [k for k in dict.fromkeys(keys) if k not in resolved]
    if missing:
        shared = await asyncio.to_thread(track_cache.get_many, missing)
        resolved.update(shared)
        _CACHE.update(shared)
        to_search = {k: s for k, s in zip(keys, songs) if k not in resolved}
        if to_search:
            spotify = user_client(token)
            gate = asyncio.Semaphore(_MAX_CONCURRENT)

            async def one(s):
                async with gate:
                    return await asyncio.to_thread(_lookup, spotify, s)

            found = await asyncio.gather(*[one(s) for s in to_search.values()], return_exceptions=True)
            fresh = {k: t for k, t in zip(to_search, found) if not isinstance(t, BaseException)}
            resolved.update(fresh)
            if len(_CACHE) >= _CACHE_MAX:
                _CACHE.clear()
            _CACHE.update(fresh)
            await asyncio.to_thread(track_cache.put_many, fresh)
            errors = [t for t in found if isinstance(t, BaseException)]
            if errors:
                raise errors[0]  # e.g. the 429 lockout -> 503, after saving what came back
    return [resolved.get(k) for k in keys]
