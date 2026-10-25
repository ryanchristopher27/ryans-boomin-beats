"""Shared DJ state across devices (SY1).

One document per Spotify user: the queue, the DJ options, session feedback and
recent history. Jam-style roles: one primary device sends to Spotify, every
other device edits the same document. Writes are optimistic: send the version
you started from in If-Match; a 409 returns the current document to re-apply on.

Field names mirror the iOS models (QueueStore, DJSettings) so both clients map
them one to one.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from config import SYNC_ENABLED
from services.dj_store import Conflict, DJStore, Unavailable, primary_info
from services.spotify_identity import current_user

router = APIRouter()

_Text = Annotated[str, StringConstraints(max_length=300)]
_Id = Annotated[str, StringConstraints(max_length=64)]


class _Strict(BaseModel):
    # Reject unknown fields: a client/server field mismatch should fail loudly,
    # not be stored and silently ignored.
    model_config = ConfigDict(extra='forbid')


class TrackRef(_Strict):
    id: _Id
    title: _Text
    artists: list[_Text] = Field(default=[], max_length=20)
    image: Annotated[str, StringConstraints(max_length=500)] = ''


class QueueItem(_Strict):
    id: _Id
    trackID: _Id
    title: _Text
    artists: list[_Text] = Field(default=[], max_length=20)
    image: Annotated[str, StringConstraints(max_length=500)] = ''
    skipOnArrival: bool = False
    addedByDJ: bool | None = None


class GuestRequest(_Strict):
    id: _Id
    trackID: _Id
    title: _Text
    artists: list[_Text] = Field(default=[], max_length=20)
    image: Annotated[str, StringConstraints(max_length=500)] = ''


class Queue(_Strict):
    sent: list[QueueItem] = Field(default=[], max_length=200)
    upcoming: list[QueueItem] = Field(default=[], max_length=200)
    requests: list[GuestRequest] = Field(default=[], max_length=100)
    guestSkips: list[_Id] = Field(default=[], max_length=200)
    keptGuests: list[_Id] = Field(default=[], max_length=200)


class AvoidedTrack(_Strict):
    id: _Id
    title: _Text
    artist: _Text


class Goal(_Strict):
    kind: Literal['destination', 'arc', 'drift']
    destination: Annotated[str, StringConstraints(max_length=200)] = ''
    shape: Literal['build', 'wind_down', 'peak_cool'] = 'build'
    minutes: int = Field(default=30, ge=5, le=240)
    startedAt: Annotated[str, StringConstraints(max_length=40)]  # ISO 8601


class Options(_Strict):
    mode: Literal['whisper', 'copilot', 'autofill', 'driver'] = 'copilot'
    adventurousness: float = Field(default=0.5, ge=0, le=1)
    clean: bool = False
    goal: Goal | None = None
    avoidTracks: list[AvoidedTrack] = Field(default=[], max_length=500)
    avoidArtists: list[_Text] = Field(default=[], max_length=500)


class Feedback(_Strict):
    liked: list[TrackRef] = Field(default=[], max_length=50)
    disliked: list[TrackRef] = Field(default=[], max_length=50)
    skipped: list[TrackRef] = Field(default=[], max_length=50)


class DJStateDoc(_Strict):
    queue: Queue = Queue()
    options: Options = Options()
    feedback: Feedback = Feedback()
    recent: list[TrackRef] = Field(default=[], max_length=50)


class PutBody(_Strict):
    state: DJStateDoc


class ClaimBody(_Strict):
    device: _Id
    label: Annotated[str, StringConstraints(max_length=60)] = ''


_store: DJStore | None = None


def get_store() -> DJStore:
    if not SYNC_ENABLED:
        raise HTTPException(status_code=503, detail="Sync isn't configured on this server.")
    global _store
    if _store is None:
        _store = DJStore()
    return _store


def _doc(row: dict | None) -> dict:
    if not row:
        return {'version': 0, 'state': None, 'primary': None}
    return {'version': row['version'], 'state': row['state'], 'primary': primary_info(row)}


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail='Sync is unavailable right now. Changes stay on this device.')


@router.get('/dj/state')
def read_state(user: str = Depends(current_user), store: DJStore = Depends(get_store)):
    try:
        return _doc(store.read(user))
    except Unavailable:
        raise _unavailable()


@router.put('/dj/state')
def write_state(
    body: PutBody,
    if_match: int = Header(..., ge=0),
    x_dj_device: str | None = Header(default=None, max_length=64),
    x_dj_label: str | None = Header(default=None, max_length=60),
    user: str = Depends(current_user),
    store: DJStore = Depends(get_store),
):
    """If-Match: 0 creates the row (the first device seeds it and becomes
    primary); otherwise it's the version this edit was based on."""
    state = body.state.model_dump()
    try:
        if if_match == 0:
            row = store.create(user, state, x_dj_device, x_dj_label)
        else:
            row = store.update(user, state, if_match)
    except Conflict:
        try:
            current = store.read(user)
        except Unavailable:
            raise _unavailable()
        return JSONResponse(status_code=409, content=_doc(current))
    except Unavailable:
        raise _unavailable()
    return _doc(row)


@router.post('/dj/primary')
def claim_primary(body: ClaimBody, user: str = Depends(current_user), store: DJStore = Depends(get_store)):
    """Drive from here: always succeeds for an existing session."""
    try:
        row = store.claim_primary(user, body.device, body.label)
    except Unavailable:
        raise _unavailable()
    if row is None:
        raise HTTPException(status_code=404, detail='No DJ session yet. Start one on this device first.')
    return _doc(row)
