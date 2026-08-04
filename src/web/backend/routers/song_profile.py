import asyncio
import logging
from fastapi import APIRouter, Depends, Query
from services import lastfm_client
from services.llm_auth import LLMCredentials, get_optional_llm_credentials
from services.llm_client import LLMClient
from services.llm_json import LLMParseError, extract_json

log = logging.getLogger(__name__)

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


def _empty_analysis(error: str | None = None) -> dict:
    return {'analysis_text': None, 'scores': None, 'tags': [], 'error': error}


def _coerce_score(val) -> int | None:
    """Accept 85, 85.0, or "85"; reject bools and anything else. Clamp to 0-100."""
    if isinstance(val, bool):  # bool is a subclass of int — would read True as 1
        return None
    if isinstance(val, (int, float)):
        return max(0, min(100, int(val)))
    if isinstance(val, str):
        try:
            return max(0, min(100, int(float(val.strip()))))
        except ValueError:
            return None
    return None


def _parse_analysis(raw: str) -> dict:
    """Parse the LLM's JSON response into analysis text, scores, and tags."""
    try:
        data = extract_json(raw, context='song-profile')
    except LLMParseError as e:
        return _empty_analysis(f'Model did not return valid JSON: {e.snippet}')

    if not isinstance(data, dict):
        log.warning('[song-profile] expected a JSON object, got %s', type(data).__name__)
        return _empty_analysis(f'Model returned a JSON {type(data).__name__}, expected an object.')

    # Rebuild the labeled-lines analysis string the frontend already understands.
    analysis_obj = data.get('analysis', {})
    if isinstance(analysis_obj, dict) and analysis_obj:
        analysis_text = '\n'.join(f'{k}: {v}' for k, v in analysis_obj.items())
    else:
        analysis_text = None

    # Validate + clamp scores. Keys are matched case-insensitively — models
    # regularly return "energy" instead of "Energy", which previously dropped
    # the whole radar.
    raw_scores = data.get('scores', {}) or {}
    scores = None
    missing: list[str] = []
    if isinstance(raw_scores, dict):
        lowered = {str(k).strip().lower(): v for k, v in raw_scores.items()}
        parsed_scores = {}
        for key in SCORE_KEYS:
            coerced = _coerce_score(lowered.get(key.lower()))
            if coerced is None:
                missing.append(key)
            else:
                parsed_scores[key] = coerced
        # The radar needs all six axes; a partial set would render a misleading shape.
        if not missing:
            scores = parsed_scores
    else:
        missing = list(SCORE_KEYS)

    error = None
    if analysis_text is None:
        error = 'Model response had no "analysis" section.'
        log.warning('[song-profile] missing analysis section in model output')
    elif missing:
        error = f'Model omitted scores: {", ".join(missing)}. Radar hidden.'
        log.warning('[song-profile] missing scores: %s', missing)

    tags = data.get('tags', []) or []
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).strip().lower() for t in tags if str(t).strip()]

    return {'analysis_text': analysis_text, 'scores': scores, 'tags': tags, 'error': error}


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
async def song_profile(
    title: str = Query(...),
    artist: str = Query(...),
    creds: LLMCredentials | None = Depends(get_optional_llm_credentials),
):
    provider = creds.provider if creds else None
    api_key = creds.api_key if creds else None

    if provider and api_key:
        lastfm_data, analysis = await asyncio.gather(
            lastfm_client.track_info(title, artist),
            _llm_analysis(title, artist, [], provider, api_key),
            return_exceptions=True,
        )
        if isinstance(lastfm_data, Exception):
            log.warning('[song-profile] Last.fm lookup failed: %s', lastfm_data)
            lastfm_data = lastfm_client._empty()
        if isinstance(analysis, Exception):
            log.warning('[song-profile] %s call failed: %s', provider, analysis)
            analysis = _empty_analysis(f'{provider} request failed: {analysis}')
        # Re-run analysis grounded in the actual tags if Last.fm returned them.
        if lastfm_data['tags']:
            try:
                analysis = await _llm_analysis(title, artist, lastfm_data['tags'], provider, api_key)
            except Exception as e:
                # Keep the untagged analysis from the first call if it succeeded.
                log.warning('[song-profile] tag-grounded retry failed: %s', e)
                if analysis['analysis_text'] is None:
                    analysis = _empty_analysis(f'{provider} request failed: {e}')
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
        # Distinguishes "no LLM connected" (null) from "LLM connected but the
        # call or the parse failed" (a message) — previously indistinguishable.
        'analysis_error': analysis.get('error'),
    }
