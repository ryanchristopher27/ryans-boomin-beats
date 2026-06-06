from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class ConnectRequest(BaseModel):
    provider: str
    api_key: str


@router.post("/llm/connect/")
async def llm_connect(body: ConnectRequest, request: Request):
    try:
        if body.provider == 'claude':
            import anthropic
            client = anthropic.Anthropic(api_key=body.api_key)
            client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=1,
                messages=[{'role': 'user', 'content': 'hi'}],
            )
        elif body.provider == 'openai':
            import openai
            client = openai.OpenAI(api_key=body.api_key)
            client.models.list()
        elif body.provider == 'groq':
            from groq import Groq
            client = Groq(api_key=body.api_key)
            client.models.list()
        else:
            return {'error': f'Unknown provider: {body.provider}'}

        request.session['llm_provider'] = body.provider
        request.session['llm_api_key'] = body.api_key
        return {'connected': True}

    except Exception as e:
        return {'error': str(e)}


@router.get("/llm/status/")
def llm_status(request: Request):
    provider = request.session.get('llm_provider')
    return {'connected': provider is not None, 'provider': provider}
