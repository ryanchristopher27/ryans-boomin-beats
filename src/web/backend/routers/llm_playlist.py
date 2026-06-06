import json
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from services.llm_client import LLMClient
from services.spotify_validator import validate_songs

router = APIRouter()

SYSTEM_PROMPT = """You are a music expert who creates playlists. When asked to build a playlist, respond ONLY with a valid JSON array — no prose, no markdown, no code fences. Each object must have exactly three string fields: "title" (song title), "artist" (primary artist name), and "reason" (one sentence explaining why this song fits the request).

Example:
[{"title": "Midnight Rider", "artist": "Allman Brothers Band", "reason": "A classic late-night driving song with a restless, open-road feel."}]"""

MAX_RETRIES = 3


class GeneratePlaylistRequest(BaseModel):
    prompt: str
    messages: list[dict] = []
    count: int = 12


@router.post("/llm/generate-playlist/")
async def generate_playlist(body: GeneratePlaylistRequest, request: Request):
    provider = request.session.get('llm_provider')
    api_key = request.session.get('llm_api_key')
    if not provider or not api_key:
        raise HTTPException(status_code=401, detail='LLM not connected. POST /llm/connect/ first.')

    client = LLMClient(provider=provider, api_key=api_key)
    conversation = list(body.messages) + [{'role': 'user', 'content': body.prompt}]

    matched: list[dict] = []
    seen_ids: set[str] = set()
    failed: list[dict] = []

    for attempt in range(MAX_RETRIES + 1):
        needed = body.count - len(matched)
        if needed <= 0:
            break

        if attempt == 0:
            llm_messages = conversation
        else:
            failed_list = ', '.join(f'"{s["title"]}" by {s["artist"]}' for s in failed)
            retry_prompt = (
                f'The following songs could not be found on Spotify: {failed_list}. '
                f'Suggest {needed} different replacement songs that are definitely on Spotify. '
                f'Do not suggest any songs listed above.'
            )
            llm_messages = [{'role': 'user', 'content': retry_prompt}]

        try:
            raw = await client.generate(llm_messages, SYSTEM_PROMPT)
            raw = raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
            suggestions = json.loads(raw)
        except Exception:
            continue

        new_matched, failed = await validate_songs(suggestions)
        for song in new_matched:
            track_id = song.get('spotify', {}).get('id')
            if track_id and track_id not in seen_ids:
                seen_ids.add(track_id)
                matched.append(song)

    updated_messages = conversation + [{
        'role': 'assistant',
        'content': json.dumps([{'title': s['title'], 'artist': s['artist']} for s in matched]),
    }]

    return {
        'requested': body.count,
        'returned': len(matched),
        'playlist': matched,
        'messages': updated_messages,
    }
