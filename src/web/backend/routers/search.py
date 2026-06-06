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


@router.get("/search/")
def search(searchValue: str = Query(...)):
    spotify = _get_spotify()
    result = spotify.search(q='track:' + searchValue)

    tracks = []
    for track in result['tracks']['items']:
        tracks.append({
            'title': track['name'],
            'artists': [a['name'] for a in track['artists']],
            'id': track['id'],
        })

    return {'type': 'searchSongs', 'tracks': tracks}
