import asyncio
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from config import CLIENT_ID, CLIENT_SECRET


def _get_spotify() -> Spotify:
    return Spotify(auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    ))


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
    }


def _search_one(spotify: Spotify, title: str, artist: str) -> dict | None:
    # Pass 1: strict — title + artist
    result = spotify.search(q=f'track:{title} artist:{artist}', limit=1, type='track')
    items = result['tracks']['items']
    if items:
        return _format_track(items[0])

    # Pass 2: loose — title only
    result = spotify.search(q=f'track:{title}', limit=1, type='track')
    items = result['tracks']['items']
    if items:
        return _format_track(items[0])

    return None


async def validate_songs(suggestions: list[dict]) -> tuple[list[dict], list[dict]]:
    spotify = await asyncio.to_thread(_get_spotify)

    async def check(suggestion: dict):
        track = await asyncio.to_thread(_search_one, spotify, suggestion['title'], suggestion['artist'])
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
