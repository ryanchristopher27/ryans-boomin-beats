# Plan — LLM Playlist Builder
Date: 2026-06-04
Status: Active
Brainstorm: docs/brainstorm.md

---

## Overview

Add an AI-powered playlist builder to Ryan's Boomin Beats. Users connect their own Claude or OpenAI API key, describe a playlist in natural language, and the app generates a curated song list validated against Spotify's catalog. Results display in-app; users can select songs, save as a Spotify playlist, or queue everything to their active player. Conversation is supported — users can refine the playlist in follow-up prompts.

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|-----------------|
| LLM connection | User can select Claude or OpenAI, enter their API key, and have it validated |
| Playlist generation | A natural language prompt produces a list of 10–15 songs matched against Spotify |
| Spotify validation | Backend iterates until every song in the returned playlist is confirmed on Spotify |
| In-app display | Results show album art, title, artist, match status, and the LLM's reason for the pick |
| Conversational refinement | Follow-up prompts refine the playlist using prior message history |
| Spotify actions | "Add as Playlist" saves to user's Spotify; "Queue All" adds to active player |

---

## Scope

### In Scope
- LLM provider selection: Claude (Anthropic) and OpenAI
- BYOK API key input, validated on connect, stored in Django session
- New `/playlist-builder` route in SvelteKit
- LLM settings panel as a header toggle (icon button, opens popover/modal — consistent with account/settings UI pattern)
- One-shot and conversational prompting (same code path, chat history tracked in Svelte store)
- Iterative Spotify validation: backend retries with LLM until target count of fully matched songs is met (max 3 retry rounds)
- Song cards: album art, title, artist, LLM reason, select checkbox — all cards in result are confirmed Spotify matches
- Action bar: "Add All as Playlist", "Queue All", "Add Selected as Playlist"
- "Add as Playlist" and "Add Selected as Playlist" require user to enter a playlist name before submitting
- New Spotify OAuth scopes: `playlist-modify-private`, `user-modify-playback-state`
- New Django apps: `llm_connect`, `llm_playlist`, `spotify_actions`

### Out of Scope
- User auth / persistent key storage (future milestone)
- Direction B (LLM tool use / Spotify search inside the LLM loop) — deferred
- Manual song swap UI (not needed — iterative validation ensures all results are matched)
- Sharing or exporting playlists externally
- Seeding LLM with account analysis data (noted as a quick future win, not v1)

---

## Tech Stack & Architecture

**Backend migrated to FastAPI** (full migration from Django — decision made 2026-06-05):

| Layer | Tech | Notes |
|-------|------|-------|
| Frontend | SvelteKit | New route + components; new Svelte stores |
| Backend | FastAPI + Uvicorn | Full replacement of Django; all existing endpoints migrated |
| Sessions | Starlette SessionMiddleware | Same `request.session` dict interface as Django sessions |
| CORS | FastAPI CORSMiddleware | Replaces per-view CORS headers in old Django views |
| Spotify | Spotipy | Unchanged; sync Spotipy calls wrapped in `asyncio.to_thread` where async matters |
| LLM (Claude) | `anthropic` Python SDK | New dependency |
| LLM (OpenAI) | `openai` Python SDK | New dependency |

**Why FastAPI over Django:** Async-first (parallel Spotify validation, LLM calls), Pydantic request/response validation, automatic OpenAPI docs, cleaner CORS handling. The existing Django views were all thin Spotipy wrappers with no real ORM usage — migration cost is low.

**LLM abstraction:** A single `LLMClient` service class in `services/llm_client.py` wraps both SDKs with a common async interface. Provider-agnostic — router logic never imports anthropic or openai directly.

**Session key storage:** Starlette `SessionMiddleware` (cookie-signed). `POST /llm/connect/` stores `{ provider, api_key }` in `request.session`. All downstream endpoints read from session — key never re-sent from frontend.

**Spotify scope upgrade:** `SCOPE` constant in `config.py` gains `playlist-modify-private user-modify-playback-state`. Users who previously authenticated will need to re-auth — Spotipy handles this automatically.

---

## Project Structure

### Backend Structure (FastAPI — replaces Django)

```
src/web/backend/
├── main.py                        # FastAPI app: middleware, router registration
├── config.py                      # Shared constants: CLIENT_ID, SECRET, SCOPE, REDIRECT_URI
├── requirements.txt               # fastapi, uvicorn, spotipy, anthropic, openai, python-multipart
├── routers/
│   ├── __init__.py
│   ├── search.py                  # GET /search/
│   ├── recommendations.py         # GET /get-recommendations/
│   ├── profile.py                 # GET /get-profile/
│   ├── account_analysis.py        # GET /account-analysis/ (stub — WIP)
│   ├── llm_connect.py             # POST /llm/connect/
│   ├── llm_playlist.py            # POST /llm/generate-playlist/
│   └── spotify_actions.py         # POST /spotify/create-playlist/, POST /spotify/queue/
└── services/
    ├── __init__.py
    ├── llm_client.py              # LLMClient: async Claude + OpenAI abstraction
    └── spotify_validator.py       # Parallel Spotify search, two-pass match logic

# Old Django backend left in place at backend_server/ — safe to delete after migration verified
```

Run command: `uvicorn main:app --reload` (from `src/web/backend/`)

### New Frontend Files (SvelteKit)

```
src/web/frontend/src/
├── routes/
│   └── playlist-builder/
│       └── +page.svelte              # Main playlist builder page
├── lib/
│   └── components/
│       ├── LLMSettingsPanel.svelte   # Provider select + API key input (opened via header toggle)
│       ├── ChatInterface.svelte      # Prompt input + scrollable message history
│       ├── PlaylistResult.svelte     # Song list + action bar
│       ├── SongCard.svelte           # Individual song card (all shown are Spotify-confirmed)
│       └── PlaylistNameModal.svelte  # Name input modal shown before saving a playlist
└── stores.js                         # Add: llmConfig, chatMessages, generatedPlaylist
```

### Updated Files

- `src/web/frontend/src/stores.js` — add `llmConfig`, `chatMessages`, `generatedPlaylist`
- `src/web/frontend/src/routes/Header.svelte` — add LLM settings icon to `.header-actions`
- `src/web/frontend/src/lib/index.js` — export 5 new components

---

## Milestones

| # | Milestone | Description | Dependencies |
|---|-----------|-------------|--------------|
| M1 | LLM Connect | Backend session storage + frontend settings panel | None |
| M2 | Playlist Generation | LLM prompt → structured output → Spotify validation | M1 |
| M3 | Playlist Builder UI | `/playlist-builder` route, chat interface, song cards | M2 |
| M4 | Spotify Actions | Create playlist + queue endpoints + frontend action bar | M3, new OAuth scopes |

---

## Task Breakdown

### M1 — LLM Connect

**Backend:**
- Create `llm_connect` Django app
- `POST /llm/connect/` view: accepts `{ provider, api_key }`, makes a minimal test call to validate the key, stores in session on success, returns `{ connected: true }` or error
- Register app + URL in `urls.py` and `settings.py`

**Frontend:**
- Add `llmConfig` store: `writable({ provider: 'claude', apiKey: '', connected: false })`
- `LLMSettingsPanel.svelte`: provider radio/select + API key input + "Connect" button; on success sets store, persists connected state in `sessionStorage` so page refresh doesn't lose it
- Add settings toggle to `Header.svelte`: a key/gear icon button in the top-right nav area; shows a green dot indicator when `llmConfig.connected` is true; clicking opens `LLMSettingsPanel` as a popover or modal overlay
- Panel is globally accessible from any page via the header, not tied to `/playlist-builder`

---

### M2 — Playlist Generation

**Backend:**
- Create `llm_playlist` Django app
- `llm_client.py`: `LLMClient` class with `generate(messages, system_prompt) -> str`; dispatches to `anthropic.Anthropic` or `openai.OpenAI` based on session provider
- System prompt: instructs LLM to return only a JSON array of `{ title, artist, reason }` objects; no prose, no markdown wrapping; default 12 songs unless user specifies
- `spotify_validator.py`: for each `{ title, artist }`, searches Spotify as `track:{title} artist:{artist}`; if no result, retries without `artist:` filter; returns a Spotify track object or `None`
- `POST /llm/generate-playlist/` view: orchestrates the iterative validation loop (see below), returns only fully matched songs

**Iterative validation loop** (in the view or a helper):
1. Ask LLM for N songs (where N = requested count, default 12)
2. Run `spotify_validator` on all suggestions in parallel
3. Collect matched songs; collect failed `{ title, artist }` pairs
4. If `len(matched) < N` and retry count < 3: ask LLM for `N - len(matched)` replacements, passing the failed pairs so the LLM avoids re-suggesting them
5. Add any new matches to the pool; repeat from step 3
6. After max retries, return however many matched songs were found; include `requested` and `returned` counts in response so the frontend can notify the user if short

**Response shape:**
```json
{
  "requested": 12,
  "returned": 12,
  "playlist": [
    {
      "title": "Song Name",
      "artist": "Artist Name",
      "reason": "Why this fits the prompt",
      "spotify": {
        "id": "...",
        "title": "...",
        "artists": ["..."],
        "album": "...",
        "image": "...",
        "track_url": "...",
        "duration_ms": 0
      }
    }
  ],
  "messages": [...]
}
```

---

### M3 — Playlist Builder UI

- New route `src/routes/playlist-builder/+page.svelte`
- Add `chatMessages` store: `writable([])` — array of `{ role, content }`
- Add `generatedPlaylist` store: `writable([])` — full playlist result objects
- `ChatInterface.svelte`: text input, send button, scrollable message history display; on submit, POST to `/llm/generate-playlist/` with `{ prompt, messages: $chatMessages }`, update stores on response
- `SongCard.svelte`: album art, title, artist, reason tooltip, select checkbox — no match badge needed since all returned songs are Spotify-confirmed; if `returned < requested`, show a notice above the list ("Could only confirm X of Y songs on Spotify")
- `PlaylistResult.svelte`: renders list of `SongCard`s + action bar; "Add Selected as Playlist" enabled only when at least one card is checked
- `PlaylistNameModal.svelte`: modal with a text input for playlist name + "Save" / "Cancel"; triggered by "Add All as Playlist" and "Add Selected as Playlist" buttons; does not submit until name is non-empty
- Add "Playlist Builder" link to `Header.svelte`

**Page layout:**
```
[ Header — with LLM settings toggle icon (top-right) ]
[ ChatInterface — prompt input + message thread ]
[ PlaylistResult — song cards grid/list ]
[ Action Bar — Add All as Playlist | Queue All | Add Selected as Playlist ]
[ PlaylistNameModal — appears on top when saving ]
```

---

### M4 — Spotify Actions

**OAuth:**
- Append `playlist-modify-private user-modify-playback-state` to `SCOPE` across all backend views (or extract to a shared constant)

**Backend:**
- Create `spotify_actions` Django app
- `POST /spotify/create-playlist/` view: accepts `{ name, track_ids[] }`, creates playlist on user's Spotify account via Spotipy, adds tracks, returns playlist URL
- `POST /spotify/queue/` view: accepts `{ track_ids[] }`, adds each to active playback queue; handles "no active device" with a clear error message
- Register app + URLs

**Frontend:**
- Wire "Add All as Playlist": opens `PlaylistNameModal`; on name submit, calls `/spotify/create-playlist/` with all track IDs; shows success state with link to playlist
- Wire "Add Selected as Playlist": opens `PlaylistNameModal`; on name submit, calls `/spotify/create-playlist/` with only checked track IDs; button disabled if no cards checked
- Wire "Queue All": calls `/spotify/queue/` with all track IDs; handles "no active device" error with user-facing message ("Open Spotify on a device first")

---

## API Shapes

### POST /llm/connect/
```
Request:  { provider: "claude" | "openai", api_key: string }
Response: { connected: true } | { error: string }
```

### POST /llm/generate-playlist/
```
Request:  { prompt: string, messages: [{ role, content }] }
Response: { playlist: PlaylistItem[], messages: Message[] }
Session:  provider + api_key read from session
```

### POST /spotify/create-playlist/
```
Request:  { name: string, track_ids: string[] }
Response: { playlist_url: string, playlist_id: string }
```

### POST /spotify/queue/
```
Request:  { track_ids: string[] }
Response: { queued: number } | { error: "no_active_device" }
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM returns malformed JSON | Medium | High — breaks parsing | Wrap parse in try/except; retry once with stricter prompt; return error to user |
| Spotify search misses (hallucinated songs) | High | Low — handled by retry loop | Two-pass search per song + up to 3 LLM retry rounds; LLM told which songs failed; if still short after retries, notify user |
| New OAuth scopes require user re-auth | Certain | Low — expected behavior | Document clearly; Spotipy will redirect automatically when scopes change |
| Queue fails — no active Spotify device | Medium | Low | Return `error: "no_active_device"` with user-facing message: "Open Spotify on a device first" |
| API key stored in session leaks | Low | High | HTTPS in production; session is server-side; key never logged |
| Slow response (LLM + 12 Spotify searches) | Medium | Medium | Parallel Spotify searches; loading state in UI; target <5s total |

---

## Dependencies

**New Python packages:**
```
pip install fastapi uvicorn python-multipart itsdangerous spotipy anthropic openai
```
(`itsdangerous` is required by Starlette's SessionMiddleware; `python-multipart` for form data support)

**Spotify OAuth scope additions (breaking for existing sessions):**
```
playlist-modify-private user-modify-playback-state
```

**Django sessions:** Must be enabled in `settings.py` (`django.contrib.sessions` in `INSTALLED_APPS`, session middleware active). Check existing config — likely already present but unused.

---

## Open Questions

1. ~~Should `LLMSettingsPanel` be accessible from the `Header` (global) or only from the `/playlist-builder` page?~~ **Resolved: header toggle, globally accessible.**
2. ~~How should "Add Selected" work if the user has only selected matched songs vs. a mix?~~ **Resolved: all returned songs are matched (iterative validation); "Add Selected" disabled until at least one card checked.**
3. Should the conversation reset when the user navigates away from `/playlist-builder`? Stores are in-memory so yes by default — acceptable for v1.
4. ~~Default playlist name when saving to Spotify?~~ **Resolved: user must enter a name; no auto-generated default.**

---

## Decisions Log

| Decision | Choice | Reasoning | Date |
|----------|--------|-----------|------|
| Backend framework | FastAPI (full migration from Django) | Async-first, Pydantic validation, cleaner CORS; Django views were all thin Spotipy wrappers with no ORM — low migration cost | 2026-06-05 |
| Pipeline approach | Direction A: LLM output + Spotify validation | Speed, simplicity; Direction B deferred as upgrade | 2026-06-04 |
| LLM providers | Claude + OpenAI | BYOK; two most common developer accounts | 2026-06-04 |
| Key storage | Django session | No auth system needed in v1; persistence deferred | 2026-06-04 |
| Conversation | One-shot + chat, same code path | Message history is a trivial addition; not worth splitting releases | 2026-06-04 |
| Song default count | 12 | Enough to feel like a real playlist; user can specify differently in prompt | 2026-06-04 |
| Spotify search retry | Two-pass per song + up to 3 LLM retry rounds | Iterative: LLM told which songs failed and asked for replacements; guarantees all returned songs are on Spotify | 2026-06-04 |
| UI placement | Dedicated `/playlist-builder` route | Clean separation; feature is substantial enough to own a page | 2026-06-04 |
| LLM settings panel placement | Header icon toggle (global) | Consistent with account/settings UI patterns; green dot indicator shows connection status | 2026-06-04 |
| Unmatched song handling | Not surfaced to user — backend iterates until all valid | Cleaner UX; user never sees a song that can't be played | 2026-06-04 |
| Playlist name on save | Required user input via modal | No auto-generated names; user intentionally names their playlist before it's created on Spotify | 2026-06-04 |

---

---

# Plan — Song Exploration & Discovery (Pillar 1)
Date: 2026-06-05
Status: Active
Brainstorm: docs/brainstorm.md (section: "Song Exploration & Discovery")

---

## Overview

The explore feature replaces the home page entirely and lives at the root route (`/`). Users search for a specific song via Spotify autocomplete, view a rich profile of that song (Last.fm tags + LLM qualitative analysis), select the aspects they care about, and discover similar songs. Clicking a song in discovery results loads that song's profile on the same page — enabling a natural exploration chain. Discovery output reuses the existing Pillar 2 pipeline (iterative LLM generation + Spotify validation + `PlaylistResult` display). No free-text prompt input on this page — that belongs to the playlist builder.

Nav structure: **Explore | Playlist Builder | Profile**

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|-----------------|
| Song search | Spotify autocomplete surfaces matching tracks by title |
| Song profile | Page shows Last.fm tags and LLM prose analysis for the selected song |
| Tag selection | User can toggle individual tags on/off to define discovery intent |
| Discovery | "Discover" generates a validated Spotify playlist based on selected tags + song context |
| Actions | User can save discovery results as a playlist or queue them — same as Pillar 2 |

---

## Scope

### In Scope
- Explore page replaces the home page at root route `/` (old `routes/+page.svelte` replaced)
- Two-state page: idle (search bar only) → exploring (song profile + discovery results below)
- Clicking a song in discovery results loads that song's profile on the same page (exploration chain)
- `GET /song/profile/` endpoint — fetches Last.fm data and LLM analysis in parallel
- `services/lastfm_client.py` — Last.fm API wrapper
- `LASTFM_API_KEY` added to `.env`, `.env.example`, and `config.py`
- `SongSearch.svelte` — Spotify autocomplete component (extracted from old home page logic)
- `SongProfile.svelte` — tag pills + LLM prose + Discover button
- `TagPill.svelte` — selectable/toggleable pill
- LLM analysis always shown — structured template fills in when Last.fm data is sparse
- Discovery reuses existing `/llm/generate-playlist/` endpoint with richer context
- Discovery results rendered by existing `PlaylistResult.svelte` + `SongCard.svelte`
- Header nav updated: Home removed, Explore at `/` is the new primary nav item
- `setup.md` updated with Last.fm API key instructions

### Out of Scope
- Free text prompt input on the explore page (belongs to playlist builder)
- Radar chart visualization (deferred to a future visual pass)
- Last.fm similar tracks as a direct discovery source (LLM drives discovery, Last.fm provides context)
- Obscure song handling beyond graceful degradation (LLM fills in with what it knows)

---

## Tech Stack & Architecture

No new tech. Adds Last.fm as a data source alongside existing stack.

| Layer | Addition |
|-------|---------|
| Backend | `routers/song_profile.py`, `services/lastfm_client.py` |
| External API | Last.fm (free, API key only, no OAuth) |
| Frontend | 3 new components, root route replaced |
| Discovery pipeline | Reuses `/llm/generate-playlist/` — no new backend needed |

**Key architectural decision: single `/song/profile/` call does both Last.fm and LLM.**
Last.fm fetch and LLM analysis run in parallel (`asyncio.gather`). Frontend makes one request and gets a complete profile back — no waterfall, no second round-trip.

**Discovery via existing endpoint:**
The explore page calls `/llm/generate-playlist/` with a crafted prompt that includes the song title, artist, LLM analysis, and selected tags. The endpoint is unmodified — richer context flows through the existing `prompt` field.

---

## Project Structure

### New Backend Files

```
src/web/backend/
├── routers/
│   └── song_profile.py          # GET /song/profile/
└── services/
    └── lastfm_client.py         # Last.fm track.getInfo wrapper
```

### Replaced Frontend Files

```
src/web/frontend/src/
└── routes/
    └── +page.svelte             # Replaced: was home page, now explore page
```

### New Frontend Components

```
src/web/frontend/src/lib/components/
    ├── SongSearch.svelte         # Spotify autocomplete (extracted from old home page)
    ├── SongProfile.svelte        # Tag pills + LLM prose + Discover button
    └── TagPill.svelte            # Selectable tag pill
```

### Updated Files

- `config.py` — add `LASTFM_API_KEY`
- `.env` + `.env.example` — add `LASTFM_API_KEY`
- `main.py` — register `song_profile` router
- `lib/index.js` — export 3 new components
- `Header.svelte` — replace "Home" nav entry with "Explore" (same href `/`, new label)
- `docs/setup.md` — Last.fm API key instructions

---

## Milestones

| # | Milestone | Description | Dependencies |
|---|-----------|-------------|--------------|
| E1 | Last.fm + Profile Endpoint | `lastfm_client.py`, `song_profile.py`, config wired | None |
| E2 | Explore Page + Song Profile UI | Route, `SongSearch`, `SongProfile`, `TagPill` | E1 |
| E3 | Discovery | Wire tag selection → `/llm/generate-playlist/` → `PlaylistResult` | E2, LLM connected |

---

## API Shapes

### GET /song/profile/
```
Request:  ?title=Bohemian+Rhapsody&artist=Queen
Response: {
  "title": "Bohemian Rhapsody",
  "artist": "Queen",
  "tags": [
    { "name": "classic rock", "url": "..." },
    { "name": "epic", "url": "..." }
  ],
  "listeners": 4200000,
  "play_count": 18000000,
  "wiki_summary": "...",      // may be empty string for obscure tracks
  "analysis": "..."           // LLM prose, 2-3 sentences
}
```

**LLM system prompt for song analysis:**
> You are a music expert. Given a song title, artist, and any available listener tags, write a structured analysis covering: Mood, Instrumentation, Lyrical Themes, Era, and Cultural Context. Each field should be 1-2 sentences. If tags are provided, ground your analysis in them. If tags are absent or sparse, use your own knowledge. Return each field as a labeled line (e.g. "Mood: ..."), nothing else.

**Discovery prompt construction (frontend → `/llm/generate-playlist/`):**
```
Using "[title]" by [artist] as a reference point, find 12 songs that share these qualities: [selected tag 1], [selected tag 2], [selected tag 3]. The reference song is: [LLM analysis]. Return songs that genuinely match these specific characteristics.
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Last.fm no match for song | Medium | Low | Return empty tags gracefully; LLM analysis still runs using just title + artist |
| Sparse tags for obscure tracks | High | Low | Show whatever tags exist; if fewer than 3, LLM prompt notes limited data |
| Last.fm API key missing | Low | High | FastAPI startup check; clear error message pointing to setup.md |
| LLM analysis slow (blocks profile load) | Low | Medium | Run Last.fm + LLM in parallel; Last.fm is fast so total latency is ~LLM latency only |
| Discovery results don't match selected tags | Medium | Low | Known LLM limitation; user can re-run or adjust selection |

---

## Dependencies

**New environment variable:**
```
LASTFM_API_KEY=your-lastfm-api-key
```
Get one at: https://www.last.fm/api/account/create (free, instant)

**No new Python packages** — Last.fm API is a simple REST call; use `httpx` (already available via FastAPI's ecosystem) or `urllib` directly.

---

## Open Questions

~~1. Should `SongSearch.svelte` also replace the search on the home page?~~ **Resolved: explore page IS the home page at `/`.**
~~2. Sparse Last.fm data — show LLM analysis or notice?~~ **Resolved: always show LLM analysis using structured template.**
~~3. Clicking discovery results — navigate or stay on page?~~ **Resolved: loads new song profile on same page (exploration chain).**

---

## Decisions Log

| Decision | Choice | Reasoning | Date |
|----------|--------|-----------|------|
| Discovery data source | Last.fm tags + LLM interpretation | Spotify audio features deprecated; Last.fm is free, stable, and tag-based data maps to how users actually think about music | 2026-06-05 |
| Song profile endpoint | Single endpoint, parallel Last.fm + LLM calls | Avoids frontend waterfall; one request, complete response | 2026-06-05 |
| Discovery pipeline | Reuse `/llm/generate-playlist/` | No new backend needed; richer prompt context is the only difference | 2026-06-05 |
| Visualization | Tag pills only, radar chart deferred | Tag data is categorical not numeric; pills are honest to the data; radar revisited when numeric data available | 2026-06-05 |
| Free text on explore page | Out of scope | Belongs to playlist builder (Pillar 2); explore page is song-centric only | 2026-06-05 |
| Home page | Replaced by explore page at `/` | Old home page had no purpose after recommendations deprecated; explore is the primary surface | 2026-06-05 |
| Nav structure | Explore \| Playlist Builder \| Profile | Home removed; Explore at root is the app's primary entry point | 2026-06-05 |
| Discovery result click | Load new song profile on same page | Creates natural exploration chain; no navigation away from the page | 2026-06-05 |
| LLM analysis when data sparse | Structured template always shown | LLM fills in Mood/Instrumentation/Era/Themes/Context from its own knowledge; consistent format regardless of Last.fm data quality | 2026-06-05 |
