"""Validate a BYOK LLM key.

Stateless: the key is checked against the provider and discarded. Callers hold
the key themselves (localStorage in the web app, Keychain on iOS) and send it
per request via X-LLM-Provider / X-LLM-Key — see services/llm_auth.py.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from services.llm_auth import SUPPORTED_PROVIDERS

log = logging.getLogger(__name__)

router = APIRouter()


class ConnectRequest(BaseModel):
    provider: str
    api_key: str


@router.post("/llm/connect/")
async def llm_connect(body: ConnectRequest):
    provider = body.provider.strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        return {'error': f'Unknown provider: {body.provider}'}

    try:
        if provider == 'claude':
            import anthropic
            client = anthropic.Anthropic(api_key=body.api_key)
            client.messages.create(
                model='claude-haiku-4-5',
                max_tokens=1,
                messages=[{'role': 'user', 'content': 'hi'}],
            )
        elif provider == 'openai':
            import openai
            client = openai.OpenAI(api_key=body.api_key)
            client.models.list()
        elif provider == 'groq':
            from groq import Groq
            client = Groq(api_key=body.api_key)
            client.models.list()
    except Exception as e:
        log.info('[llm-connect] %s validation failed: %s', provider, e)
        return {'error': str(e)}

    return {'connected': True, 'provider': provider}
