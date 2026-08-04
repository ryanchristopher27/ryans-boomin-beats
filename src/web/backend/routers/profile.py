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
        # Spotify usually returns 3 image sizes but does not guarantee it; the
        # rest of the codebase guards this and an unguarded [2] is a 500 waiting
        # for the first album art with fewer sizes.
        images = track['album'].get('images') or []
        thumb = images[2] if len(images) > 2 else (images[-1] if images else {})
        top_tracks_objects.append({
            'title': track['name'],
            'artists': [a['name'] for a in track['artists']],
            'id': track['id'],
            'image': thumb.get('url', ''),
            'image_size': thumb.get('height', 0),
            'duration_ms': track['duration_ms'],
            'explicit': track['explicit'],
            'track_url': track['external_urls']['spotify'],
            'album': track['album']['name'],
            'release_date': track['album'].get('release_date', ''),
        })

    return {
        'type': 'get_profile',
        'profile': current_user,
        'top_artists': top_artists_objects,
        'top_tracks': top_tracks_objects,
    }
