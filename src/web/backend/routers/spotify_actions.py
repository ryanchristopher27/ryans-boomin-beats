from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from spotipy import Spotify

router = APIRouter()


class CreatePlaylistRequest(BaseModel):
    name: str
    track_ids: list[str]
    access_token: Optional[str] = None


class QueueRequest(BaseModel):
    track_ids: list[str]
    access_token: Optional[str] = None


@router.post("/spotify/create-playlist/")
def create_playlist(body: CreatePlaylistRequest):
    if not body.access_token:
        raise HTTPException(status_code=401, detail="Log in to Spotify on the Profile page first.")
    spotify = Spotify(auth=body.access_token)
    playlist = spotify._post("me/playlists", payload={"name": body.name, "public": False, "description": "Created by Boomin Beats"})
    spotify.playlist_add_items(playlist['id'], body.track_ids)
    return {
        'playlist_url': playlist['external_urls']['spotify'],
        'playlist_id': playlist['id'],
    }


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
