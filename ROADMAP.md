# Ryan's Boomin Beats — Roadmap

## Context

Ryan's Boomin Beats is a personal Spotify companion that turns your listening life into something you own and can query, edit, and explore with an LLM — all running locally on Apple Silicon.

Four intertwined goals:
1. **Playlist curation & editing** — deep inspection and non-destructive edits on your Spotify playlists.
2. **Discovery & recommendation** — grounded in *your* history, not the generic Spotify graph.
3. **Listening analytics** — the "Wrapped anytime, sliced any way" dashboard.
4. **Natural-language DJ** — chat with a local LLM that has tools to search your library, build playlists, and control playback.

Current scaffold (reported, not yet audited): Spotify OAuth + API client, SvelteKit frontend with routing/layout, FastAPI backend skeleton. **Phase 0 audits the real repo state**; every later phase is expected to be pruned, reordered, or expanded once the audit lands.

---

## Target architecture

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (Python 3.11+) | Already scaffolded; async is a good fit for Spotify + LLM streaming. |
| Frontend | SvelteKit | Already scaffolded. |
| Primary store | **Postgres + pgvector**, run locally via Docker; hosted via Supabase or Neon | Same schema local and hosted; pgvector unlocks lyric/vibe semantic search from the local LLM. Overkill vs SQLite, but the DJ + discovery features lean hard on embeddings so it earns its keep. |
| Cache / rate-limit | Redis | Spotify response cache, sync cursors, rate-limit buckets. |
| Task queue | `arq` (Redis-backed) | Background syncs, embedding jobs, lyric backfill. |
| LLM runtime | **Ollama** on the host Mac | M-series Metal acceleration; simple lifecycle. |
| Chat model | **Qwen 2.5 14B Instruct** (Q4_K_M) as primary; **Llama 3.2 3B** for fast tool-routing | 14B fits in ~9GB, good tool-use quality on M-series. 3B for cheap classifier/router calls. |
| Embeddings | **`nomic-embed-text`** (768-d) via Ollama | Fast, good for lyric + tag search; single model keeps things simple. |
| LLM interface | `litellm` proxy in front of Ollama | Provider-agnostic backend code; drop-in swap to Anthropic/OpenAI in hosted mode. |
| Auth | Spotify OAuth (already working); single-user, no app-side accounts for v1 | Personal tool. |

---

## Data sources to connect

| Source | Purpose | Notes |
|---|---|---|
| **Spotify Web API** | Library, playlists, top items, audio features, recently-played, currently-playing, playback control | Poll `recently-played` every ~15 min — API only returns last 50. |
| **Last.fm** | Long-term scrobble history (Spotify only exposes ~50 recent) | Full backfill on first connect, then incremental. |
| **ListenBrainz** | Open-data alternative/complement to Last.fm | Cross-check + fill gaps. |
| **MusicBrainz** | Canonical IDs (MBID) for tracks/artists/releases via ISRC + name match | The join key that makes multi-source data coherent. |
| **AcousticBrainz** (or replay Essentia locally if AB stays offline) | Open audio features when Spotify's are missing or you want raw signal | Optional but nice. |
| **Genius** (via `lyricsgenius`) | Lyrics for semantic search + LLM context | Cache aggressively. |
| **LRCLIB** | Time-synced lyrics for the "now playing" widget | Free, no auth. |
| **Setlist.fm / Bandsintown** | Tour dates for artists in your rotation | Powers the concert-calendar view. |
| **YouTube Music** (via `ytmusicapi`) | Optional cross-service comparison / export | Nice-to-have. |

---

## Schemas (Postgres, illustrative)

Canonical entities are MBID-keyed; per-service IDs live in an alias table so nothing is Spotify-locked.

```
accounts(id, spotify_user_id, display_name, country, product, created_at)
spotify_tokens(account_id FK, access_token, refresh_token, expires_at, scopes)

artists(mbid PK, name, sort_name, disambiguation, formed_year, country, tags jsonb)
albums(mbid PK, title, release_date, artist_mbid FK, type)
tracks(mbid PK, title, primary_artist_mbid FK, album_mbid FK, duration_ms, isrc)

track_aliases(track_mbid FK, source enum('spotify','lastfm','listenbrainz','youtube'), external_id, UNIQUE(source, external_id))

audio_features(track_mbid PK, source, danceability, energy, valence, tempo, key, mode, loudness, acousticness, instrumentalness, speechiness, liveness, time_signature, fetched_at)

lyrics(track_mbid PK, source, text, language, fetched_at)

track_embeddings(track_mbid FK, kind enum('lyric','tag','audio'), embedding vector(768), model, created_at, PRIMARY KEY(track_mbid, kind, model))

plays(id, account_id FK, track_mbid FK, played_at, source enum('spotify','lastfm','listenbrainz'), context jsonb)
  -- indexed on (account_id, played_at desc)

playlists(id, spotify_id UNIQUE, account_id FK, name, description, collaborative, public, snapshot_id, cover_url, updated_at)
playlist_tracks(playlist_id FK, position, track_mbid FK, added_at, added_by, PRIMARY KEY(playlist_id, position))

taste_profile(account_id PK, summary text, preferences jsonb, do_not_play jsonb, updated_at)
  -- long-term facts the DJ remembers between chats

tags(track_mbid FK, tag, source, weight)  -- lastfm tags + user tags + LLM-generated

recommendations(id, account_id, track_mbid, generator, score, reason, surfaced_at, feedback smallint, feedback_at)

chat_conversations(id, account_id, started_at, summary)
chat_messages(id, conversation_id FK, role, content, tool_calls jsonb, tool_results jsonb, created_at)

sync_state(account_id, source, cursor, last_run_at, last_success_at)
```

Design notes:
- `plays` deduped by `(account_id, track_mbid, played_at)` with a small window tolerance across sources.
- All rollups (top artists, weekly minutes, streaks) computed on the fly from `plays` — materialized views only if a query gets slow.
- Embeddings stored per-model so you can swap embedding models without a destructive re-index.

---

## What the connected Spotify account should show

**Account header:** avatar, display name, product tier (Free/Premium — Premium gates playback control), country, follower/following counts, joined date, "linked since" for other sources.

**KPI tiles (windowable: 4w / 6m / 1y / all-time):**
- Total minutes listened, unique tracks, unique artists, unique albums
- Discovery rate (new-to-you artists per week)
- Longest listening session, current streak
- Library size (saved tracks), playlist count, followed artists

**Charts:**
- Top artists / tracks / albums / genres (rank + trend arrows vs previous window)
- Listening heatmap (hour × day-of-week)
- Timeline of daily minutes with genre stacking
- Genre sunburst
- Audio-feature radar: your average vs a chosen playlist/artist/era
- Repeat-listener chart (most-replayed tracks with play counts)
- "Wrapped anytime" comparison view — window A vs window B side by side

**Now-playing widget:** cover, title, artist, progress, time-synced lyrics (LRCLIB), audio-feature bars, "why this fits" one-liner from the LLM.

---

## Playlist inspection & modification

**List view** — every playlist with cover, size, duration, last modified, owner, collaborative flag; sortable + filterable.

**Detail view** — a tracks table with:
- index, art, title, artist, album, duration, added_at, added_by
- inline meters for energy/valence/danceability
- key + BPM columns for DJ-style sorting
- click-through to a track drawer with lyrics, features, similar tracks, play-history-in-this-playlist

**Editing:**
- Drag-to-reorder, bulk-select, remove, add-via-search
- Sort/filter by any audio feature, era, artist, key, BPM range
- Non-destructive **diff view** — every LLM-proposed edit renders as add/remove/move rows with per-row accept/reject before it hits Spotify
- **Playlist recipes** — save a set of filters + prompts as a named recipe that regenerates the playlist on demand ("Sunday morning coffee: 60–90 BPM, high valence, low energy, minimum 5 years old, ≤2 tracks per artist")

**Safety rails:**
- Every mutation writes a snapshot to `playlist_snapshots` so any edit is undoable within N days
- Spotify's `snapshot_id` used as an optimistic-lock; conflicts surface a diff instead of clobbering

---

## Local LLM & DJ chat

**Model layout:**
- `qwen2.5:14b-instruct-q4_K_M` — primary chat + tool use
- `llama3.2:3b-instruct-q4_K_M` — fast router / classifier for cheap decisions
- `nomic-embed-text` — embeddings

**Orchestration:** small in-house tool loop (nothing fancy — LangGraph if you want a state machine later). All tool calls + results logged to `chat_messages` for replay and eval.

**Tools exposed to the DJ:**

| Tool | Purpose |
|---|---|
| `search_library` | Query your saved tracks / playlists by text or filters |
| `semantic_track_search` | pgvector nearest-neighbor over lyric/tag embeddings |
| `get_audio_features` | Fetch features for one or many tracks |
| `get_similar_tracks` | Blend Spotify recs + Last.fm similar + embedding neighbors |
| `build_playlist` | Create a new playlist from a spec |
| `add_to_playlist` / `remove_from_playlist` / `reorder_playlist` | Mutations (always via the diff-review flow) |
| `get_stats_summary` | Structured account analytics for a window |
| `play` / `pause` / `skip` / `queue` | Playback control (Premium) |
| `remember` / `forget` | Update `taste_profile` (do-not-play list, preferences) |

**Session memory:** each conversation gets a rolling summary; durable facts land in `taste_profile`.

---

## Roadmap (execution order)

### Phase 0 — Audit the current repo (do this first)

Everything below Phase 0 is speculative until this audit runs. A local agent with read access to `ryans-boomin-beats/` produces a short **State-of-the-Repo** report answering:

**Layout & tooling**
- Actual top-level layout (`tree -L 3 -I 'node_modules|__pycache__|.venv|.svelte-kit|dist|build'`)
- Package managers (`pyproject.toml` / `requirements.txt` / `poetry.lock` / `uv.lock`; `package.json` / `pnpm-lock.yaml` / `bun.lockb`) and pinned Python + Node versions
- Lint/format/test config present (`ruff`, `mypy`, `pytest`, `vitest`, `playwright`, `pre-commit`)
- Any `docker-compose.yml`, `Dockerfile`, `Makefile`, `justfile`, or `scripts/`
- CI workflows in `.github/workflows/`

**Backend**
- Framework confirmed (FastAPI? Flask? Starlette?) and app entrypoint
- Route inventory (path, method, one-line purpose)
- Spotify client: which library (`spotipy`, `tekore`, hand-rolled?), which scopes requested, token-storage mechanism
- Data layer: any ORM (`SQLAlchemy`, `SQLModel`, `Prisma`)? Any migrations? What DB is configured?
- Existing models / schemas / services / background tasks
- Config approach (`pydantic-settings`? `.env` loader? hard-coded?)
- Tests present, and what they cover

**Frontend**
- SvelteKit version + adapter; TS or JS
- Route tree (`src/routes/**`), shared layout, stores (`src/lib/stores`), API client (`src/lib/api` or similar)
- UI kit (`shadcn-svelte`, `skeleton`, `bits-ui`, plain CSS, Tailwind?)
- Auth flow on the frontend (how OAuth redirect + session is handled)
- Any existing views for account / playlists / analytics / chat

**Integrations & data**
- What's already wired beyond Spotify (Last.fm? Genius? Ollama?)
- Any local data files, fixtures, or cached responses committed to the repo
- Any secrets in `.env.example` or docs that reveal intended integrations

**Deliverable of Phase 0:** a `docs/state-of-repo.md` (or comment on this roadmap) with:
1. A **Done** list — features/infra that exist and work
2. A **Partial** list — scaffolded but not wired end-to-end, with the gap named
3. A **Missing** list — nothing there yet
4. A **Delete/rework** list — code that conflicts with the target architecture and should be removed or refactored

Then revise this roadmap: strike any Done items, promote Partial items into their owning phase with a "finish X" scope, and keep Missing items where they are.

### Phase 1 — Foundations
- Repo layout: `backend/`, `frontend/`, `infra/`, `scripts/`, `docs/`
- `docker-compose.yml`: Postgres+pgvector, Redis, backend, frontend, litellm
- Alembic migrations for the schema above
- `pydantic-settings` config; `.env.example` covering Spotify, Last.fm, Genius, Ollama URL
- Structured logging (`structlog`) with request IDs
- Rate-limit + retry middleware wrapping the Spotify client (respect `Retry-After`)

### Phase 2 — Data pipeline
- Idempotent syncers per source, cursor-tracked in `sync_state`
- Spotify: library, playlists, top items, audio features, recently-played (15-min poll)
- MBID resolver (ISRC → MusicBrainz recording → canonical row)
- Last.fm full backfill + incremental
- Lyric fetcher on-demand with cache; embed on ingest

### Phase 3 — Analytics dashboard
- Backend endpoints for KPIs and charts (all windowable)
- Svelte pages for account header, KPIs, top-N, heatmap, timeline, sunburst, radar
- Now-playing widget with LRCLIB sync
- Contract: OpenAPI schema exported, frontend consumes it via `openapi-typescript`

### Phase 4 — Playlist inspection & edit
- List + detail views
- Sort/filter/reorder/remove/add
- Snapshot table + undo
- Diff-review component (used later by the DJ)

### Phase 5 — Local LLM stack
- Ollama install script + model pulls in `scripts/setup-llm.sh`
- litellm config; backend client that speaks OpenAI-shape
- Tool loop + tool registry
- Chat UI in Svelte with streamed responses + tool-call inspector

### Phase 6 — DJ chat wired to real tools
- Connect tools to real endpoints; every mutation routes through the diff-review
- Golden-set eval: ~20 canonical prompts → expected tool sequences, run in CI
- `taste_profile` read/write via `remember`/`forget`

### Phase 7 — Discovery & recommendations
- Candidate generators (Spotify recs, Last.fm similar, embedding neighbors, ListenBrainz)
- LLM ranker with one-line "why"
- 👍/👎 feedback stored, fed back as ranker context

### Phase 8 — Background jobs
- `arq` workers: nightly full sync, hourly recent-plays, weekly Last.fm backfill, on-demand lyric+embed
- Launchd plists for pure-local operation without Docker (optional)

### Phase 9 — Hosted deployment (optional)
- Backend on Fly.io (iad); Postgres on Supabase or Neon (pgvector enabled); frontend on Vercel/Cloudflare Pages
- `LLM_BACKEND=local|remote` toggle: local uses Ollama over Tailscale from the hosted backend; remote falls back to Anthropic/OpenAI via litellm
- Secrets via 1Password CLI locally, Fly secrets in prod

### Phase 10 — Polish & nice-to-haves
- Concert calendar (setlist.fm / bandsintown)
- "Vibe search" — natural-language mood → embedding query → ranked playlist
- Blend view — compare your taste to a friend via shared Last.fm
- Weekly discovery digest (notification / email)
- Export playlists to YouTube Music / Apple Music
- `beats` CLI for scripting

---

## Improvements to the existing scaffold (do alongside Phase 1)

- Type-check: `mypy --strict` on backend; TypeScript `strict: true` on frontend
- Lint/format: `ruff` + `black` (backend), `prettier` + `eslint` (frontend), all via `pre-commit`
- Tests: `pytest` + `pytest-asyncio` (backend), `vitest` + Playwright (frontend)
- Spotify contract tests recorded via `vcr.py` so CI doesn't hit the real API
- `.env.example` complete and documented in `docs/setup.md`
- Session-start hook (Claude Code on the web) that runs `pytest -q` and `pnpm test` for fast feedback

---

## Verification (how to know it's real)

End-to-end walkthrough that should work after each major phase:

1. `docker compose up` → all services green
2. Log in with Spotify → OAuth completes, tokens persist
3. Initial sync finishes → library, playlists, recent plays populated; row counts logged
4. Open dashboard → KPIs match what Spotify's own client shows for the same window (spot-check)
5. Open a playlist → tracks render with audio-feature meters; reorder → change persists to Spotify
6. Open the DJ chat → "make me a 45-minute focus playlist from my library, 90–110 BPM, low vocals" → diff-review shows proposed tracks → accept → playlist appears in Spotify
7. Currently-playing widget updates within 5s of skipping in the Spotify app
8. `pytest`, `pnpm test`, and the LLM golden-set eval all pass in CI

---

## Open questions to answer as you go

- Do you want the hosted deployment ever, or is local-only the long-term stance? (Affects how hard to push the "same schema, both places" line.)
- Single-user forever, or leave a door open for a partner/family account? (Affects whether `account_id` stays a stub or becomes real from day one.)
- How aggressive on lyric embedding coverage — every track ever played, or only saved/playlisted? (Cost vs. recall trade-off.)

---

## Questions the Phase 0 audit should also resolve

These are questions I would have answered from code inspection if this session could see the repo. Bake them into the State-of-the-Repo report:

- Which HTTP framework is actually in use, and is `async def` used throughout, or is anything sync-blocking on Spotify calls?
- Which Spotify client library (if any)? If hand-rolled, does it already do token refresh + retry-on-429?
- Is there a database configured yet, and if so which one? If SQLite, is anything blocking a move to Postgres (raw SQL, SQLite-only features)?
- Does the frontend already have a typed API client generated from the backend, or are types hand-maintained?
- Is there a chat/LLM code path in either half of the stack yet, even stubbed?
- Are there tests? If yes, do they hit the network, or are Spotify responses mocked/recorded?
- Is Ollama assumed to be running, or does the backend try to manage its lifecycle?
