import asyncio
from fastapi import APIRouter, Query, Request
from services import lastfm_client
from services.llm_client import LLMClient

router = APIRouter()

ANALYSIS_PROMPT = """You are a music expert. Given a song title, artist, and any available listener tags, write a structured analysis. Return exactly these five labeled lines and nothing else:

Mood: ...
Instrumentation: ...
Lyrical Themes: ...
Era: ...
Cultural Context: ...

Each value should be 1-2 sentences. If tags are provided, ground your analysis in them. If tags are absent or sparse, use your own knowledge of the song."""


async def _llm_analysis(title: str, artist: str, tags: list, provider: str, api_key: str) -> str:
    tag_names = ', '.join(t['name'] for t in tags) if tags else 'none available'
    user_msg = f'Song: "{title}" by {artist}\nListener tags: {tag_names}'
    client = LLMClient(provider=provider, api_key=api_key)
    return await client.generate([{'role': 'user', 'content': user_msg}], ANALYSIS_PROMPT)


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
            analysis = None
        # Re-run analysis with actual tags if Last.fm returned them
        if provider and api_key and not isinstance(lastfm_data, Exception) and lastfm_data['tags']:
            try:
                analysis = await _llm_analysis(title, artist, lastfm_data['tags'], provider, api_key)
            except Exception:
                pass
    else:
        lastfm_data = await lastfm_client.track_info(title, artist)
        analysis = None

    return {
        'title': title,
        'artist': artist,
        'tags': lastfm_data['tags'],
        'listeners': lastfm_data['listeners'],
        'play_count': lastfm_data['play_count'],
        'wiki_summary': lastfm_data['wiki_summary'],
        'analysis': analysis,
        'has_llm': analysis is not None,
    }
