# Handoff: Boomin Beats web redesign

## Overview
A redesign of the Boomin Beats web app (`src/web/frontend`, SvelteKit) covering the app shell, Explore, Playlist builder, Profile, DJ, Settings, first run and empty states, plus a phone layout. The goal is a more polished, "state of the art" product: immersive color, motion while music plays, denser song lists, and tighter links between pages.

## About the design files
The files in this bundle are **design references built in HTML**. They show the intended look and behavior; they are not production code. Recreate them in the existing SvelteKit app using its patterns (Svelte components, `stores.js`, `lib/dj/*`, existing API routes). Do not port the HTML/JS directly.

- `Boomin Beats.dc.html` is the whole app as one clickable prototype. Open it in a browser (it needs `support.js` beside it).
- `SongRow.dc.html` is the shared song row used by every list.
- All data in the prototype is mocked (songs, playlists, AI picks, profile stats, timings).
- The template uses `{{ }}` holes filled by the `Component` class at the bottom of each file. `renderVals()` is the best place to read the logic for each control.

**Tweaks (top of the prototype)** switch between variants:
- `pageStyle`: Immersive (default) / Flat
- `navStyle`: Top bar (default) / Sidebar
- `djLayout`: Host (default) / Compass
- `device`: Responsive / Phone frame (forces the 390×844 layout)
- `startAt`: Signed in / First run

## Fidelity
**High fidelity.** Colors, type, spacing, radii and motion are final unless noted. Keep the repo's token names (`--accent`, `--surface-*` …) and map the values below onto them.

Open decisions for the implementer:
1. **Font.** The prototype uses **Geist / Geist Mono**; the repo uses Inter / Fira Mono. Pick one. The sizes below work with either.
2. **Text size.** The prototype scales the whole app with CSS `zoom` (default 0.9). In Svelte, prefer a root `font-size` scale with rem-based styles, if the codebase allows it.
3. **Previews.** Spotify mostly no longer returns `preview_url`. Use Deezer's 30-second preview (search already uses Deezer) played through an `<audio>` element on the current device.

---

## Design tokens

### Color
| Token | Value | Use |
|---|---|---|
| bg | `#0a0a0c` | page |
| surface-raised | `#0d0d10` | sidebar, dock, mini player base |
| card (flat) | `#131316` | Explore and Builder cards, inputs |
| card (glass) | `rgba(20,20,24,.62)` + `backdrop-filter: blur(24px)` | DJ and Profile cards, toolbar pills |
| popover | `#17171b` / `rgba(23,23,27,.94)` + blur 30px | Settings, palette, modals |
| active fill | `#24242a` | selected segment, active nav |
| hover fill | `#1b1b1f` / `rgba(255,255,255,.05)` | row and button hover |
| border | `rgba(255,255,255,.07)` (cards), `.08–.10` (controls), `.12–.14` (secondary buttons) | |
| text | `#f3f3f5` | primary |
| text muted | `rgba(243,243,245,.6)` | secondary |
| text subtle | `rgba(243,243,245,.4–.5)` | meta, captions |
| accent | `#5ec9ff` | primary buttons, active icons, progress, links |
| accent hover | `#8ad8ff` | link hover |
| accent text-on | `#06121a` | text on accent buttons |
| accent tint | `rgba(94,201,255,.12–.14)` bg, `.5–.55` border, `#9ddfff` text | selected chips and tags |
| purple | `#a235ff`; light `#c49bff`, `#d7bcff` | Goal and Toward move only, gradient end |
| brand gradient | `linear-gradient(135deg,#5ec9ff,#a235ff)` | Build playlist, Find songs, progress bars, visualizer |
| success | `#4ade80` | AI or Spotify connected dot |
| danger | `#ff7a7a`, text `#ff9a9a`, `#ffb0b0` | not on Spotify, decline, remove hover |

Cover placeholders: `linear-gradient(140deg, oklch(.66 .12 H), oklch(.32 .08 H+45))`. In production use real album art. Immersive backgrounds use the cover's hue, so use `lib/dj/ambience.js` `sampleCover()` to get it.

### Type (Geist; mono = Geist Mono)
| Role | Size / weight / line-height / tracking |
|---|---|
| Hero h1 (immersive) | `clamp(44px,9vw,84px)` / 700 / .95 / -.05em |
| Song h1 (immersive) | `clamp(40px,8vw,76px)` / 700 / .95 / -.045em |
| Playlist h1 (immersive) | `clamp(40px,7vw,68px)` / 700 / .95 / -.045em |
| Page h1 (flat) | `clamp(38px,7vw,56px)` / 600 / 1.02 / -.035em |
| Profile name | `clamp(32px,5vw,56px)` / 700 / 1 / -.04em |
| Card title | 15–16 / 600 |
| Panel header | 14 / 500 |
| Body | 14–15 / 400 / 1.5 |
| Row title / artist | 14 / 500 and 13 / 400 (compact: 13 and 12) |
| Meta | 12 / 400; mono 11–12 |
| Section eyebrow | mono 11–12 / 500, accent or subtle |
| Profile summary | 22 / 500 / 1.45 / -.015em; muted, with key phrases in full white |

### Radius, spacing and shadow
- Radius: 5–7 (covers, small buttons), 8–9 (buttons, inputs), 10–12 (rows, chips groups, inner tiles), 14–16 (cards), 18–22 (popovers, hero inputs), 999 (pills).
- Spacing: 4 / 6 / 8 / 10 / 12 / 14 / 16 / 20 / 24 / 28 / 32. Card padding 16–20. Page padding 28 desktop, 16 phone. Grid gaps 12 (DJ), 16 (Profile), 24 (Explore).
- Shadows: popovers `0 30px 80px rgba(0,0,0,.55)`. Covers `0 16–30px 40–80px rgba(0,0,0,.4)`. Toast `0 20px 50px rgba(0,0,0,.5)`.
- Control heights: 28 (small segment), 32–34 (header buttons), 36–38 (secondary), 40–46 (primary), 60–64 (hero search).

### Motion
Easing: `cubic-bezier(.16,1,.3,1)` everywhere. Respect `prefers-reduced-motion` and the **Playback animations** setting (pause everything below).

| Name | Spec | Where |
|---|---|---|
| bbin | opacity 0→1, translateY 6px→0, .2–.4s | popovers, cards mounting, list items (stagger 40–60ms) |
| bbshimmer | bg-position 200%→-200%, 1.6s linear, gradient `#1c1c21 / #2a2a31` | all skeletons |
| bbspin | 360°, .7s linear | button spinners, refresh icon while loading |
| bbeq | scaleY .18→1, .5–.95s alternate, staggered negative delays | visualizer, mini-player bars, loading bars |
| bbbreath | scale 1→1.03, 5s | Now playing cover while playing |
| bbglow | blurred copy of cover behind it, scale .92→1.06, 4.5s, opacity .75 when playing and .2 when paused | Now playing covers |
| bbpop | scale .9→1 + fade, .55s | cover when the song changes (keyed on track id) |
| bbdrift | 3 blurred blobs (blur 100px, opacity .26, oklch(.5 .13 H)) translate 7vw/5vh + scale 1.18, 22–30s alternate | immersive DJ background, Profile hero, onboarding |

---

## Global shell
- **Header** (60px, `rgba(10,10,12,.82)` + blur 20, bottom border). Logo 30px plus "Boomin Beats" (15/600) on the left, 220px wide. Centered **segmented nav** with Explore / Builder / DJ / Profile, each with an icon: 32px items, active `#24242a` with an accent icon, and a 5px accent dot on DJ while music plays. On the right: Search button (⌘K), Playlists toggle, and a **gear** button (34px circle) with a status dot for the AI connection.
- **Sidebar variant** (248px): logo, a search field, vertical nav, the playlist list (drop targets), and a footer Settings button showing the AI status.
- **Command palette** (⌘K): 620px, 14vh from the top. Lists songs (recent ones, or matches as you type) and Go to pages. On DJ it adds the picked song to Up next.
- **Mini player** (64px, glass): a 2px progress line along the top (gradient + glow); cover (glow/breath) with title, playing bars and artist; prev / play / next; goal, time, and Open DJ. Hidden on the DJ page and when nothing is playing.
- **Playlists dock** (340px right panel): search, Recent / A to Z sort, New playlist tile, and a grid of playlist tiles. **Every song row is draggable** onto a playlist: tiles get a dashed outline while dragging and solid accent plus scale 1.03 on hover-over. Dropping adds the song and shows a toast.
- **Toast**: white pill above the mini player. Queue edits get an **Undo** button and stay 4.5s; other toasts stay 2.2s.

## Settings (gear popover, 380px; bottom sheet on phone)
Header "Settings", a segmented **General | AI** control, and a close button. The body scrolls. The footer reads "Saved on this device" and, on General, has **Reset to defaults**.
- **General**
  - DISPLAY: Text size as a segmented control (80 / 90 / 100 / 110 / 120%, default 90%) showing the current value. **Compact song rows** toggle.
  - PLAYBACK: **Clean only** (skip explicit songs in DJ picks, playlists and recommendations). **Lower Spotify while previewing** (default on).
  - MOTION: **Playback animations** (default on).
  - ACCOUNT: avatar, name, "Spotify connected", Log out (goes to first run).
- **AI**
  - Status card: green tint when connected.
  - Provider radio list: Claude, OpenAI, Groq, Your Claude Code (no key needed).
  - Key field (password), Connect/Save and Disconnect.
- Toggles are 36×22 tracks with a 16px knob (accent when on).
- Persist settings in localStorage: `bb-zoom`, `bb-compact`, `bb-motion`.

## Explore
**Idle, immersive:**
- A radial hero tinted by the hovered top-track's hue, with the eyebrow "Explore · {song}".
- h1 "What are you in the mood for?" and a 64px pill search (glass) with type-ahead (up to 6 rows).
- Mood chips go straight to the Builder.
- Below: "Start from your top tracks", a grid of 150px cover tiles with the rank in the corner. They lift on hover and open the song.

**Idle, flat:** the same content left-aligned, with a 60px search and a 3-column list of top tracks.

**Song page:**
- Sticky bar: back button, a **Path** trail (breadcrumb chips of songs explored this session, clickable), and New search.
- Immersive: a full-width hero (232px cover, 76px title, artist, Last.fm stats, Play / Add to queue). Flat: a compact card instead.
- Left column (1.35fr):
  - **Tags** (Last.fm; tap to add to the recipe).
  - **What the AI hears**: a 2-column grid of aspect cards with a checkbox. Without a key, show "Add an AI key…" and a button.
  - **Sound profile** bars and **About**.
- Right column (min 340px, sticky at top 76): **Your recipe**.
  - Picked items appear as removable accent chips.
  - **Find 12 similar songs** (gradient; shows a spinner while loading).
  - **Build a playlist from this recipe →** sends `songs like {title}: {picks}` to the Builder and starts building.
  - Results: shimmer skeletons, then rows with "Shares …" reasons and Save as playlist.
- Clicking a result opens that song and adds it to the Path.

## Playlist builder
- **Empty:** h1 "Describe a playlist.", a composer (textarea + Songs 10 / 12 / 20 + Build playlist) and example chips. Enter submits.
- **Active (2 columns: 340–420px chat | playlist):**
  - Chat shows user bubbles (`#24242a`) and AI replies (outlined).
  - The loading card shows gradient bars plus 3 steps (Picking songs → Matching each one on Spotify → Naming it), the current step with a pulsing dot.
  - Refine chips: More upbeat, Add some 90s, Fewer Frank Ocean, Shorter songs. A follow-up input below.
  - Playlist side:
    - Immersive hero with a 220px 2×2 cover mosaic, generated name and meta, plus Save to Spotify, Add all to queue, Start a DJ set from it.
    - A red notice when a song wasn't matched on Spotify; the row is flagged with a Swap button.
    - Skeleton rows while the first build runs; the list dims to 40% during refines.
    - Hint: "Click any song to explore from it, or drag it onto a playlist." Clicking a row opens Explore.
  - Save opens a name modal.

## Profile
- Header: 88px avatar, name, "29 followers · Spotify", and a **4 weeks / 6 months / All time** segmented control.
- Immersive: drifting blue blobs behind the header that fade out down the page.
- One-sentence **summary** with key phrases highlighted.
- **Insights row** (auto-fill, min 230px glass cards, staggered fade-in, lift on hover). Each card has a label, a 20px statement and an accent action:
  - Top genre → Build a {genre} playlist
  - Eras → Build from the {second era}
  - Listening clock → Start an evening/late-night DJ set (applies the Pregame or Afterparty preset)
  - Top artist → Build songs like {artist}
- **Module grid** (12 columns):
  - Top tracks 5, Top artists 4, Top genres 3 (520px tall)
  - Eras 3, Taste over time 5, Listening clock 4 (300px)
  - Each module has an expand button that makes it the only module, 12 columns wide.
  - Below 1180px wide modules span 6 columns; on phone, 12.

## DJ
**Toolbar** (glass pills):
- "DJ" (24/700), plus a Driving from {device} status with **Drive from here**.
- **Night presets**: Dinner, Pregame, Peak, Afterparty. Each sets Safe↔Bold, Familiar↔New and Goal.
- Host / Compass toggle, **Add playlist**, Save tonight's set.

**Immersive background:** a radial gradient plus drifting blobs from the current song's hue. They only move while music is playing.

**No page scroll on desktop (≥1180px).** The page is 100% tall and each panel scrolls on its own.

**Host layout** (3 columns: 3fr | 6fr | 3.4fr, one row filling the height):
- Left column:
  - **Now playing** (fixed height): small bars + "Now playing", device name. 100px cover (breath, glow, pop on change), title (2-line clamp) and artist. 40-bar gradient **visualizer**, gradient progress, and Less like this / prev / play / next / More like this.
  - **DJ controls** (fills the rest, scrolls):
    - Mode segment (Whisper / Co-pilot / Autofill / Driver) with a description.
    - Safe↔Bold and Familiar↔New sliders; Familiar↔New shows "From your library / Mix / Mostly new".
    - Goal chips (purple).
    - Pick source line ("Picks from Claude…" or "No AI key: Last.fm similar tracks" with Add key).
- Middle column, **Next moves**:
  - Header shows the pick count and a refresh-all button.
  - Body is a grid (auto-fill, min 270px) of move groups: Hold =, Lift ↑, Toward ◆ (purple, hidden when Goal = None), Pivot ←, Curveball →, Drop ↓.
  - Each group shows 3 compact rows with a 1-line reason and its own **refresh** button (see interactions).
- Right column: **Requests** (Keep / Later (clock) / Decline per row, with a red count badge), **Up next** (fills, scrolls), and the optional **Playlist** section.

**Compass layout:**
- Control bar: mode, two sliders, and "Arrow keys add a move · H holds · T toward".
- 3×3 grid of equal rows:
  - Top row: Hold, Lift, Toward. Middle row: Pivot, **Now playing**, Curveball.
  - Bottom row: Playlist (or a dashed "Add playlist" slot), Drop, Up next.
- Move cards show 4 compact rows without reasons (the reason is the row's tooltip), plus refresh and a key badge.
- Keys: ↑ Lift, ↓ Drop, ← Pivot, → Curveball, H Hold, T Toward. Each adds the first pick not already queued and flashes the card border accent for 500ms.

**Playlist section:**
- Opened with Add playlist; a dropdown picks one of the user's playlists.
- Shows the count, a filter field and compact rows with + to queue.
- Close removes the section.

**Nothing playing (empty state):**
- Gradient bars, "Nothing is playing yet", and a line explaining that playing anything in Spotify will be picked up.
- Starter rows: clicking one starts it; tapping its cover previews it.

**Save tonight's set** (modal, 720px): playlist name, AI recap (toggle "Add to description"), stats (time played, DJ picks kept, guest requests), and the list of songs played on the right. Save to Spotify.

## Song row (`SongRow.dc.html`)
- Props: `song`, `index`, `size`, `compact`, `showReason`, `showDur`, `added`, `previewId`, `onPreview`, `onOpen`, `onAdd`, `onSwap`, `onDrag`, `onDragEnd`.
- Layout: optional rank (20px mono), cover (40px; compact 34px), title + ✦ when the DJ picked it, artist, optional reason (2-line clamp; compact 1 line), optional duration, Swap when flagged, and a + button (32px; compact 28px). The + turns into an accent check once queued.
- Padding is 8×10 (compact 5×8) with radius 10 and hover `rgba(255,255,255,.05)`. The whole row is draggable.
- **Preview affordance:** a tiny play badge in the cover's corner. Clicking the cover previews (and doesn't open the song). While previewing, the cover gets an accent ring and animated white bars, the title turns `#9ddfff`, and the row is tinted.

---

## Interactions & behavior
- **Refresh per move:**
  - The refresh icon opens "What's off about these?" chips: Too slow, Too intense, Heard recently, Wrong genre, Too obvious, **Just show new ones**.
  - Picking a chip closes them, spins the icon, shows shimmer rows for about 800ms, then new picks.
  - Feedback chips are stored per move and shown as "Avoiding: …" under the header, with a toast confirming.
  - **Implementation:** send the feedback with the move request in `lib/dj/dj.js` / `logic.js`.
- **Preview:**
  - 15 seconds on the current device. The floating pill (480px, glass, accent border) shows the cover, title, time, a progress bar, the output note ("Spotify lowered" when ducking is on), **Queue it** and Stop.
  - It ends on its own at 15s. Starting a new preview replaces the old one.
  - Ducking uses the Spotify volume endpoint: lower to about 20%, then restore.
- **Editing the queue (Up next):**
  - Drag rows to reorder by the grip or the row; the list reorders live and the dragged row shows at 55% opacity.
  - Per row: **Play now** and **Remove**. The header has **Clear** and Add song (opens the palette).
  - Every edit snapshots the queue and now playing, and shows a toast with **Undo**.
- **Requests:** Keep inserts the song after the next one, Later appends it, Decline removes it. All show a toast.
- **Next song:** shift the queue into now playing. Moves reload (skeleton) unless the mode is Whisper, which shows "Get moves".
- **First run:**
  1. Connect Spotify (button spinner).
  2. Pick an AI or "Skip, use Last.fm only".
  3. Start with Explore, Build a playlist, or Start a DJ set.
  - There are progress dots, and the immersive background runs throughout.
  - After that: top tracks and the Profile grid are replaced by empty-state copy, and the DJ shows the nothing-playing state.
- **Explore ↔ Builder:** the recipe goes to the Builder; Builder rows open Explore. Mood chips on Explore go to the Builder too.

## Responsive
Breakpoints use effective width (window width ÷ text-size scale): **phone < 760**, **tablet 760–1179**, **desktop ≥ 1180**.
- Phone:
  - The header nav is hidden (logo, search icon and gear remain) and a **bottom tab bar** appears (4 items, 52px, icon + label).
  - The mini player shows only the left and center parts.
  - Settings becomes a bottom sheet (8px inset, max 82% tall) and the dock covers the full width.
  - Page padding is 16px.
- Below desktop:
  - Explore song page and Builder become single columns; Builder chat goes under the playlist at 520px tall.
  - The recipe column stops being sticky.
  - DJ grids collapse: Host to 2 columns (tablet) or 1 (phone). Compass puts Now playing on top across the full width, then the cards flow in 2 columns or 1.
  - The page scrolls and panels cap at 360px.

## State (suggested stores)
- `settings`: zoom, compact, motion, clean, duck, aiProvider, aiConnected (persisted).
- `player`: now, pos, playing, idle, queue[], driving device.
- `dj`: mode, bold, familiar, goal, preset, layout, movesState (idle / loading / ready), picks per move, loading and feedback per move, requests[], playlist section id and filter.
- `preview`: { id, song, pos } | null.
- `explore`: songId, trail[], picked[], discover state.
- `builder`: phase, messages[], tracks[], name, prompt, step.
- `ui`: page, settingsOpen and tab, paletteOpen, dockOpen, toast { text, undo }, onboarding step.

## Assets
- `assets/logo.jpg`: from `src/lib/images/BoominBeatsLogo.jpg` in the repo.
- Icons are simple inline 24px stroke icons (stroke 1.7–2, round caps). Replace them with the codebase's icon set if it has one.
- Album art is placeholder gradients; use real Spotify covers.

## Screenshots
`screenshots/`: 01-explore-idle.jpg, 02-explore-song.jpg, 03-explore-recipe.jpg, 04-builder-empty.jpg, 05-builder-playlist.jpg, 06-profile.jpg, 07-dj-host.jpg, 08-dj-refresh-feedback.jpg, 09-dj-preview.jpg, 10-dj-compass.jpg, 11-settings-general.jpg, 12-settings-ai.jpg.
They were captured at about 924px wide, so they show the **tablet** layout (DJ in 2 columns, Explore and Builder stacked). Open the prototype at 1280px or wider to see the desktop 3-column DJ and the side-by-side Explore and Builder. Use the `device` tweak to see the phone layout.

## Files
- `Boomin Beats.dc.html`: full prototype (template + `Component` logic at the bottom).
- `SongRow.dc.html`: shared row.
- `support.js`: runtime needed to open the prototype locally.
- `assets/logo.jpg`

### Map to repo
| Prototype area | Repo files |
|---|---|
| Shell, header, settings | `routes/+layout.svelte`, `routes/Header.svelte`, `lib/components/LLMSettingsPanel.svelte`, `routes/styles.css` |
| Explore | `routes/+page.svelte`, `SongSearch.svelte`, `SongProfile.svelte`, `TopTrackSeeds.svelte`, `TagPill.svelte` |
| Builder | `routes/playlist-builder/+page.svelte`, `ChatInterface.svelte`, `PlaylistResult.svelte`, `PlaylistNameModal.svelte` |
| Profile | `routes/profile/+page.svelte`, `DashboardModule.svelte`, chart components |
| DJ | `routes/dj/+page.svelte`, `lib/dj/layout.js` (add a Compass preset and a Playlist widget), `lib/dj/ambience.js`, `lib/components/dj/*` |
| Playlists dock | `PlaylistsPanel.svelte`, `lib/playlistActions.js` |
| Song row | `SongCard.svelte` |
