from fastapi import APIRouter, Query
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from config import CLIENT_ID, CLIENT_SECRET

router = APIRouter()


def _get_spotify() -> Spotify:
    return Spotify(auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    ))


@router.get("/get-recommendations/")
def get_recommendations(trackId: str = Query(...), numberOfSongs: int = Query(25)):
    spotify = _get_spotify()
    result = spotify.recommendations(seed_tracks=[trackId], limit=numberOfSongs)

    tracks = []
    for track in result['tracks']:
        tracks.append({
            'title': track['name'],
            'artists': [a['name'] for a in track['artists']],
            'id': track['id'],
            'image': track['album']['images'][2]['url'],
            'image_size': track['album']['images'][2]['height'],
            'duration_ms': track['duration_ms'],
            'explicit': track['explicit'],
            'track_url': track['external_urls']['spotify'],
            'album': track['album']['name'],
        })

    return {'type': 'recommendations', 'tracks': tracks}
