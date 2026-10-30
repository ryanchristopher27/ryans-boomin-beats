"""Artist genres for Profile. Spotify's `genres` is deprecated and comes back
empty for every artist in this app (checked 2026-10-29), so empty ones are
filled from Last.fm tags, cached in `track_lookup` for 30 days under a
`lastfm-tags` key (one Last.fm call per artist a month, not per Profile load)."""
import asyncio

from services import lastfm_client, track_cache

_PARALLEL = 8


async def fill_genres(artists: list[dict]) -> None:
    """Set `genres` on artists that have none (in place)."""
    empty = [a for a in artists if not a.get('genres') and a.get('name')]
    if not empty:
        return
    keys = {a['name']: track_cache.key('lastfm-tags', a['name']) for a in empty}
    cached = await asyncio.to_thread(track_cache.get_many, list(set(keys.values())))
    todo = sorted({a['name'] for a in empty if keys[a['name']] not in cached})
    gate = asyncio.Semaphore(_PARALLEL)

    async def fetch(name):
        async with gate:
            return name, await lastfm_client.artist_top_tags(name)

    fetched = dict(await asyncio.gather(*(fetch(n) for n in todo)))
    # A failed call (None) isn't cached, so it's retried next time.
    fresh = {keys[n]: {'tags': tags} for n, tags in fetched.items() if tags is not None}
    if fresh:
        await asyncio.to_thread(track_cache.put_many, fresh)
    for a in empty:
        hit = cached.get(keys[a['name']]) or fresh.get(keys[a['name']])
        # Re-filtered, so a tag added to the not-a-genre list drops out of cached rows too.
        a['genres'] = [t for t in (hit or {}).get('tags', []) if lastfm_client.is_genre_tag(t)]
