"""Type-ahead (Q3, fixed 2026-10-25): no Spotify quota per keystroke.

Two sources, each covering the other's blind spot:
- Last.fm ranks by popularity, so a complete query gets the original first
  (Deezer's search buried Kendrick Lamar's "Money Trees" under re-uploads),
  but it only matches whole words.
- Deezer matches prefixes ("redbo" -> Redbone), so it carries mid-word queries.
Popular, Deezer-confirmed Last.fm hits lead; Deezer's results follow; the rest
of Last.fm fills in. Re-uploads drop unless asked for. The chosen result
resolves via POST /tracks/resolve/.
"""
import re

from fastapi import APIRouter, HTTPException, Query

from services import deezer, lastfm_client

router = APIRouter()

RESULTS = 10
ENRICH = 6  # Deezer lookups per query: art + ISRC for the top of the list (cached)
# A Last.fm hit this popular, confirmed on Deezer, leads the list. Mid-word
# queries only get whole-word junk from Last.fm ("Septem" by Hexis for
# "septem"), which never reaches this, so Deezer's prefix matches lead instead.
STRONG_LISTENERS = 100_000
MAX_STRONG = 3


def _fold(s: str) -> str:
    return re.sub(r'[^0-9a-z]', '', s.casefold())


def _key(title: str, artist: str) -> str:
    lead = deezer.artists_of(artist)[0] if deezer.artists_of(artist) else artist
    return f'{_fold(deezer._base_title(title))}|{_fold(lead)}'


def _is_reupload(title: str, artist: str, query: str) -> bool:
    return deezer.is_reupload(title, artist, query)


def _relevant(title: str, artist: str, query: str) -> bool:
    """Every word typed must start some word of the title or artist. Last.fm
    matches whole words only, so mid-word ("money tre") it returns unrelated
    songs ("HONEY", "Dirty Money" by Tre Loaded); this drops them, and Deezer,
    which matches prefixes well, fills in until the word is complete."""
    words = re.findall(r'[0-9a-z]+', f'{title} {artist}'.casefold())
    return all(any(w.startswith(t) for w in words) for t in re.findall(r'[0-9a-z]+', query.casefold()))


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
        if k in seen or _is_reupload(hit['title'], hit['artist'], q) or not _relevant(hit['title'], hit['artist'], q):
            continue
        seen.add(k)
        ranked.append(hit)
    top = ranked[:ENRICH]
    found = await deezer.find_many([{'title': h['title'], 'artist': h['artist']} for h in top]) if top else {}
    try:
        from_deezer = await deezer.client().search(q, limit=25)
    except deezer.DeezerUnavailable:
        if not ranked:
            raise HTTPException(status_code=503, detail="Search isn't available right now. Try again in a moment.")
        from_deezer = []

    tracks, ids = [], set()

    def keep(track):
        # Last.fm lists one recording under several credits ("Masego", "Masego,
        # FKJ", "Fkj & Masego"); they only look alike once Deezer resolves them.
        if track['id'] not in ids and len(tracks) < RESULTS:
            ids.add(track['id'])
            tracks.append(track)

    # 1. Popular songs Last.fm is sure of (the original "Money Trees" leads).
    #    Mid-word, Last.fm only has whole-word junk, which won't be this popular.
    strong = [h for h in top if h['listeners'] >= STRONG_LISTENERS and found.get((h['title'], h['artist']))]
    for h in strong[:MAX_STRONG]:
        keep(deezer.as_track(found[(h['title'], h['artist'])]))
    # 2. Deezer's own results: it matches prefixes, so it carries mid-word queries.
    for s in from_deezer:
        artist = s['artists'][0] if s['artists'] else ''
        if _is_reupload(s['title'], artist, q) or not _relevant(s['title'], artist, q):
            continue
        keep(deezer.as_track(s))
    # 3. The rest of Last.fm's hits, for songs too niche for Deezer's search.
    for h in top:
        song = found.get((h['title'], h['artist']))
        keep(deezer.as_track(song) if song else _bare(h['title'], h['artist']))
    return {'type': 'searchSongs', 'tracks': tracks}
