import json
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.llm_auth import LLMCredentials, get_llm_credentials
from services.llm_client import LLMClient
from services.llm_json import LLMParseError, extract_json
from services.spotify_validator import validate_songs

log = logging.getLogger(__name__)

router = APIRouter()

# Keys a model might nest the array under when it ignores "respond ONLY with a
# valid JSON array" and returns an object instead.
_ARRAY_KEYS = ('playlist', 'songs', 'tracks', 'results', 'items')


def _normalize_suggestions(data) -> list[dict]:
    """Coerce a parsed model response into a list of {title, artist, reason} dicts.

    validate_songs() indexes suggestion['title'] directly, so anything malformed
    here becomes a KeyError/TypeError mid-request. Filter to well-formed entries.
    """
    if isinstance(data, dict):
        for key in _ARRAY_KEYS:
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            # A single song object rather than an array.
            data = [data]

    if not isinstance(data, list):
        return []

    cleaned = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get('title', '')).strip()
        artist = str(entry.get('artist', '')).strip()
        if title and artist:
            cleaned.append({
                'title': title,
                'artist': artist,
                'reason': str(entry.get('reason', '')).strip(),
            })
    return cleaned

SYSTEM_PROMPT = """You are a music expert who creates playlists. When asked to build a playlist, respond ONLY with a valid JSON array — no prose, no markdown, no code fences. Each object must have exactly three string fields: "title" (song title), "artist" (primary artist name), and "reason" (one sentence explaining why this song fits the request).

Example:
[{"title": "Midnight Rider", "artist": "Allman Brothers Band", "reason": "A classic late-night driving song with a restless, open-road feel."}]"""

MAX_RETRIES = 3


class GeneratePlaylistRequest(BaseModel):
    prompt: str
    messages: list[dict] = []
    count: int = 12


@router.post("/llm/generate-playlist/")
async def generate_playlist(
    body: GeneratePlaylistRequest,
    creds: LLMCredentials = Depends(get_llm_credentials),
):
    provider = creds.provider
    client = LLMClient(provider=provider, api_key=creds.api_key)
    conversation = list(body.messages) + [{'role': 'user', 'content': body.prompt}]

    matched: list[dict] = []
    seen_ids: set[str] = set()
    failed: list[dict] = []
    last_error: str | None = None

    for attempt in range(MAX_RETRIES + 1):
        needed = body.count - len(matched)
        if needed <= 0:
            break

        if attempt == 0:
            llm_messages = conversation
        elif failed:
            failed_list = ', '.join(f'"{s["title"]}" by {s["artist"]}' for s in failed)
            retry_prompt = (
                f'The following songs could not be found on Spotify: {failed_list}. '
                f'Suggest {needed} different replacement songs that are definitely on Spotify. '
                f'Do not suggest any songs listed above.'
            )
            llm_messages = [{'role': 'user', 'content': retry_prompt}]
        else:
            # The previous attempt produced no usable songs (call failed, bad
            # JSON, or wrong shape) — re-ask the original request rather than
            # sending a "could not be found: <empty list>" prompt.
            llm_messages = conversation + [{
                'role': 'user',
                'content': (
                    f'Return {needed} songs as a raw JSON array only — no prose, '
                    f'no markdown fences. Each object needs "title", "artist", "reason".'
                ),
            }]

        try:
            raw = await client.generate(llm_messages, SYSTEM_PROMPT)
        except Exception as e:
            last_error = f'{provider} request failed: {e}'
            log.warning('[playlist] attempt %d: %s', attempt, last_error)
            failed = []
            continue

        try:
            suggestions = _normalize_suggestions(extract_json(raw, context='playlist'))
        except LLMParseError as e:
            last_error = f'Model did not return valid JSON: {e.snippet}'
            log.warning('[playlist] attempt %d: parse failed', attempt)
            failed = []
            continue

        if not suggestions:
            last_error = 'Model returned JSON with no usable {title, artist} entries.'
            log.warning('[playlist] attempt %d: %s', attempt, last_error)
            failed = []
            continue

        new_matched, failed = await validate_songs(suggestions)
        for song in new_matched:
            track_id = song.get('spotify', {}).get('id')
            if track_id and track_id not in seen_ids:
                seen_ids.add(track_id)
                matched.append(song)
        if new_matched:
            last_error = None

    updated_messages = conversation + [{
        'role': 'assistant',
        'content': json.dumps([{'title': s['title'], 'artist': s['artist']} for s in matched]),
    }]

    if not matched and last_error is None:
        last_error = 'No suggested songs could be matched on Spotify.'

    return {
        'requested': body.count,
        'returned': len(matched),
        'playlist': matched,
        'messages': updated_messages,
        # Non-null when the run ended short. Previously an all-attempts-failed
        # run returned an empty playlist with HTTP 200 and no explanation.
        'error': last_error,
    }
