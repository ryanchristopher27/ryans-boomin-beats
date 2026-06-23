import json
import asyncio
from fastapi import APIRouter, Query, Request
from services import lastfm_client
from services.llm_client import LLMClient

router = APIRouter()

SCORE_KEYS = ['Energy', 'Danceability', 'Positivity', 'Acousticness', 'Intensity', 'Tempo']

ANALYSIS_PROMPT = """You are a music expert. Given a song title, artist, and any available listener tags, return a single JSON object and NOTHING else — no prose, no markdown code fences.

The JSON must have exactly this structure:
{
  "analysis": {
    "Mood": "1-2 sentences",
    "Instrumentation": "1-2 sentences",
    "Lyrical Themes": "1-2 sentences",
    "Era": "1-2 sentences",
    "Cultural Context": "1-2 sentences"
  },
  "scores": {
    "Energy": <int 0-100>,
    "Danceability": <int 0-100>,
    "Positivity": <int 0-100>,
    "Acousticness": <int 0-100>,
    "Intensity": <int 0-100>,
    "Tempo": <int 0-100>
  },
  "tags": ["<lowercase genre/mood descriptor>", ...]
}

Guidance:
- Ground the analysis in the provided listener tags when available; otherwise use your own knowledge of the song.
- scores: integers 0-100. Energy=calm→energetic, Danceability=still→danceable, Positivity=dark/sad→bright/happy, Acousticness=electronic→acoustic, Intensity=gentle→intense, Tempo=slow→fast.
- tags: 5-8 short lowercase descriptors (genres, moods, eras), e.g. "shoegaze", "melancholic", "2000s".
"""


def _empty_analysis() -> dict:
    return {'analysis_text': None, 'scores': None, 'tags': []}


def _parse_analysis(raw: str) -> dict:
    """Parse the LLM's JSON response into analysis text, scores, and tags."""
    try:
        cleaned = raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        data = json.loads(cleaned)
    except Exception:
        return _empty_analysis()

    # Rebuild the labeled-lines analysis string the frontend already understands.
    analysis_obj = data.get('analysis', {})
    if isinstance(analysis_obj, dict) and analysis_obj:
        analysis_text = '\n'.join(f'{k}: {v}' for k, v in analysis_obj.items())
    else:
        analysis_text = None

    # Validate + clamp scores.
    raw_scores = data.get('scores', {}) or {}
    scores = None
    if isinstance(raw_scores, dict):
        parsed_scores = {}
        for key in SCORE_KEYS:
            val = raw_scores.get(key)
            if isinstance(val, (int, float)):
                parsed_scores[key] = max(0, min(100, int(val)))
        if len(parsed_scores) == len(SCORE_KEYS):
            scores = parsed_scores

    tags = data.get('tags', []) or []
    tags = [str(t).strip().lower() for t in tags if str(t).strip()]

    return {'analysis_text': analysis_text, 'scores': scores, 'tags': tags}


async def _llm_analysis(title: str, artist: str, tags: list, provider: str, api_key: str) -> dict:
    tag_names = ', '.join(t['name'] for t in tags) if tags else 'none available'
    user_msg = f'Song: "{title}" by {artist}\nListener tags: {tag_names}'
    client = LLMClient(provider=provider, api_key=api_key)
    raw = await client.generate([{'role': 'user', 'content': user_msg}], ANALYSIS_PROMPT)
    return _parse_analysis(raw)


def _merge_tags(lastfm_tags: list, ai_tags: list) -> list:
    """Merge Last.fm tags (list of {name}) with AI tags (list of str), deduped (case-insensitive)."""
    merged = []
    seen = set()
    for t in lastfm_tags:
        name = t.get('name', '').strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            merged.append({'name': name})
    for name in ai_tags:
        key = name.strip().lower()
        if name.strip() and key not in seen:
            seen.add(key)
            merged.append({'name': name.strip()})
    return merged


@router.get('/song/profile/')
async def song_profile(request: Request, title: str = Query(...), artist: str = Query(...)):
    provider = request.session.get('llm_provider')
    api_key = request.session.get('llm_api_key')

    if provider and api_key:
        lastfm_data, analysis = await asyncio.gather(
            lastfm_client.track_info(title, artist),
            _llm_analysis(title, artist, [], provider, api_key),
            return_exceptions=True,
        )
        if isinstance(lastfm_data, Exception):
            lastfm_data = lastfm_client._empty()
        if isinstance(analysis, Exception):
            analysis = _empty_analysis()
        # Re-run analysis grounded in the actual tags if Last.fm returned them.
        if not isinstance(lastfm_data, Exception) and lastfm_data['tags']:
            try:
                analysis = await _llm_analysis(title, artist, lastfm_data['tags'], provider, api_key)
            except Exception:
                pass
    else:
        lastfm_data = await lastfm_client.track_info(title, artist)
        analysis = _empty_analysis()

    merged_tags = _merge_tags(lastfm_data['tags'], analysis['tags'])

    return {
        'title': title,
        'artist': artist,
        'tags': merged_tags,
        'listeners': lastfm_data['listeners'],
        'play_count': lastfm_data['play_count'],
        'wiki_summary': lastfm_data['wiki_summary'],
        'analysis': analysis['analysis_text'],
        'scores': analysis['scores'],
        'has_llm': analysis['analysis_text'] is not None,
    }
