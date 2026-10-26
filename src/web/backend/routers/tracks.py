"""POST /tracks/resolve/: songs chosen from Deezer-backed lists (DJ picks,
search, playlists) become playable Spotify tracks (plan Q1)."""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from services import track_resolver
from services.spotify_auth import get_spotify_token

router = APIRouter()

_Text = Annotated[str, StringConstraints(max_length=300)]


class Song(BaseModel):
    model_config = ConfigDict(extra='forbid')
    isrc: Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9]{12}$')] | None = None
    title: _Text = ''
    artist: _Text = ''


class ResolveBody(BaseModel):
    # A playlist's "add all" is the biggest caller; cap it so one request can't
    # spend a large share of the day's search quota.
    songs: list[Song] = Field(..., min_length=1, max_length=50)


@router.post('/tracks/resolve/')
async def resolve(body: ResolveBody, token: str = Depends(get_spotify_token)):
    tracks = await track_resolver.resolve(token, [s.model_dump() for s in body.songs])
    return {'tracks': tracks}
