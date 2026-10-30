"""DJ chat: the host asks in their own words. The AI answers with a short reply,
songs that fit (checked on Deezer like the moves), and actions the page applies:
switch or rearrange the widget layout, change the DJ's controls, set a goal,
or re-ask the board of moves with a note. Actions are validated here and again
on the page (lib/dj/chat.js) before anything changes."""
import json
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from routers.dj import Goal, TrackRef, _refs, fill_moves
from services.claude_code import ClaudeCodeError
from services.llm_auth import LLMCredentials, get_llm_credentials
from services.llm_client import NeedsLLM
from services.llm_json import LLMParseError, extract_json

log = logging.getLogger(__name__)

router = APIRouter()

MAX_PICKS = 6
PRESETS = ('host', 'board', 'compass', 'focus')
MODES = ('whisper', 'copilot', 'autofill', 'driver')
MOVE_KINDS = ('toward', 'hold', 'lift', 'drop', 'pivot', 'curveball', 'drift')

_Short = Annotated[str, StringConstraints(max_length=2000)]


class ChatTurn(BaseModel):
    role: Literal['user', 'assistant']
    content: _Short


class LayoutItem(BaseModel):
    type: Annotated[str, StringConstraints(max_length=20)]
    kind: Annotated[str, StringConstraints(max_length=20)] | None = None
    x: int = Field(ge=0, le=12)
    y: int = Field(ge=0, le=60)
    w: int = Field(ge=1, le=12)
    h: int = Field(ge=1, le=30)


class WidgetInfo(BaseModel):
    type: Annotated[str, StringConstraints(max_length=20)]
    title: Annotated[str, StringConstraints(max_length=40)]
    minW: int = Field(ge=1, le=12)
    minH: int = Field(ge=1, le=30)


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    history: list[ChatTurn] = Field(default=[], max_length=12)
    now_playing: TrackRef | None = None
    recent: list[TrackRef] = _refs()
    upcoming: list[TrackRef] = _refs()
    mode: Literal['whisper', 'copilot', 'autofill', 'driver'] = 'copilot'
    adventurousness: float = Field(default=0.5, ge=0, le=1)
    familiar: float = Field(default=0.5, ge=0, le=1)
    clean: bool = False
    goal: Goal | None = None
    preset: Annotated[str, StringConstraints(max_length=20)] = 'host'
    layout: list[LayoutItem] = Field(default=[], max_length=20)
    widgets: list[WidgetInfo] = Field(default=[], max_length=20)


SYSTEM_PROMPT = """You are the DJ assistant inside a party DJ app. The host chats with you to get songs, steer the DJ, or change how the DJ screen is laid out.

Respond ONLY with a JSON object, no prose and no code fences:
{"reply": "one or two short sentences to the host",
 "picks": [{"title": "...", "artist": "primary artist", "reason": "one short sentence"}],
 "actions": [ ... ]}

"picks": songs that answer the host's ask (0 to 8; the app checks they exist and shows the best). Leave it empty when the host only wants a layout or setting change. Never repeat songs already played or queued.

"actions" (0 or more, only what the host asked for):
- {"type": "preset", "name": "host" | "board" | "compass" | "focus"}  switch to a built-in layout
- {"type": "layout", "items": [{"type": "...", "kind": "...", "x": 0, "y": 0, "w": 3, "h": 6}]}  a full custom layout on a 12-column grid (x + w <= 12). Include every widget that should stay. "kind" only for type "move" (one move's card). Respect each widget's minimum size. Use rows 0-20.
- {"type": "controls", "mode": "whisper"|"copilot"|"autofill"|"driver", "adventurousness": 0-1 (0 safe, 1 bold), "familiar": 0-1 (0 from their library, 1 mostly new)}  include only the fields to change
- {"type": "goal", "goal": null}  or  {"type": "goal", "goal": {"kind": "destination", "destination": "where the night should end up", "minutes": 30}}  or  {"kind": "drift"}  or  {"kind": "arc", "shape": "build"|"wind_down"|"peak_cool", "minutes": 60}
- {"type": "refresh_moves", "note": "what to change about the suggested moves, a few words"}  when the host wants the whole board of moves to shift (e.g. more upbeat)

If the host asks for something the app can't do, say so in "reply" and return no actions."""


def build_prompt(body: ChatRequest) -> str:
    def ref(t: TrackRef) -> str:
        return f'"{t.title}" by {t.artist}'

    widgets = '\n'.join(f'- {w.type}: {w.title} (min {w.minW}x{w.minH})' for w in body.widgets)
    layout = json.dumps([i.model_dump(exclude_none=True) for i in body.layout])
    goal = body.goal.model_dump(exclude={'elapsed_minutes'}) if body.goal else None
    lines = [
        f'Now playing: {ref(body.now_playing)}' if body.now_playing else 'Nothing is playing.',
        f'Played recently: {", ".join(ref(t) for t in body.recent[:10]) or "nothing yet"}',
        f'Queued: {", ".join(ref(t) for t in body.upcoming[:10]) or "nothing"}',
        f'DJ controls: mode {body.mode}, adventurousness {body.adventurousness:.2f}, familiar {body.familiar:.2f}, clean only {body.clean}, goal {json.dumps(goal)}',
        f'Layout preset: {body.preset}. Current widgets: {layout}',
        f'Widget types:\n{widgets}',
        f'Move kinds for "move" widgets: {", ".join(MOVE_KINDS)}',
        '',
        f'Host: {body.message}',
    ]
    return '\n'.join(lines)


def clean_actions(raw, widget_types: set[str]) -> list[dict]:
    """Keep only well-formed actions; the page validates the layout again."""
    out = []
    for a in raw if isinstance(raw, list) else []:
        if not isinstance(a, dict):
            continue
        kind = a.get('type')
        if kind == 'preset' and a.get('name') in PRESETS:
            out.append({'type': 'preset', 'name': a['name']})
        elif kind == 'layout' and isinstance(a.get('items'), list):
            items = []
            for i in a['items'][:20]:
                try:
                    item = LayoutItem(**{k: i[k] for k in ('type', 'kind', 'x', 'y', 'w', 'h') if k in i})
                except (TypeError, ValueError):
                    continue
                if item.type in widget_types and (item.type != 'move' or item.kind in MOVE_KINDS):
                    items.append(item.model_dump(exclude_none=True))
            if items:
                out.append({'type': 'layout', 'items': items})
        elif kind == 'controls':
            c = {'type': 'controls'}
            if a.get('mode') in MODES:
                c['mode'] = a['mode']
            for key in ('adventurousness', 'familiar'):
                v = a.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    c[key] = min(1.0, max(0.0, float(v)))
            if len(c) > 1:
                out.append(c)
        elif kind == 'goal':
            g = a.get('goal')
            if g is None:
                out.append({'type': 'goal', 'goal': None})
            else:
                try:
                    goal = Goal(**g) if isinstance(g, dict) else None
                except (TypeError, ValueError):
                    goal = None
                if goal:
                    out.append({'type': 'goal', 'goal': goal.model_dump(exclude={'elapsed_minutes'})})
        elif kind == 'refresh_moves' and isinstance(a.get('note'), str) and a['note'].strip():
            out.append({'type': 'refresh_moves', 'note': a['note'].strip()[:60]})
    return out


def pick_entries(raw) -> list[dict]:
    out = []
    for p in raw if isinstance(raw, list) else []:
        if isinstance(p, dict) and isinstance(p.get('title'), str) and isinstance(p.get('artist'), str) and p['title'].strip() and p['artist'].strip():
            out.append({'title': p['title'].strip()[:200], 'artist': p['artist'].strip()[:200], 'reason': str(p.get('reason') or '')[:300]})
    return out[:MAX_PICKS + 2]


@router.post('/dj/chat/')
async def dj_chat(body: ChatRequest, creds: LLMCredentials = Depends(get_llm_credentials)):
    client = creds.client()
    messages = [{'role': t.role, 'content': t.content} for t in body.history[-10:]]
    messages.append({'role': 'user', 'content': build_prompt(body)})
    try:
        raw = await client.generate(messages, SYSTEM_PROMPT)
    except NeedsLLM:
        raise
    except Exception as e:
        log.warning('[dj-chat] %s request failed: %s', creds.provider, e)
        message = str(e) if isinstance(e, ClaudeCodeError) else f'{creds.provider} request failed: {e}'
        raise HTTPException(status_code=502, detail=message)
    try:
        data = extract_json(raw, context='dj-chat')
    except LLMParseError:
        # A plain-text answer still reads as a reply.
        return {'reply': raw.strip()[:600], 'picks': [], 'actions': []}
    if not isinstance(data, dict):
        data = {}

    entries = pick_entries(data.get('picks'))
    picks = []
    if entries:
        refs = [r for r in (body.now_playing, *body.recent, *body.upcoming) if r]
        exclude = {r.isrc for r in refs if r.isrc}
        result = await fill_moves({'chat': entries}, exclude, MAX_PICKS, clean=body.clean)
        picks = result[0]['tracks'] if result else []

    widget_types = {w.type for w in body.widgets} or {i.type for i in body.layout}
    return {
        'reply': str(data.get('reply') or '').strip()[:600] or ('Here are some songs.' if picks else 'Done.'),
        'picks': picks,
        'actions': clean_actions(data.get('actions'), widget_types),
    }
