# Review — AI DJ Companion DJ0–DJ4 + shared backend fixes
Date: 2026-10-23
Triggered by: ad hoc (pre-commit, after /build of DJ1–DJ4)
Scope: every uncommitted change in the working tree. This is the DJ work (`routers/dj.py`,
`routers/player.py`, `src/ios/BoominBeats/DJ/*`, `RootView`, `SettingsView`, `Config`,
`APIClient`) plus the shared fixes (`spotify_client.py`, `spotify_validator.py`, `llm_client.py`,
`main.py`, `spotify_actions.py`, `PlaylistResult.svelte`). It also includes an **earlier
uncommitted refactor that predates this session**: routing every Spotify client through
`services/spotify_client.py` (`profile.py`, `search.py`, `spotify_actions.py`, part of `main.py`).
Focus: All

## Summary

Healthy. The DJ milestones match the plan, and each deviation was flagged and logged during the
build: the adaptive buffer, the ⋯ menu instead of long-press, and Driver's scope before DJ6. There
are no critical findings. The main gaps are two boundary or robustness issues in `dj.py`, a tracked
token file, and no automated tests for the iOS queue logic.

Critical: 0 | Warning: 4 | Suggestion: 6

## Plan Adherence

- DJ0–DJ4 are built as planned. The results are recorded in `docs/plan.md`, and the tracker tasks
  for DJ1–DJ4 are in review.
- Deviations, all logged: the adaptive buffer (1 in the foreground, N on background) instead of a
  fixed 5; a ⋯ menu instead of long-press for do-not-play; Driver = "keep 3 lined up" until DJ6;
  `_OVERASK` 1→2; Groq `reasoning_effort='low'` (approved by the owner).
- Built but **not exercised live**: drag-to-reorder Up Next, the "Later" swipe, the buffer-depth
  stepper, the no-device and "nothing playing" states, skip detection feeding `skipped`, and the
  DJ0.1 Jam half (deferred by the owner).
- Live verification of DJ3/DJ4 is blocked until about 2026-10-24 21:15 CDT by Spotify's app-wide
  search 429. The fail-fast path is verified.

## Code Quality

- The backend follows the established patterns: thin routers, `services/` for clients, pure
  helpers (`normalize_*`, `select_tracks`, `salvage_truncated`) with unit tests. 61 tests pass.
- iOS follows the `ProfileModel` pattern (`@MainActor @Observable`, models injected through the
  environment). The file-system-synchronized group picked up `DJ/` with no pbxproj churn.
- The `QueueStore` / `SuggestionStore.autopilot` logic is the most intricate code in the change, and
  it has no automated check. The iOS project has no test target.

## Security

- BYOK key: stored in the Keychain on iOS, and in the existing `localStorage` on the web. It travels
  per request, with no server-side storage. ✓
- No secrets were added to source. `.env` stays gitignored. **But `src/web/backend/.cache` (a
  spotipy client-credentials token cache) is tracked despite `.gitignore`.** It was committed in
  `c0e744c`, before the ignore rule existed.
- `/dj/suggest/` validates scalars (`per_move`, `adventurousness`) but not list or string sizes.
- LLM output never reaches the client unvalidated: every suggestion is re-resolved through Spotify
  search and filtered. Prompt injection through track titles can only affect the user's own
  suggestions.
- No injection sinks: no SQL, shell or HTML rendering of model output.

## Findings

### Critical
| # | Location | Issue | Recommendation | Status |
|---|---|---|---|---|
| — | — | None | — | — |

### Warning
| # | Location | Issue | Recommendation | Status |
|---|---|---|---|---|
| W1 | `routers/dj.py` `_spotify_recent` | The best-effort history call catches builtin `TimeoutError`/`ConnectionError`, but `requests.exceptions.ReadTimeout`/`ConnectionError` don't subclass them (verified). A slow Spotify history call therefore fails the *whole* suggestion with a 503 instead of being skipped. | Also catch `requests.exceptions.RequestException`. | Fixed pre-commit |
| W2 | `routers/dj.py` `SuggestRequest` / `TrackRef` | Unbounded `recent`/`upcoming`/`liked`/`disliked`/`skipped`/`avoid_*` lists and string lengths. A client can inflate the prompt, which costs the user's LLM budget, and on the hosted instance it sits behind only the device key. | `Field(max_length=…)`: lists ≤ 50, strings ≤ 300. | Fixed pre-commit |
| W3 | `src/web/backend/.cache` | A token cache is tracked in git despite `.gitignore`. It holds a (now expired) app access token, which is in history since `c0e744c`. | `git rm --cached src/web/backend/.cache`. The token is short-lived, so no rotation is needed. | Fixed pre-commit |
| W4 | `src/ios/BoominBeats/DJ/QueueStore.swift`, `SuggestionStore.autopilot` | Order-sensitive logic (arrival trimming, skip-on-arrival, reconcile matching with duplicates, Autofill/Driver targets) has no runnable check. It was only verified by hand in the Simulator. | Add an XCTest target and pure-logic tests with a fake client. → /iterate | Fixed before DJ5 |

### Suggestion
| # | Location | Issue | Recommendation | Status |
|---|---|---|---|---|
| S1 | `Networking/APIClient.swift` | Sends `X-LLM-Provider`/`X-LLM-Key` on **every** request, not just LLM routes. That widens where the key travels (proxies, future logging) for no benefit. | Attach them only for `dj/`, `llm/` and `song/` paths. | Open |
| S2 | `DJ/QueueStore.reconcile` | `GET /me/player/queue` returns at most 20 items. If more than 20 non-app tracks sit ahead (a busy Jam), still-queued `sent` items get dropped as "played". | Only drop `sent` items when the response has fewer than 20 entries, or keep unmatched ones. | Fixed before DJ5 |
| S3 | `DJ/NowPlayingView.swift` `content()` | The `ScrollView` was wrapped around an un-reindented `VStack`, so it misreads as unbalanced. | Re-indent. | Open |
| S4 | `DJ/SuggestionStore.swift` doc comment | It says a call "takes ~6s", which is stale after `reasoning_effort='low'` (about 3s). | Update the comment. | Open |
| S5 | `routers/spotify_actions.py` | It imports `player_error` from another router. | Move `player_error` to `services/` when next touched. | Open |
| S6 | `DJ/QueueStore.autoSkipped` | Grows for the whole session. | Cap it or prune it on arrival. Trivial. | Open |

## Resolved This Session
- `queue_songs` 403 → "Premium required" mis-mapping. Fixed with `player_error`, and the web
  `PlaylistResult` "unknown error shown as success" bug fixed alongside it.
- Retired Groq model (`llama-3.3-70b-versatile`) → `openai/gpt-oss-120b`.
- Expired Spotify token surfaced as 500 → now 401.
- A Spotify 429 hung workers for the Retry-After duration (about 23h) → own `Session` without
  Retry-After, plus a 429 → 503 handler.
- The DJ title-only fallback wasted searches → `fallback=False`, plus the process cache.

## Carried to /iterate
1. **W4:** XCTest target + `QueueStore`/autopilot tests. Highest value before DJ5, which builds on
   reconcile.
2. **S2:** reconcile's 20-item ceiling. It matters exactly when DJ5 (guest requests) lands.
3. **S1:** scope the LLM headers to LLM routes.
4. S3–S6: tidy-ups, whenever those files are next touched.

None of these block shipping. W1–W3 were fixed before the commit: `requests` exceptions are caught
(with a test), `SuggestRequest` has bounds (lists ≤ 50, strings ≤ 300, with a test), and `.cache`
is untracked with `git rm --cached`. 63 tests pass.

## Follow-up (2026-10-23, before DJ5)
- **W4:** added a `BoominBeatsTests` target to the hand-written pbxproj: a synchronized folder,
  hosted in the app, using Swift Testing. The pure logic was extracted into
  `QueueStore.arrival(of:in:)`, `QueueStore.reconciled(_:against:)` and
  `SuggestionStore.autopilotCandidates(...)`, with 11 tests. Run:
  `xcodebuild test -scheme BoominBeats -destination 'platform=iOS Simulator,name=iPhone 17 Pro'`.
- **S2:** `reconciled` drops only the *played prefix* (everything before the first `sent` track
  still visible). When the view is full (20), it keeps the trailing tracks it can't match. Keeping
  "any unmatched track when the view is full" would have been wrong, because the playing context
  nearly always pads the view to 20. Ceiling: with 20+ non-app tracks ahead, nothing of ours is
  visible, and everything is treated as played.
