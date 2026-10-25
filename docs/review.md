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

---

# Review — SY1 backend sync API
Date: 2026-10-25
Triggered by: /build completion (SY1), commit `822070f`
Scope: `routers/dj_state.py`, `services/dj_store.py`, `services/spotify_identity.py`, the
`routers/player.py` piggyback, `config.py`, `supabase/migrations/…_dj_state.sql`,
`tests/test_dj_state.py`
Focus: All, with an emphasis on security (the first persistent server-side state)

## Summary

Sound. All 8 SY1 tasks were built as planned, and the 409/seed/claim/piggyback flow is verified
live. No criticals. One security warning: expired Spotify tokens stay accepted for sync, because
of how long user ids are cached. The "never break player state" guarantee has a gap. The repo's
migration file doesn't match the recorded version.

Critical: 0 | Warning: 4 | Suggestion: 4

## Plan Adherence

- Every SY1 task is done. The deviations are allowed by the plan or noted in the SY1 result:
  `httpx` instead of the `supabase` package; the piggyback costs one server-side DB read per poll.
- The validation is stricter than the plan asked (unknown fields forbidden at every level, not just
  top-level), and that's on purpose.

## Code Quality

- Thin router, store in `services/`, pure helpers (`primary_info`, `heartbeat_due`) unit-tested.
  It matches the existing patterns.
- The happy path of the piggyback (`dj_status` writing a heartbeat when due and returning
  version/primary) is only covered by the live check, not by a test.

## Security

- **No injection:** PostgREST filters go through `httpx` params (URL-encoded), and `eq.` values
  are compared literally. The device id is bounded to 64 characters.
- **Authorization:** rows are keyed by the Spotify id resolved from the caller's own token, so a
  client can't name another user's row. A 409 only ever returns the caller's own document.
- **Secrets:** the service key is server-only (`.env`, gitignored, scan clean). RLS deny-all means
  a leaked anon key can't read the table.
- **Input:** bounded lists and strings and strict schemas. The worst-case document is about 1 MB.
- **Weakness:** see W1. The identity cache outlives tokens.

## Findings

### Critical
| # | Location | Issue | Recommendation | Status |
|---|---|---|---|---|
| — | — | None | — | — |

### Warning
| # | Location | Issue | Recommendation | Status |
|---|---|---|---|---|
| W1 | `services/spotify_identity.py` `_TTL` | User ids are cached for 50 minutes from *first use*, and `/dj/state` never calls Spotify after that. A token first used near its 1-hour expiry keeps working for sync for up to ~50 minutes **after** it expires, which widens the window a leaked token is useful. | Cut `_TTL` to 5 minutes. That's one `/me` call per device per 5 minutes and bounds expired-token acceptance to 5 minutes. | Fixed |
| W2 | `routers/player.py` `dj_status` ← `user_id()` | `user_id()` only converts `SpotifyException`. A `requests` timeout or connection error from `/me` escapes `dj_status` (which catches `Unavailable` and `HTTPException`), so the **player poll itself fails with 503**. That breaks the documented "sync never breaks player state" guarantee whenever `/me` is slow. | Catch `requests.exceptions.RequestException` in `user_id()` and raise a 503 `HTTPException`. That covers the sync routes too. | Fixed |
| W3 | `supabase/migrations/20261025180000_dj_state.sql` | Supabase recorded the migration as **`20261025175713`**. If the Supabase CLI is ever used (`db push`/`db diff`), it treats the file as unapplied, re-runs it, and fails with "relation already exists". | Rename the file to `20261025175713_dj_state.sql`. | Fixed |
| W4 | `tests/test_dj_state.py` | The piggyback's success path is untested: heartbeat written only when due, `{version, primary}` returned, `{version: 0}` with no row. Only the failure path has a test. | Add 2–3 tests with the fake store and a stubbed `user_id`. | Fixed |

### Suggestion
| # | Location | Issue | Recommendation | Status |
|---|---|---|---|---|
| S1 | `routers/dj_state.py` endpoint signatures | `current_user` (a Spotify `/me` call) resolves *before* `get_store`, so an unconfigured server spends a Spotify call before answering 503. | Order the dependencies `store` before `user`. | Open |
| S2 | `routers/player.py` `dj_status` | Imports inside the function. There's no import cycle that needs them. | Move them to the module top. | Open |
| S3 | `routers/dj_state.py` `Goal.startedAt` | Free-form string. A malformed date is stored and fails later on a client. | Type it as `datetime` and dump with `model_dump(mode='json')`. | Open |
| S4 | Data handling | Listening history, feedback and do-not-play now persist server-side, and there's no way to delete them. | Add `DELETE /dj/state` ("Clear synced DJ data") in SY3, and mention it in the data notes. | Open |

## Resolved This Session
- **W1:** `_TTL` cut to 5 minutes. The docstring now explains why the TTL bounds expired-token
  acceptance.
- **W2:** `user_id()` converts `requests` network errors to a 503 `HTTPException`. There's a test.
- **W3:** the migration was renamed to `20261025175713_dj_state.sql`, matching Supabase's record.
- **W4:** three piggyback tests (no session; version + primary; heartbeat only when due and only
  from the primary) plus the identity network-error test. 90 tests pass.

## Carried to /iterate
1. W1, W2, W3: bounded; recommended before SY2/SY3 build on this.
2. W4: tests to accompany the W2 fix.
3. S1–S3: tidy-ups, cheap to do with the above.
4. S4: fits SY3, where the iOS UI gets a sync section.
