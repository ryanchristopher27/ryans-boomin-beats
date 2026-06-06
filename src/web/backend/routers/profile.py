from fastapi import APIRouter, Query
from spotipy import Spotify

router = APIRouter()


@router.get("/get-profile/")
def get_profile(
    access_token: str = Query(...),
    num_tops: int = Query(10),
    time_period: str = Query('short_term'),
):
    spotify = Spotify(auth=access_token)

    current_user = spotify.me()
    top_artists = spotify.current_user_top_artists(limit=num_tops, offset=0, time_range=time_period)
    top_tracks = spotify.current_user_top_tracks(limit=num_tops, offset=0, time_range=time_period)

    top_artists_objects = []
    for artist in top_artists['items']:
        top_artists_objects.append({
            'name': artist.get('name', ''),
            'id': artist.get('id', ''),
            'genres': artist.get('genres', []),
            'popularity': artist.get('popularity', 0),
            'images': artist.get('images', []),
            'url': artist.get('external_urls', {}).get('spotify', ''),
        })

    top_tracks_objects = []
    for track in top_tracks['items']:
        top_tracks_objects.append({
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

    return {
        'type': 'get_profile',
        'profile': current_user,
        'top_artists': top_artists_objects,
        'top_tracks': top_tracks_objects,
    }
