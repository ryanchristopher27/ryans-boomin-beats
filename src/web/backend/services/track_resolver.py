"""Turn a chosen song into a playable Spotify track (plan Q1): the one place
Spotify search is spent once showing songs moves to Deezer.

By ISRC first: one exact search (`isrc:`), no title guessing, so no
wrong-artist matches. Title + artist search only when a song has no ISRC.
Searches use the app's client credentials and a fixed market (SPOTIFY_MARKET,
default US): `market=from_token` needs the user-read-private scope, which the
apps don't request (Q4 live check: 403). Ceiling: a friend in another country
could get a version that isn't playable for them; per-user markets would need
that scope (and everyone signing in again).
"""
import asyncio

from services import track_cache
from services.deezer import _VARIANTS
from config import SPOTIFY_MARKET
from services.spotify_client import app_client, search

_MAX_CONCURRENT = 4
_CACHE: dict[str, dict | None] = {}
_CACHE_MAX = 5000


def _format_track(track: dict) -> dict:
    images = track['album']['images']
    image = images[2]['url'] if len(images) > 2 else (images[0]['url'] if images else '')
    return {
        'id': track['id'],
        'title': track['name'],
        'artists': [a['name'] for a in track['artists']],
        'album': track['album']['name'],
        'image': image,
        'track_url': track['external_urls']['spotify'],
        'duration_ms': track['duration_ms'],
        'explicit': track.get('explicit', False),
    }


def _is_reupload(t: dict, wanted_title: str) -> bool:
    """Sped-up/slowed re-releases can share the original's ISRC (Q0 spike: the
    only 'single' under September's ISRC was a "sped up + slowed" release)."""
    names = f"{t.get('name', '')} {(t.get('album') or {}).get('name', '')}".casefold()
    return any(v in names and v not in wanted_title.casefold() for v in _VARIANTS)


def _pick(items: list[dict], wanted_title: str = '') -> dict | None:
    """Of the tracks sharing an ISRC, the playable one from the artist's album,
    else a single, else a compilation. Spotify lists compilations first (Q0
    spike: Redbone's album came 8th), so order matters."""
    ok = [t for t in items if t.get('is_playable', True) and not _is_reupload(t, wanted_title)]
    for kind in ('album', 'single', 'compilation'):
        for t in ok:
            if (t.get('album') or {}).get('album_type') == kind:
                return t
    return ok[0] if ok else None


def _lookup(spotify, song: dict) -> dict | None:
    if song.get('isrc'):
        items = search(spotify, purpose='resolve:isrc', q=f"isrc:{song['isrc']}", type='track', limit=10,
                       market=SPOTIFY_MARKET)['tracks']['items']
        hit = _pick(items, song.get('title', ''))
        if hit or not song.get('title'):
            return _format_track(hit) if hit else None
    # No ISRC (or none Spotify knows): one strict title + artist search.
    items = search(spotify, purpose='resolve:title', q=f"track:{song['title']} artist:{song['artist']}",
                   type='track', limit=5, market=SPOTIFY_MARKET)['tracks']['items']
    hit = _pick(items, song.get('title', ''))
    return _format_track(hit) if hit else None


def _key(song: dict) -> str:
    if song.get('isrc'):
        return track_cache.key('isrc', song['isrc'])
    return track_cache.key('resolve', song['title'], song['artist'])


async def resolve(songs: list[dict]) -> list[dict | None]:
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
            spotify = await asyncio.to_thread(app_client)
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
