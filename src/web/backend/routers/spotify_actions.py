from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from spotipy import Spotify, SpotifyException

router = APIRouter()


class CreatePlaylistRequest(BaseModel):
    name: str
    track_ids: list[str]
    access_token: Optional[str] = None


class QueueRequest(BaseModel):
    track_ids: list[str]
    access_token: Optional[str] = None


class AddToPlaylistRequest(BaseModel):
    playlist_id: str
    track_ids: list[str]
    access_token: Optional[str] = None


class SaveTrackRequest(BaseModel):
    track_ids: list[str]
    remove: bool = False
    access_token: Optional[str] = None


@router.post("/spotify/create-playlist/")
def create_playlist(body: CreatePlaylistRequest):
    if not body.access_token:
        raise HTTPException(status_code=401, detail="Log in to Spotify on the Profile page first.")
    spotify = Spotify(auth=body.access_token)
    playlist = spotify._post("me/playlists", payload={"name": body.name, "public": False, "description": "Created by Boomin Beats"})
    if body.track_ids:
        spotify.playlist_add_items(playlist['id'], body.track_ids)
    return {
        'playlist_url': playlist['external_urls']['spotify'],
        'playlist_id': playlist['id'],
    }


@router.get("/spotify/playlists/")
def list_playlists(access_token: Optional[str] = Query(default=None)):
    """List the user's editable playlists (owned or collaborative)."""
    if not access_token:
        raise HTTPException(status_code=401, detail="Log in to Spotify on the Profile page first.")
    spotify = Spotify(auth=access_token)
    me_id = spotify.me()['id']

    playlists = []
    offset = 0
    while True:
        page = spotify.current_user_playlists(limit=50, offset=offset)
        items = page.get('items', [])
        for p in items:
            if p is None:
                continue
            owned = p.get('owner', {}).get('id') == me_id
            if not (owned or p.get('collaborative')):
                continue
            images = p.get('images') or []
            # Spotify's /me/playlists returns the track ref under "items" (newer)
            # or "tracks" (older) — both are {href, total}.
            tracks_ref = p.get('items') or p.get('tracks') or {}
            track_count = tracks_ref.get('total', 0) if isinstance(tracks_ref, dict) else 0
            playlists.append({
                'id': p['id'],
                'name': p['name'],
                'image': images[0]['url'] if images else '',
                'track_count': track_count,
            })
        if page.get('next'):
            offset += 50
        else:
            break

    return {'playlists': playlists}


@router.post("/spotify/add-to-playlist/")
def add_to_playlist(body: AddToPlaylistRequest):
    if not body.access_token:
        raise HTTPException(status_code=401, detail="Log in to Spotify on the Profile page first.")
    if not body.track_ids:
        return {'added': 0}
    spotify = Spotify(auth=body.access_token)
    spotify.playlist_add_items(body.playlist_id, body.track_ids)
    return {
        'added': len(body.track_ids),
        'playlist_url': f'https://open.spotify.com/playlist/{body.playlist_id}',
    }


@router.get("/spotify/top-tracks/")
def top_tracks(
    access_token: Optional[str] = Query(default=None),
    limit: int = Query(default=12),
    time_range: str = Query(default='medium_term'),
):
    if not access_token:
        raise HTTPException(status_code=401, detail="Log in to Spotify on the Profile page first.")
    spotify = Spotify(auth=access_token)
    result = spotify.current_user_top_tracks(limit=limit, time_range=time_range)
    tracks = []
    for t in result.get('items', []):
        images = t['album']['images']
        image = images[-1]['url'] if images else ''
        tracks.append({
            'title': t['name'],
            'artists': [a['name'] for a in t['artists']],
            'id': t['id'],
            'image': image,
        })
    return {'tracks': tracks}


@router.post("/spotify/save-track/")
def save_track(body: SaveTrackRequest):
    if not body.access_token:
        raise HTTPException(status_code=401, detail="Log in to Spotify on the Profile page first.")
    if not body.track_ids:
        return {'ok': True, 'saved': not body.remove}
    spotify = Spotify(auth=body.access_token)
    try:
        if body.remove:
            spotify.current_user_saved_tracks_delete(tracks=body.track_ids)
        else:
            spotify.current_user_saved_tracks_add(tracks=body.track_ids)
    except SpotifyException as e:
        if e.http_status in (401, 403):
            raise HTTPException(status_code=403, detail="reconnect")
        raise HTTPException(status_code=500, detail=str(e))
    return {'ok': True, 'saved': not body.remove}


@router.get("/spotify/saved-contains/")
def saved_contains(access_token: Optional[str] = Query(default=None), ids: str = Query(default="")):
    if not access_token:
        raise HTTPException(status_code=401, detail="Log in to Spotify on the Profile page first.")
    id_list = [i for i in ids.split(',') if i]
    if not id_list:
        return {'saved': {}}
    spotify = Spotify(auth=access_token)
    try:
        flags = spotify.current_user_saved_tracks_contains(tracks=id_list)
    except SpotifyException as e:
        if e.http_status in (401, 403):
            raise HTTPException(status_code=403, detail="reconnect")
        raise HTTPException(status_code=500, detail=str(e))
    return {'saved': dict(zip(id_list, flags))}


@router.post("/spotify/queue/")
def queue_songs(body: QueueRequest):
    if not body.access_token:
        raise HTTPException(status_code=401, detail="Log in to Spotify on the Profile page first.")
    spotify = Spotify(auth=body.access_token)
    try:
        for track_id in body.track_ids:
            spotify.add_to_queue(f'spotify:track:{track_id}')
        return {'queued': len(body.track_ids)}
    except Exception as e:
        error_str = str(e)
        if 'NO_ACTIVE_DEVICE' in error_str or 'Player command failed' in error_str:
            return {'error': 'no_active_device'}
        raise HTTPException(status_code=500, detail=error_str)
