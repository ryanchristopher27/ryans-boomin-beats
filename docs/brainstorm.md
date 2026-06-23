# Brainstorm: LLM Playlist Generation
_Date: 2026-06-04 | Feature: AI-powered playlist builder_

---

## Problem / Opportunity

Ryan's Boomin Beats is a Spotify-integrated web app (SvelteKit + Django) that lets users explore music, search tracks, and get Spotify-seeded recommendations. The existing recommendation engine is constrained to Spotify's own similarity model — it requires a seed track and stays within Spotify's catalog graph.

The opportunity: let users describe what they want in natural language and have an LLM generate a tailored playlist that isn't tied to Spotify's recommendation logic. A user should be able to say "songs for a late-night drive in the rain" or "build me something like Kendrick's moody instrumentals but with more jazz influence" and get a curated, playable result.

---

## Goals

- Natural language prompting (one-shot or conversational) generates a song list
- Songs are validated against Spotify's catalog and surfaced in the app
- User can select individual songs, add the full list as a Spotify playlist, or queue everything to their active player
- Support Claude (Anthropic) and OpenAI as LLM providers via user-supplied API keys
- Session-based key storage initially; persistence deferred to a future auth layer

---

## Audience

Personal / developer use initially — the owner building and running this locally. Designed to scale to shared use later with minimal rework (BYOK already anticipates multi-user scenarios).

---

## Constraints

- **BYOK only:** no app-level LLM key; user must supply their own
- **Session-based key storage** in v1 — no DB writes, no user identity required yet
- **Existing stack:** SvelteKit frontend, Django backend, Spotipy, Python
- **New Spotify OAuth scopes required:**
  - `playlist-modify-private` — create playlists on user's account
  - `user-modify-playback-state` — add songs to active playback queue (requires an active Spotify device)
- Direction C (LLM → Spotify recommendation params) explicitly out of scope — the goal is to escape Spotify's recommendation graph, not stay within it

---

## Ideas & Directions

### Direction A: LLM → Structured Output → Spotify Validation ✅ Selected for v1

1. User writes a prompt (e.g., "moody jazz for 3am")
2. Backend sends prompt (+ chat history for conversation) to the selected LLM
3. LLM returns a structured JSON list: `[{ "title": "...", "artist": "...", "reason": "..." }]`
4. Backend fires parallel Spotify searches for each `{title, artist}` pair
5. Matched songs surface with Spotify track data (album art, ID, URL)
6. Unmatched songs are flagged — user can manually swap them out
7. User acts on the result: select songs, add as playlist, or queue all

**Why this wins:** Fast to build, fast to run (parallel searches), naturally supports conversation (just send message history), and gives the user visibility into misses rather than silently dropping songs.

**Hallucination handling:** For each `{title, artist}`, search Spotify as `track:{title} artist:{artist}`. If top result confidence is low or empty, flag with "Not found on Spotify" — allow user to search and swap manually.

---

### Direction B: LLM + Tool Use / Function Calling (Upgrade Path)

- LLM is given a `search_spotify(query)` tool it calls before adding each song
- Every song in the final list is confirmed to exist before returning
- Higher accuracy, zero hallucinated songs
- More latency (sequential tool calls), more complex plumbing

Not selected for v1 but the natural upgrade path once A is shipped and the "not found" rate is measured.

---

## Architecture

### Backend — New Django Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/llm/connect` | POST | Validate provider + API key, store in Django session |
| `/api/llm/generate-playlist` | POST | Prompt LLM, validate results against Spotify, return merged list |
| `/api/spotify/create-playlist` | POST | Create playlist on user's Spotify account (`playlist-modify-private`) |
| `/api/spotify/queue` | POST | Add songs to active playback queue (`user-modify-playback-state`) |

### Frontend — New SvelteKit Components / Routes

- **LLM settings panel** — provider selector (Claude / OpenAI) + API key input; validate on submit; session persists until reload
- **Chat / prompt interface** — text input, scrollable message history, shows both user prompts and assistant responses
- **Playlist result view** — song cards with album art, title, artist, match status badge, select checkbox
- **Action bar** — "Add All as Playlist", "Queue All", "Add Selected to Playlist", "Queue Selected"

### Spotify OAuth Scope Upgrade

Add to the existing `SCOPE` variable in all Django views:

```
playlist-modify-private user-modify-playback-state
```

Queue endpoint note: `user-modify-playback-state` requires an active Spotify device. If none is active, return a clear error the UI can surface to the user ("Open Spotify on a device first").

---

## LLM Output Format

System prompt instructs the LLM to return only valid JSON in this shape:

```json
[
  {
    "title": "Song Name",
    "artist": "Artist Name",
    "reason": "One sentence on why this fits the prompt"
  }
]
```

The `reason` field displays as subtext or a tooltip on each song card — gives the playlist a curated feel and helps users understand picks they don't recognize.

---

## Conversational Flow

- Frontend maintains a `messages` array: `[{ role: "user" | "assistant", content: "..." }]`
- Each new prompt appends to the array; full history sent to backend on every turn
- LLM receives full history and returns a **complete revised playlist** (not a delta) — simpler to render and avoids merge complexity
- Chat history resets on page reload in v1 (session-based; persistence is a future concern)

---

## Enhancement: Personalization via Account Analysis

The app already has an account analysis feature. The LLM system prompt could optionally include the user's top artists and genres from that feature to bias recommendations toward their actual taste. This is a low-effort, high-impact upgrade to layer on top of the base feature.

---

## Recommendations

**Ship Direction A with Spotify validation.** The LLM generates the list fast, parallel Spotify searches confirm existence, and flagged misses give the user control without blocking them. Conversational mode is a thin layer on top — just maintain message history on the frontend and send it along.

**Start one-shot, add conversation in the same pass.** The only meaningful difference is tracking `messages` state in the Svelte store. Not worth splitting into two releases.

**Use Django session for key storage.** Avoids building any auth or encryption infrastructure in v1. When persistence becomes a goal, that's the moment to introduce user accounts.

---

## Suggested Decisions (All Confirmed)

- [x] BYOK, session-based storage in v1
- [x] Direction A: LLM structured output + Spotify validation pass
- [x] Claude (Anthropic) + OpenAI as supported providers
- [x] Result displayed in app — user can select, add as playlist, or queue
- [x] New Spotify OAuth scopes: `playlist-modify-private`, `user-modify-playback-state`
- [x] One-shot and conversational both supported in v1

---

## Open Questions for /plan

- What does the LLM settings UI look like? Modal, sidebar panel, or a dedicated `/settings` route?
- Where does the chat interface live in the app? New route, drawer, or embedded on an existing page?
- How is the LLM system prompt crafted? What context does it receive beyond the user's message?
- Should the system prompt optionally include the user's top artists/genres from account analysis?
- What's the retry strategy for Spotify search misses before flagging as "not found"? (e.g., try again without `artist:` filter)
- Does conversation history persist across navigation, or only within a single session on one page?
- How many songs should the LLM target by default if the user doesn't specify? (Suggest: 10–15)

---

## Next Steps for /plan

1. Define new Django apps + endpoint signatures in detail
2. Map SvelteKit route/component structure for the new UI
3. Write the LLM system prompt template (including output format enforcement)
4. Define the Spotify search + validation logic (query format, confidence thresholds, retry strategy)
5. Plan the OAuth scope upgrade path and session key storage implementation
6. Decide on UI placement and flow for the chat + result views

---

# Brainstorm: Song Exploration & Discovery (Pillar 1)
_Date: 2026-06-05 | Feature: Explore page — song profile + tag-driven discovery_

---

## Problem / Opportunity

The app has two pillars: song-centric exploration and prompt-based playlist creation. Pillar 2 (LLM playlist builder) is scaffolded. Pillar 1 needs its own feature: given a specific song, show the user what makes it what it is, and let them discover similar songs based on the aspects they care about.

Spotify's recommendations and audio features endpoints are deprecated for new apps, removing the obvious data source. The replacement: **Last.fm as the structured data layer, LLM as the interpretation and discovery engine.**

---

## Goals

- User can search for any song using Spotify's autocomplete
- App builds a rich profile of that song: LLM qualitative analysis + Last.fm tags and metadata
- User selects which aspects (tags) they want to match in discovery
- App generates a list of similar songs based on selected tags + song context
- Results are validated against Spotify and displayed with the same save/queue actions as Pillar 2

---

## Audience

Same as Pillar 2 — personal/developer use initially. The explore page is the primary discovery surface for song-centric users (vs. vibe/prompt-centric users who go to the playlist builder).

---

## Constraints

- Spotify recommendations and audio features endpoints are unavailable for new apps
- Last.fm API requires a free API key (5-minute signup) — added to `.env`
- Discovery stays song-centric on the explore page — free text input belongs to Pillar 2 (playlist builder), not here
- Tag pills are the primary discovery affordance — radar chart deferred to a future visual pass
- Reuse existing playlist builder pipeline for discovery results (same backend endpoints, richer LLM context)

---

## Confirmed Decisions

| Decision | Choice |
|----------|--------|
| Home page | Search-only for now; explore page is the destination. Home page filled in later. |
| Song profile display | Last.fm tag pills + LLM prose analysis. Radar chart deferred. |
| Discovery input | Spotify autocomplete song search — tag selection drives discovery. No free text on this page. |
| Last.fm API | Yes — free key added to project |

---

## Architecture

### Explore Page Flow

1. User lands on `/explore`
2. Spotify autocomplete search (reuses existing `/search/` endpoint)
3. User selects a song → app fetches song profile
4. Song profile displays: LLM analysis prose + Last.fm tag pills + metadata (listeners, play count)
5. User selects tags they want to match (pills are toggleable)
6. User clicks "Discover" → backend calls LLM with song context + selected tags → iterative Spotify validation → results displayed
7. User can save as playlist or queue — same `PlaylistResult` component as Pillar 2

### New Backend

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/song/profile/` | GET | Fetch Last.fm data + LLM analysis for a given title + artist |

**`routers/song_profile.py`** — calls Last.fm `track.getInfo`, passes tags + metadata to LLM, returns structured profile

**`services/lastfm_client.py`** — Last.fm API wrapper: `track_info(title, artist)` returns tags, listeners, wiki summary, similar tracks

**LLM system prompt for song analysis:** Given the song title, artist, and Last.fm tags, produce a 2-3 sentence qualitative description of the song — mood, instrumentation, lyrical themes, era, cultural context. Ground the analysis in the provided tags. Return as plain prose (no JSON).

**Discovery reuses existing `/llm/generate-playlist/` endpoint** — the explore page calls it with a richer system context: song title, artist, selected tags, and LLM analysis as grounding.

### New Frontend

| File | Purpose |
|------|---------|
| `routes/explore/+page.svelte` | Main explore page |
| `lib/components/SongSearch.svelte` | Spotify autocomplete — reusable, extracted from home page logic |
| `lib/components/SongProfile.svelte` | Tag pills + LLM prose + Discover button |
| `lib/components/TagPill.svelte` | Selectable/toggleable tag pill |

**Reused from Pillar 2:** `PlaylistResult.svelte`, `SongCard.svelte` — discovery results render identically to playlist builder output.

### Last.fm API

- Endpoint used: `track.getInfo` (title + artist → tags, listeners, play count, wiki summary)
- Fallback: `artist.getTopTags` if track-level tags are sparse
- API key stored in `.env` as `LASTFM_API_KEY`, read via `config.py`
- No auth beyond API key — free tier is sufficient

---

## What's Not Solved Yet (For /plan)

- **Last.fm matching edge cases** — Last.fm takes title + artist as strings; non-English titles, featuring credits, and remaster titles can cause misses. Need a fallback strategy.
- **Sparse data for obscure songs** — Last.fm tags and LLM knowledge both degrade for less-known tracks. Acknowledged as a known limitation; surface gracefully in UI rather than hiding it.
- **Home page interim state** — the home page currently has search + broken recommendations. Decide what it shows while the explore page is being built. Simple landing / nav redirect is fine for now.
- **SongSearch component** — the autocomplete logic currently lives inline in `+page.svelte`. Extracting it to `SongSearch.svelte` makes it reusable across home and explore pages; decide if this extraction happens in this milestone or later.
- **Navigation** — how does a user get from search results to the explore page? Clicking a song in autocomplete results navigates to `/explore?title=...&artist=...&id=...` with query params.

---

## Recommendations

1. **`/explore` as a new dedicated route** — substantial enough for its own page; query params carry song context so URLs are shareable
2. **Last.fm + LLM profile on a single backend call** — `GET /song/profile/` fetches Last.fm data and calls the LLM in parallel, returns both in one response to avoid frontend waterfall
3. **Tag pills as the primary discovery affordance** — all selected tags get passed as context to the existing `/llm/generate-playlist/` endpoint; no new discovery pipeline needed
4. **Extract `SongSearch` component now** — it will be needed on both the home page (eventually) and explore page; cleaner to extract once than copy-paste

---

## Next Steps for /plan

1. Define `GET /song/profile/` endpoint signature and response shape
2. Define `services/lastfm_client.py` interface
3. Map the LLM prompt template for song analysis (inputs: title, artist, tags, wiki summary → output: prose analysis)
4. Define how selected tags are passed to `/llm/generate-playlist/` — new field in request body or modified prompt construction
5. Map the explore page component tree and data flow
6. Decide on home page interim state during this build
7. Plan Last.fm API key addition to `.env`, `config.py`, and `setup.md`

---

# Frontend Redesign — Sleek Dark Theme (2026-06-22)

## Problem / Opportunity
The current frontend is visually inverted from modern music apps: a light-blue background with dark cards, Arial typography, and inconsistent polish across pages (the profile page lags noticeably behind the explore page). The app works end-to-end but doesn't *look* the part. The opportunity is a cohesive visual redesign that reads as sleek and premium — using Spotify's design language as a proven reference, not a pixel-perfect target.

## Goals
- A sleek, polished, cohesive look across the entire app
- Dark, layered surfaces (Spotify-like depth via elevation)
- Use the existing `#5ec9ff` light blue as the single accent color
- Bring every page up to a consistent quality bar
- Keep it tasteful and restrained — premium over busy

## Audience
Primary user is Ryan (personal project), but the design bar is "something you'd be proud to show off."

## Constraints
- Keep the existing `#5ec9ff` accent — this is the brand anchor
- SvelteKit component structure already exists; redesign should reuse structure where sound, not rebuild from scratch
- No proprietary fonts (Spotify's Circular is licensed) — use a free geometric sans
- Local dev only; no responsive/mobile mandate beyond what already exists (min-width 800px)

## Ideas & Directions

### Direction A — Token swap + polish (low effort)
Flip global color tokens so the background goes dark and blue becomes accent-only. Most components already use `--color-dark-gray` for cards and `--color-light-blue` for accents, so flipping the page background gets ~70% there. Clean up rough edges after. Fast, low-risk, but stops short of "genuinely polished."

### Direction B — Full Spotify structural clone (high effort)
Dark background + left sidebar nav (Library/Explore/Builder). Closer to how Spotify actually feels, but a big layout restructure that's overkill for a 3-page app with no persistent "now playing" concept.

### Direction C — Dark + top nav, full component rewrite (medium effort) [CHOSEN]
Dark layered background, keep and slim down the top header, full styling pass on every component: typography upgrade, consistent card radius + hover states, refined buttons, spacing rhythm. Bigger than A, smaller than B. Lands the "sleek" goal without a structural rewrite.

## Recommendations
Go with **Direction C**, tuned by the confirmed decisions below:

- **Surfaces:** layered dark — `#0a0a0a` page → `#181818` cards → `#282828` hover. Depth-via-elevation is the biggest "sleek" lever.
- **Accent:** minimal/monochrome. Mostly grayscale dark UI; `#5ec9ff` reserved for active states, primary buttons, and links. Restraint reads as intentional.
- **Typography:** swap Arial → **Inter**. Heading weights 600–700, comfortable body line-height.
- **Components:** full pass — consistent radius, real hover transitions, refined buttons, better spacing. Profile page brought up to explore-page quality.
- **Nav:** keep top header, slim it down, cleaner active state.
- **Motion:** subtle — smooth hover transitions, gentle fades on results loading. Tasteful, not flashy.
- **Scope:** everything this round — global tokens + all pages + every component, one cohesive pass.

## Suggested Decisions (confirmed)
- [x] Direction C — dark, polished, top nav
- [x] Accent intensity: **minimal / monochrome**
- [x] Scope: **everything** (tokens + all pages + all components)
- [x] Motion: **subtle**
- [x] Keep top navigation (no sidebar)
- [x] Typography: Inter (pending final confirmation in plan)

## Open Questions (for /plan to resolve)
- Final font choice: Inter vs. DM Sans (both free, geometric) — lock one
- Exact surface/elevation token values and naming (`--surface-0/1/2`?)
- Whether to introduce semantic tokens (`--surface`, `--text-primary`, `--text-muted`, `--accent`) vs. keep the current raw color names
- Build order across components to minimize churn (design system → shell/header → pages)
- How to handle the legacy `styles.css` light-theme tokens (`--color-bg-0/1/2`, `--color-theme-1/2`) — remove or repurpose
- Profile page is the roughest — does it need structural changes or just restyle?

## Next Steps (what /plan needs)
1. Lock the final type + token system (semantic naming, surface elevation values)
2. Define the build order (design system first, then shell, then pages)
3. Inventory every component + page that needs a pass
4. Decide the legacy `styles.css` cleanup approach
5. Set acceptance criteria for "sleek" (consistency checklist: radius, spacing, hover, type scale)

---

# Cover Art on Playlist Results (2026-06-23)

## Problem / Opportunity
The discovery results (and later the Playlist Builder results) are a plain list of song rows on a flat surface. Album art is available per song but unused at the playlist level. Adding the cover art as a larger visual element would make the results feel richer, more immersive, and more on-brand — without changing the underlying functionality.

## Goals
- Make the playlist/discovery results visually richer using album cover art
- Keep it aesthetically pleasing and cohesive with the sleek dark theme (priority: looks)
- Tie the results visually + semantically to their source (the selected song)
- Stay readable — album art is unpredictable (bright/busy), text must remain legible

## Audience
Personal project; the bar is "something that looks polished enough to show off."

## Constraints
- A generated playlist has **no single cover** — it's many songs with many covers. The chosen anchor is the **selected/reference song's** cover, not the playlist's.
- `PlaylistResult` is shared by Explore discovery results AND the Playlist Builder — changes must be gated/optional so Explore can adopt first.
- **Key prerequisite:** the selected song's cover image is not reliably available today. The search-select path provides `image` (after the recent `search.py` change), but the Explore→ chain rebuilds the next song as `{title, artists, id}` and drops the image, and `/song/profile/` returns no image. The image must be threaded through both selection paths.
- Dark scrim / gradient mask required for text contrast over arbitrary covers.

## Ideas & Directions

### Source image (which cover anchors the visual)
- **Selected/reference song's cover [CHOSEN]** — on Explore, the song you explored from; semantically perfect as the anchor for "similar songs"
- First/top result's cover — simplest, used as the Builder fallback later
- 2×2 mosaic of 4 covers — Spotify-style auto-cover; busier as a background
- Dominant color extracted from art — sleekest ambient look, but needs canvas + CORS work

### Treatment (how it appears)
- **Ambient blurred backdrop + "Based on" band [CHOSEN]** — selected song's cover, heavily blurred at low opacity, bleeding from the top of the results container and fading into `--surface-1` via a gradient mask, dark scrim for readability. Layered on top: a crisp cover thumbnail + "Based on *Song* by Artist" replacing the current "Similar Songs" header.
- Hero header only — crisp cover + meta, no wash (cleanest, less immersive)
- Blurred backdrop only — no crisp header (simplest)

## Recommendations
Build the **ambient blurred backdrop + "Based on" header**, anchored to the **selected song's cover**, scoped to **Explore discovery results** first, with `PlaylistResult` taking an optional cover prop so the Builder can adopt it later (first-song cover).

Rationale: matches the user's "large with opacity in the background" instinct, ties results to their source, stays immersive but readable, and avoids the cost/complexity of color extraction or per-row art treatments. The gradient-masked fade + scrim keeps it tasteful on any cover.

## Suggested Decisions (confirmed)
- [x] Source = selected/reference song's cover
- [x] Treatment = ambient blurred backdrop + crisp "Based on" thumbnail header (aesthetic call delegated to assistant)
- [x] Scope = Explore discovery results now; extend to Playlist Builder later
- [x] Enabling change = thread the selected song's image through search-select + explore-chain paths

## Open Questions (for /plan)
- Builder's later source image: first-song cover vs 2×2 mosaic (defer; note it)
- Backdrop tint: neutral dark scrim (simpler) vs subtle tint toward the cover's dominant color (nicer, more work) — lean neutral for v1
- Exact placement of the "Based on" header: inside `PlaylistResult` vs the Explore page's existing "Similar Songs" header slot
- Fallback when no cover image is available (e.g., older selections): graceful no-backdrop state

## Next Steps (what /plan needs)
1. Define how the selected song's `image` is propagated (SongSearch already; SongCard explore button + `onExploreSong` need to carry it; consider persisting on `selectedSong`)
2. Decide `PlaylistResult` API: optional `coverImage` + `coverLabel`/`coverSubtitle` props
3. Spec the backdrop layering (absolute blurred img, gradient mask, scrim, z-index) within the existing `.result-container`
4. Map the "Based on" header markup + where it lives
5. Acceptance criteria: readable on bright covers, graceful no-image fallback, no layout shift
