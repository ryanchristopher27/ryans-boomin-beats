# Ryan's Boomin' Beats

A Spotify-integrated music app with an AI-powered playlist builder. Search tracks, explore your listening history, and generate curated playlists from natural language prompts using Claude or OpenAI.

## Quick Start

See **[docs/setup.md](docs/setup.md)** for full setup instructions.

```bash
# 1. Create and activate the conda environment
conda env create -f environment.yml
conda activate ryans-boomin-beats

# 2. Run the backend (terminal 1)
cd src/web/backend
uvicorn main:app --reload --port 8005

# 3. Run the frontend (terminal 2)
cd src/web/frontend
npm install  # first time only
npm run dev
```

App runs at [http://localhost:5173](http://localhost:5173) · API docs at [http://127.0.0.1:8005/docs](http://127.0.0.1:8005/docs)

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | SvelteKit |
| Backend | FastAPI + Uvicorn |
| Music | Spotify API (Spotipy) |
| AI | Claude (Anthropic) or OpenAI — BYOK |

---

## Features

- **Track Search** — search Spotify's catalog and get seed-based recommendations
- **Profile** — view your top artists and tracks across different time periods
- **Playlist Builder** — describe a playlist in natural language; AI generates and validates songs against Spotify, then lets you save or queue the result

---

## Links

### Docs
- [docs/setup.md](docs/setup.md) — environment setup and first run
- [docs/brainstorm.md](docs/brainstorm.md) — feature design notes
- [docs/plan.md](docs/plan.md) — implementation plan

### References
- [Spotipy](https://spotipy.readthedocs.io/en/2.22.1/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SvelteKit](https://kit.svelte.dev/)
- [Anthropic API](https://docs.anthropic.com/)

---

## Styles

| Name | Hex |
|------|-----|
| Light Blue | `#5ec9ff` |
| Purple | `#a235ff` |
| Dark Gray | `#242424` |
| Gray | `#444444` |
