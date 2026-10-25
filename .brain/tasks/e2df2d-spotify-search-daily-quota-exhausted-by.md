---
id: e2df2d
source: review:ryans-boomin-beats:spotify-search-daily-quota
title: Spotify search daily quota exhausted by DJ prefetch
type: bug
status: backlog
assignee: 
scoped_dir: .
created: 2026-10-25T19:09:28Z
updated: 2026-10-25T22:36:32Z
---

## Brief
High. /dj/suggest/ validation. 2026-10-25: search 429 QUOTA_EXCEEDED, resets around 21:20 local, same as 10-24, after a morning of Co-pilot prefetch (10-20 searches per track change). A 4h party of about 60 tracks could exhaust it. Options: validate lazily (only shown picks), fewer overasks, prefetch only on open or in Autofill/Driver, a cross-instance cache in Supabase, and measure the real quota.

## Acceptance

## Runs

## Updates
- 2026-10-25T19:09:28Z · created
- 2026-10-25T22:36:32Z · comment: Partial mitigation: per-process search lockout honours Retry-After, so a locked-out instance makes zero search calls (live: 2nd+ searches refused in 0 ms). Root cause (searches per suggestion, prefetch frequency) still open.
