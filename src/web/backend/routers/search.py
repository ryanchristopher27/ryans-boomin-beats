from fastapi import APIRouter, Query

from services.spotify_client import app_client, search as guarded_search

router = APIRouter()


@router.get("/search/")
def search(searchValue: str = Query(...)):
    spotify = app_client()
    result = guarded_search(spotify, purpose='typeahead', q='track:' + searchValue)

    tracks = []
    for track in result['tracks']['items']:
        images = track['album']['images']
        image = images[-1]['url'] if images else ''
        tracks.append({
            'title': track['name'],
            'artists': [a['name'] for a in track['artists']],
            'id': track['id'],
            'album': track['album']['name'],
            'image': image,
        })

    return {'type': 'searchSongs', 'tracks': tracks}
