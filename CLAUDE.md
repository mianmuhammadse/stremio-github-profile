# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flask web app that displays what you're currently watching on Stremio (via Trakt) as an SVG badge or HTML widget on your GitHub profile. OAuth flow stores tokens in Firebase Firestore; the view endpoint reads playback state from Trakt and renders themed SVG/HTML.

## Commands

### Run locally (Docker)
```bash
docker-compose up
```
Three services: view (5003), trakt-login (5001), trakt-callback (5002).

### Run tests
```bash
pip install -r api/requirements.txt
pytest tests/ -v
pytest tests/ -v --cov=api --cov-report=html   # with coverage
pytest tests/test_trakt_integration.py -v -k "test_name"  # single test
```
Test markers: `slow`, `integration`, `unit`.

### Code quality (matches CI)
```bash
black --check api/ util/ tests/
isort --check-only api/ util/ tests/
mypy api/ util/
bandit -r api/ util/
```

## Architecture

### Request Flow
1. **OAuth**: `/api/login` → Trakt authorize → `/api/callback` exchanges code for tokens → stored in Firestore keyed by Trakt username
2. **SVG view**: `/api/view?uid=...` → reads tokens from Firestore → refreshes if expired → calls Trakt playback API → renders Jinja2 SVG template → returns with no-cache headers (for GitHub Camo)
3. **HTML widget**: `/api/widget?uid=...` → same data flow → renders auto-refreshing HTML page for iframe embedding

### Key Files
- `api/app.py` — Flask route definitions (delegates to handlers)
- `api/view.py` — SVG/widget rendering (`catch_all()` for SVG, `widget()` for HTML)
- `api/trakt_login.py` / `api/trakt_callback.py` — OAuth handlers
- `util/trakt.py` — Trakt API client (token management, playback, history, TMDB posters)
- `util/firestore.py` — Firebase Firestore client init
- `api/templates/` — 7 SVG theme variants + widget HTML template (Jinja2)

### Environment Variables
- `TRAKT_CLIENT_ID`, `TRAKT_CLIENT_SECRET` — Trakt API credentials
- `BASE_URL` — OAuth callback base (e.g., `http://localhost:3000/api`)
- `FIREBASE` — Base64-encoded Firebase service account JSON
- `TMDB_API_KEY` — Optional, for poster images

### Design Decisions
- Images are base64-embedded in SVG for GitHub Camo proxy compatibility
- Aggressive no-cache headers on SVG responses to force fresh data on GitHub
- Token refresh happens inline during view requests when tokens are expired
- Profanity filter applied to media titles before rendering
