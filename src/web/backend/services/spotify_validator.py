import asyncio

from spotipy import Spotify

from services.spotify_client import app_client


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
    result = spotify.search(q=f'track:{title} artist:{artist}', limit=1, type='track')
    items = result['tracks']['items']
    track = _format_track(items[0]) if items else None

    # Pass 2: loose — title only. Callers that reject other artists' songs
    # anyway (the DJ) pass fallback=False and save the search.
    if track is None and fallback:
        result = spotify.search(q=f'track:{title}', limit=1, type='track')
        items = result['tracks']['items']
        track = _format_track(items[0]) if items else None

    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = track
    return track


async def validate_songs(suggestions: list[dict], fallback: bool = True) -> tuple[list[dict], list[dict]]:
    spotify = await asyncio.to_thread(app_client)

    async def check(suggestion: dict):
        track = await asyncio.to_thread(_search_one, spotify, suggestion['title'], suggestion['artist'], fallback)
        return suggestion, track

    results = await asyncio.gather(*[check(s) for s in suggestions])

    matched, failed = [], []
    for suggestion, track in results:
        if track:
            matched.append({
                'title': suggestion['title'],
                'artist': suggestion['artist'],
                'reason': suggestion.get('reason', ''),
                'spotify': track,
            })
        else:
            failed.append(suggestion)

    return matched, failed
