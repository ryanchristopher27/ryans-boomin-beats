import logging
import re
import httpx
from config import LASTFM_API_KEY

log = logging.getLogger(__name__)

# HTTPS: the API key travels in the query string.
BASE_URL = 'https://ws.audioscrobbler.com/2.0/'


# Last.fm's stand-in when it has no art (a grey star): treat as no image.
_PLACEHOLDER = '2a96cbd8b46e442fc41c2b86b821562f'


def _image(images) -> str:
    """The largest real image URL from Last.fm's [{'#text': url, 'size': ...}] list."""
    for img in reversed(images or []):
        url = (img or {}).get('#text') or ''
        if url and _PLACEHOLDER not in url:
            return url
    return ''


async def track_search(query: str, limit: int = 15) -> list[dict]:
    """[{title, artist, listeners}] ranked by Last.fm (by popularity), or []
    on any failure. Type-ahead uses it because Deezer's search can bury the
    original under re-uploads (Money Trees wasn't in its top 50)."""
    if not LASTFM_API_KEY:
        return []
    params = {'method': 'track.search', 'track': query, 'api_key': LASTFM_API_KEY, 'format': 'json', 'limit': limit}
    try:
        async with httpx.AsyncClient() as client:
            data = (await client.get(BASE_URL, params=params, timeout=4.0)).json()
        tracks = data['results']['trackmatches']['track']
    except Exception as e:
        log.info('[lastfm] search failed: %s', e)
        return []
    out = []
    for t in tracks if isinstance(tracks, list) else [tracks]:
        try:
            out.append({'title': t['name'], 'artist': t['artist'], 'listeners': int(t.get('listeners') or 0),
                        'image': _image(t.get('image'))})
        except (KeyError, TypeError, ValueError):
            continue
    return out


async def track_similar(title: str, artist: str, limit: int = 30) -> list[dict]:
    """[{title, artist, match}] that Last.fm listeners play alongside this track,
    best match first, or [] on any failure. The DJ's no-AI-key picks (F3e)."""
    if not LASTFM_API_KEY:
        return []
    params = {'method': 'track.getSimilar', 'artist': artist, 'track': title, 'api_key': LASTFM_API_KEY,
              'format': 'json', 'autocorrect': 1, 'limit': limit}
    try:
        async with httpx.AsyncClient() as client:
            data = (await client.get(BASE_URL, params=params, timeout=4.0)).json()
        tracks = data['similartracks']['track']
    except Exception as e:
        log.info('[lastfm] similar failed: %s', e)
        return []
    out = []
    for t in tracks if isinstance(tracks, list) else [tracks]:
        try:
            out.append({'title': t['name'], 'artist': t['artist']['name'], 'match': float(t.get('match') or 0)})
        except (KeyError, TypeError, ValueError):
            continue
    return out


async def track_info(title: str, artist: str) -> dict:
    params = {
        'method': 'track.getInfo',
        'api_key': LASTFM_API_KEY,
        'artist': artist,
        'track': title,
        'format': 'json',
        'autocorrect': 1,
    }
    if not LASTFM_API_KEY:
        log.warning('[lastfm] LASTFM_API_KEY is unset — tags and play counts unavailable')
        return _empty()

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(BASE_URL, params=params, timeout=5.0)
            data = res.json()
    except Exception as e:
        log.warning('[lastfm] request failed for %r by %r: %s', title, artist, e)
        return _empty()

    # Error 10 is an invalid API key — a config problem, not a missing track,
    # and it silently degraded every profile to zero tags before this log.
    if 'error' in data:
        log.warning('[lastfm] API error %s: %s', data.get('error'), data.get('message'))
        return _empty()

    if 'track' not in data:
        log.info('[lastfm] no track match for %r by %r', title, artist)
        return _empty()

    track = data['track']

    tags = []
    if 'toptags' in track and 'tag' in track['toptags']:
        tags = [
            {'name': t['name'], 'url': t['url']}
            for t in track['toptags']['tag']
            if t.get('name')
        ]

    wiki_summary = ''
    if 'wiki' in track and 'summary' in track['wiki']:
        raw = track['wiki']['summary']
        wiki_summary = re.sub(r'<[^>]+>', '', raw).strip()
        wiki_summary = wiki_summary.split('Read more on Last.fm')[0].strip()

    return {
        'tags': tags,
        'listeners': int(track.get('listeners', 0) or 0),
        'play_count': int(track.get('playcount', 0) or 0),
        'wiki_summary': wiki_summary,
    }


def _empty() -> dict:
    return {'tags': [], 'listeners': 0, 'play_count': 0, 'wiki_summary': ''}


# Last.fm tags are free text; these are common ones that aren't genres.
_NOT_GENRES = {
    'seen live', 'favorites', 'favourites', 'favorite', 'favourite', 'love', 'awesome', 'beautiful', 'cool',
    'male vocalists', 'female vocalists', 'male vocalist', 'female vocalist', 'singer-songwriter',
    'american', 'british', 'uk', 'usa', 'canadian', 'english', 'australian', 'french', 'german', 'swedish',
    'korean', 'japanese', 'irish', 'scottish', 'spotify', 'albums i own', 'under 2000 listeners', 'all',
    'chill', 'mellow', 'sexy', 'party', 'catchy', 'fun',
    'bosnian', 'serbian', 'croatian', 'dutch', 'italian', 'spanish', 'brazilian', 'mexican', 'nigerian',
    'african', 'jamaican', 'norwegian', 'danish', 'finnish', 'polish', 'russian', 'new zealand', 'nz',
    # Places (cities and states are common artist tags).
    'north carolina', 'south carolina', 'california', 'texas', 'georgia', 'florida', 'new jersey', 'virginia',
    'atlanta', 'chicago', 'detroit', 'houston', 'memphis', 'new orleans', 'new york', 'nyc', 'brooklyn',
    'los angeles', 'la', 'bay area', 'toronto', 'london', 'philadelphia', 'seattle', 'miami', 'compton',
}


def is_genre_tag(name: str) -> bool:
    """False for the tags `genre_tags` always drops; also used on cached results."""
    return name not in _NOT_GENRES
# One spelling per genre: "hip-hop" and "hip hop" are the same bar on Profile.
_SPELLING = {'rnb': 'r&b', 'r and b': 'r&b', 'rhythm and blues': 'r&b', 'hiphop': 'hip hop', 'electronica': 'electronic'}


def genre_tags(tags: list[dict], artist: str, limit: int = 3) -> list[str]:
    """The genre-like tags from Last.fm's [{name, count}] (count is 0-100, relative
    to the top tag): no artist names, nationalities, decades or opinions."""
    me = artist.casefold().strip()
    out = []
    for t in tags:
        name = str(t.get('name') or '').strip().lower().replace('-', ' ')
        name = _SPELLING.get(name, name)
        try:
            count = int(t.get('count') or 0)
        except (TypeError, ValueError):
            count = 0
        if (count < 10 or not name or len(name) > 30 or name in _NOT_GENRES or name == me
                or re.fullmatch(r"\d{2,4}s?|'\d0s", name) or name in out):
            continue
        out.append(name)
        if len(out) == limit:
            break
    return out


async def artist_top_tags(artist: str) -> list[str] | None:
    """Genre-like tags for an artist from Last.fm (Spotify's artist genres come
    back empty for this app, 2026-10-29), or None when Last.fm didn't answer."""
    if not LASTFM_API_KEY or not artist:
        return None
    params = {'method': 'artist.getTopTags', 'artist': artist, 'api_key': LASTFM_API_KEY, 'format': 'json', 'autocorrect': 1}
    try:
        async with httpx.AsyncClient() as client:
            data = (await client.get(BASE_URL, params=params, timeout=4.0)).json()
        tags = data['toptags']['tag']
    except Exception as e:
        log.info('[lastfm] tags failed: %s', e)
        return None
    return genre_tags(tags if isinstance(tags, list) else [tags], artist)
