import asyncio

from spotipy import Spotify

from services import track_cache
from services.spotify_client import app_client, search


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


# Search results by (title, artist, fallback), misses included, for the life of
# the process. Spotify's Development Mode search quota is small and app-wide: a
# DJ testing burst (20-50 searches per suggestion call) earned a ~23h 429 (DJ4
# result). Errors raise before anything is stored, so a 429 is never cached.
# Ceiling: cleared wholesale at _CACHE_MAX; an LRU would keep hot entries.
_CACHE: dict[tuple[str, str, bool], dict | None] = {}
_CACHE_MAX = 5000


def _search_one(spotify: Spotify, title: str, artist: str, fallback: bool = True) -> dict | None:
    key = (title.casefold(), artist.casefold(), fallback)
    if key in _CACHE:
        return _CACHE[key]

    # Pass 1: strict — title + artist
    result = search(spotify, purpose='validate', q=f'track:{title} artist:{artist}', limit=1, type='track')
    items = result['tracks']['items']
    track = _format_track(items[0]) if items else None

    # Pass 2: loose — title only. Callers that reject other artists' songs
    # anyway (the DJ) pass fallback=False and save the search.
    if track is None and fallback:
        result = search(spotify, purpose='validate:fallback', q=f'track:{title}', limit=1, type='track')
        items = result['tracks']['items']
        track = _format_track(items[0]) if items else None

    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = track
    return track


# Searches in flight at once. Spotify also rate-limits over a rolling 30s
# window, and firing a whole suggestion round (20+ searches) at once invites it.
_MAX_CONCURRENT = 4


async def validate_songs(suggestions: list[dict], fallback: bool = True) -> tuple[list[dict], list[dict]]:
    """Look each suggestion up on Spotify, cheapest source first: this process's
    cache, then the shared Supabase cache (services/track_cache.py), then a
    search. New results go back to the shared cache for every other instance."""
    resolved: dict[tuple[str, str, bool], dict | None] = {}
    pending = {}
    for s in suggestions:
        k = (s['title'].casefold(), s['artist'].casefold(), fallback)
        if k in _CACHE:
            resolved[k] = _CACHE[k]
        else:
            pending[k] = s
    if pending:
        digests = {k: track_cache.key(s['title'], s['artist'], fallback) for k, s in pending.items()}
        shared = await asyncio.to_thread(track_cache.get_many, list(set(digests.values())))
        for k, d in digests.items():
            if d in shared:
                resolved[k] = _CACHE[k] = shared[d]
        to_search = {k: s for k, s in pending.items() if k not in resolved}
        if to_search:
            spotify = await asyncio.to_thread(app_client)
            gate = asyncio.Semaphore(_MAX_CONCURRENT)

            async def search_one(s: dict):
                async with gate:
                    return await asyncio.to_thread(_search_one, spotify, s['title'], s['artist'], fallback)

            found = await asyncio.gather(*[search_one(s) for s in to_search.values()], return_exceptions=True)
            fresh = {}
            for k, t in zip(to_search, found):
                if not isinstance(t, BaseException):
                    resolved[k] = t
                    fresh[digests[k]] = t
            await asyncio.to_thread(track_cache.put_many, fresh)
            # A 429 (or other failure) still fails the call, after saving what did come back.
            errors = [t for t in found if isinstance(t, BaseException)]
            if errors:
                raise errors[0]

    matched, failed = [], []
    for s in suggestions:
        track = resolved.get((s['title'].casefold(), s['artist'].casefold(), fallback))
        if track:
            matched.append({
                'title': s['title'],
                'artist': s['artist'],
                'reason': s.get('reason', ''),
                'spotify': track,
            })
        else:
            failed.append(s)

    return matched, failed
