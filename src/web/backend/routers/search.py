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
ENRICH = 8  # Deezer lookups per query: cover + ISRC for the Last.fm hits shown (cached)
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


def _artist_prefixed(title: str, artist: str, songs: set[tuple[str, str]]) -> bool:
    """A YouTube-style upload titled "Artist - Song", e.g. "Kendrick Lamar -
    Money Trees" posted by "Music": the real recording ("Money Trees" by Kendrick
    Lamar) is elsewhere in the results, or the uploader prefixed its own name.
    Real dashed titles stay: "September - Live" by Earth, Wind & Fire isn't
    dropped just because a band called September exists."""
    m = re.match(r'^(.+?)\s-\s(.+)$', title)
    if not m:
        return False
    left, song = _fold(m.group(1)), _fold(deezer._base_title(m.group(2)))
    return left == _fold(artist) or (left, song) in songs


_FEATURING = re.compile(r'[\(\[]\s*(?:feat\.?|ft\.?|featuring|with)\b[^\)\]]*[\)\]]', re.I)


def _names_other_artist(title: str, artist: str, named: set[str], query: str) -> bool:
    """When the query names an artist ("kendrick lamar money"), a result whose
    title mentions that artist but isn't by them is an upload, parody or tribute
    ("humble by kendrick lamar", "kendrick lamar ~ money trees ﾉ slowed + reverb
    ﾉ"). Featured credits ("(feat. Kendrick Lamar)") are real collaborations.
    A title that is itself what was typed is the song, not a mention: "Dancing
    Queen" by ABBA stays though a "Queen" exists, as does "Redbone (Slowed)".
    Not "Kendrick Lamar - Money Without Me": its left side is the named artist."""
    dashed = re.match(r'^(.+?)\s-\s', title)
    if _fold(deezer._base_title(title)) in _fold(query) and not (dashed and _fold(dashed.group(1)) in named):
        return False
    text = _fold(_FEATURING.sub('', title))
    own = {_fold(a) for a in deezer.artists_of(artist)}
    return any(a in text and a not in own for a in named)


def _relevant(title: str, artist: str, query: str) -> bool:
    """Every word typed must start some word of the title or artist. Last.fm
    matches whole words only, so mid-word ("money tre") it returns unrelated
    songs ("HONEY", "Dirty Money" by Tre Loaded); this drops them, and Deezer,
    which matches prefixes well, fills in until the word is complete."""
    words = re.findall(r'[0-9a-z]+', f'{title} {artist}'.casefold())
    return all(any(w.startswith(t) for w in words) for t in re.findall(r'[0-9a-z]+', query.casefold()))


def _bare(title: str, artist: str, image: str = '') -> dict:
    """A Last.fm hit Deezer couldn't fill in: still shown (with Last.fm's cover
    when it has one), resolved by title on tap."""
    return {'id': f'lfm:{_key(title, artist)}'[:64], 'isrc': None, 'title': title, 'artists': [artist],
            'album': '', 'image': image, 'track_url': '', 'duration_ms': 0, 'explicit': False}


@router.get("/search/")
async def search(searchValue: str = Query(..., min_length=1, max_length=200)):
    q = searchValue.strip()
    hits = await lastfm_client.track_search(q)
    try:
        from_deezer = await deezer.client().search(q, limit=25)
    except deezer.DeezerUnavailable:
        if not hits:
            raise HTTPException(status_code=503, detail="Search isn't available right now. Try again in a moment.")
        from_deezer = []
    # (artist, song) pairs either source lists, to spot "Artist - Song" uploads.
    credited = {(_fold(a), _fold(deezer._base_title(h['title']))) for h in hits for a in deezer.artists_of(h['artist'])}
    credited |= {(_fold(s['artists'][0]), _fold(deezer._base_title(s['title']))) for s in from_deezer if s['artists']}
    # Artists the query names (credited by a real result), for _names_other_artist.
    names = {_fold(a) for h in hits for a in deezer.artists_of(h['artist'])}
    names |= {_fold(s['artists'][0]) for s in from_deezer if s['artists']}
    # Only when the query is more than the name: "september" alone could mean
    # the song or the band September, so it names nobody.
    named = {a for a in names if len(a) >= 4 and a in _fold(q) and a != _fold(q)}
    ranked, seen = [], set()
    for hit in hits:
        k = _key(hit['title'], hit['artist'])
        if k in seen or _is_reupload(hit['title'], hit['artist'], q) or not _relevant(hit['title'], hit['artist'], q) \
                or _artist_prefixed(hit['title'], hit['artist'], credited) or _names_other_artist(hit['title'], hit['artist'], named, q):
            continue
        seen.add(k)
        ranked.append(hit)
    top = ranked[:ENRICH]
    found = await deezer.find_many([{'title': h['title'], 'artist': h['artist']} for h in top]) if top else {}

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
    shown = set()
    for h in strong[:MAX_STRONG]:
        keep(deezer.as_track(found[(h['title'], h['artist'])]))
        shown.add(_key(h['title'], h['artist']))
    # 2. Deezer's own results: it matches prefixes, so it carries mid-word queries.
    for s in from_deezer:
        artist = s['artists'][0] if s['artists'] else ''
        if _is_reupload(s['title'], artist, q) or not _relevant(s['title'], artist, q) \
                or _artist_prefixed(s['title'], artist, credited) or _names_other_artist(s['title'], artist, named, q):
            continue
        # One row per song per artist: Deezer lists every release ("Come and Get
        # Your Love", its single version, re-records, compilations) separately.
        k = _key(s['title'], artist)
        if k in shown:
            continue
        shown.add(k)
        keep(deezer.as_track(s))
    # 3. The rest of Last.fm's hits, for songs too niche for Deezer's search.
    for h in top:
        if _key(h['title'], h['artist']) in shown:
            continue
        song = found.get((h['title'], h['artist']))
        keep(deezer.as_track(song) if song else _bare(h['title'], h['artist'], h.get('image', '')))
    return {'type': 'searchSongs', 'tracks': tracks}


@router.get("/preview/")
async def preview(
    dz: int | None = Query(None, ge=1),
    isrc: str | None = Query(None, pattern=r'^[A-Za-z0-9]{12}$'),
    title: str = Query('', max_length=300),
    artist: str = Query('', max_length=300),
):
    """A fresh Deezer 30 s preview URL for a song (F2). Never touches Spotify."""
    try:
        url = await deezer.client().preview(dz, isrc, title, artist)
    except deezer.DeezerUnavailable:
        raise HTTPException(status_code=503, detail="Previews aren't available right now. Try again in a moment.")
    if not url:
        raise HTTPException(status_code=404, detail="No preview for this song.")
    return {'url': url}
