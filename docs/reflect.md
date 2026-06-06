# Reflect — LLM Playlist Builder: Brainstorm → Scaffold + FastAPI Migration
Date: 2026-06-05
Type: Session
Phase context: /brainstorm → /plan → cleanup → /scaffold → environment setup → debugging

---

## Accomplished

- Full brainstorm and plan for the LLM playlist builder feature (4 milestones, all decisions confirmed)
- Header nav refactored from brittle if/else chain to array-driven pattern before scaffold
- Full FastAPI migration from Django (7 routers, 2 services, CORS + session middleware)
- 6 new SvelteKit components scaffolded (LLMSettingsPanel, ChatInterface, SongCard, PlaylistResult, PlaylistNameModal, playlist-builder page)
- conda environment, requirements.txt, environment.yml, .env setup with python-dotenv
- Spotify OAuth modernized: implicit grant → Authorization Code + PKCE
- Profile page working end-to-end on new FastAPI backend

---

## What Worked

- **Brainstorm → plan pipeline was tight.** Decisions compounded cleanly. By the time scaffold started, every significant choice was already locked — no mid-scaffold surprises from ambiguity.
- **Catching the FastAPI migration before scaffold.** The user raised it as a question mid-preview. Pausing to think through the hybrid vs. full migration tradeoff (and choosing full migration) was the right call. Django views were thin enough that the migration cost was low; the async benefit for the LLM feature is real.
- **Header cleanup before scaffold.** The if/else nav refactor took five minutes and prevented scaffolding onto a pattern we'd want to change. Small investment, clean result.
- **Reading both auth flows before planning.** The existing code had two separate Spotify auth paths (app credentials for search/recs, user token for profile). Catching that early shaped how the new spotify_actions endpoints were designed.

---

## What Didn't Work

- **Port hardcoding throughout the frontend.** Every fetch call has `http://127.0.0.1:8005` hardcoded. Changing the port required a grep-and-replace across 7 files. Should be a single shared constant or Vite env var.
- **Credentials setup was an afterthought.** The `.env` file and `python-dotenv` setup happened after the user noticed credentials were hardcoded. It should have been part of the scaffold — the scaffold preview even had `config.py` as a file to create, but didn't flag the credentials pattern.
- **CORS error masked a 500.** When the profile endpoint threw `KeyError: 'genres'`, the browser reported it as a CORS error because the 500 response dropped CORS headers. Required an extra round-trip to diagnose (user had to paste the uvicorn traceback). A global FastAPI exception handler that ensures CORS headers survive errors would have surfaced the real cause immediately.

---

## Decisions Reviewed

| Decision | Outcome | Confidence |
|----------|---------|------------|
| FastAPI full migration | Right call — clean, low cost, async benefit is real | High |
| PKCE for Spotify auth | Necessary, not optional — implicit grant is deprecated | High |
| `127.0.0.1` instead of `localhost` | Required by Spotify policy for new apps (April 2025) | High |
| Iterative Spotify validation loop | Solid design — all returned songs are confirmed Spotify tracks | High |
| Session-based LLM key storage | Works for v1; will need revisiting when auth is added | Medium |

---

## Surprises

- **Spotify deprecated the implicit grant flow.** `response_type=token` is dead for new apps as of April 2025. PKCE is now the required approach for SPAs. The existing profile page code would have needed this fix regardless of the new features.
- **`localhost` is blocked as a Spotify redirect URI.** New apps (post-April 2025) must use `http://127.0.0.1` explicitly. This also required updating the Vite config to bind to `127.0.0.1` since macOS resolves `localhost` to `::1` (IPv6), not `127.0.0.1` (IPv4).
- **Spotipy fields aren't guaranteed.** `artist['genres']` threw a `KeyError` — even well-documented Spotify API fields can be absent on specific objects. Safe `.get()` defaults should be used throughout.

---

## Lessons Learned

- Scaffold should prompt for a credentials strategy upfront — hardcoded secrets in config files is a predictable problem worth addressing in the preview, not after.
- A FastAPI global exception handler that re-applies CORS headers is worth adding early. Debugging masked 500s is friction that compounds during a debug session.
- Spotify's policy changes (PKCE, IP literals) will affect any project using their OAuth. Worth flagging in setup docs for anyone starting fresh.

---

## Next Steps

1. **Test home page search and recommendations** — these hit the migrated FastAPI endpoints (`/search/`, `/get-recommendations/`) which haven't been exercised yet
2. **Fix port hardcoding** — extract `http://127.0.0.1:8005` to a Vite env var (`PUBLIC_API_URL`) so changing the port is a one-line change
3. **Add FastAPI global exception handler** — ensure CORS headers survive 500 errors to make future debugging faster
4. **Test the playlist builder end-to-end** — connect LLM key, generate a playlist, verify Spotify validation loop, test save and queue actions
5. **Add new Spotify scopes to the frontend OAuth** — `playlist-modify-private` and `user-modify-playback-state` are in the backend SCOPE config but the frontend's PKCE auth flow needs them too for the spotify_actions endpoints to work

## Suggested Next Phase

`/build` — the scaffold is in place and the profile page is verified working. The next session should drive the feature to a working end-to-end state: fix the port config, exercise the remaining endpoints, and get the playlist builder generating and saving playlists.
