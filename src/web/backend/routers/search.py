"""Type-ahead (Q3, fixed 2026-10-25): no Spotify quota per keystroke.

Last.fm finds the songs, ranked by popularity, so the original comes first.
Deezer's own search buried Kendrick Lamar's "Money Trees" under covers and
sped-up re-uploads (not in its top 50). Deezer then fills in art, ISRC and the
explicit flag for the top few, and its search tops up the list for songs too
niche for Last.fm. The chosen result resolves via POST /tracks/resolve/.
"""
import re

from fastapi import APIRouter, HTTPException, Query

from services import deezer, lastfm_client

router = APIRouter()

RESULTS = 10
ENRICH = 6  # Deezer lookups per query: art + ISRC for the top of the list (cached)


def _fold(s: str) -> str:
    return re.sub(r'[^0-9a-z]', '', s.casefold())


def _key(title: str, artist: str) -> str:
    lead = deezer.artists_of(artist)[0] if deezer.artists_of(artist) else artist
    return f'{_fold(deezer._base_title(title))}|{_fold(lead)}'


def _is_reupload(title: str, artist: str, query: str) -> bool:
    text, q = f'{title} {artist}'.casefold(), query.casefold()
    return any(v in text and v not in q for v in deezer._VARIANTS)


def _bare(title: str, artist: str) -> dict:
    """A Last.fm hit Deezer couldn't fill in: still shown, resolved by title on tap."""
    return {'id': f'lfm:{_key(title, artist)}'[:64], 'isrc': None, 'title': title, 'artists': [artist],
            'album': '', 'image': '', 'track_url': '', 'duration_ms': 0, 'explicit': False}


@router.get("/search/")
async def search(searchValue: str = Query(..., min_length=1, max_length=200)):
    q = searchValue.strip()
    ranked, seen = [], set()
    for hit in await lastfm_client.track_search(q):
        k = _key(hit['title'], hit['artist'])
        if k in seen or _is_reupload(hit['title'], hit['artist'], q):
            continue
        seen.add(k)
        ranked.append(hit)
    top = ranked[:ENRICH]
    found = await deezer.find_many([{'title': h['title'], 'artist': h['artist']} for h in top]) if top else {}
    tracks, ids = [], set()

    def keep(track):
        # Last.fm lists one recording under several credits ("Masego", "Masego,
        # FKJ", "Fkj & Masego"); they only look alike once Deezer resolves them.
        if track['id'] not in ids:
            ids.add(track['id'])
            tracks.append(track)
    for h in top:
        song = found.get((h['title'], h['artist']))
        keep(deezer.as_track(song) if song else _bare(h['title'], h['artist']))
    # Deezer's own results fill the rest: songs too niche for Last.fm.
    try:
        extra = await deezer.client().search(q, limit=25)
    except deezer.DeezerUnavailable:
        if not tracks:
            raise HTTPException(status_code=503, detail="Search isn't available right now. Try again in a moment.")
        extra = []
    for s in extra:
        if len(tracks) >= RESULTS:
            break
        k = _key(s['title'], s['artists'][0] if s['artists'] else '')
        if k in seen or _is_reupload(s['title'], s['artists'][0] if s['artists'] else '', q):
            continue
        seen.add(k)
        keep(deezer.as_track(s))
    return {'type': 'searchSongs', 'tracks': tracks[:RESULTS]}
