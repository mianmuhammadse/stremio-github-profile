# stremio-github-profile

Show what you're currently watching on **Stremio** on your GitHub profile!

This works by connecting to **Trakt**, which Stremio can scrobble to. When you watch something on Stremio, it appears on your GitHub README in real-time.

Running on a serverless function, storing data in Firebase (only access_token, refresh_token, and token_expired_timestamp).

## Table of Contents  
- [How It Works](#how-it-works)
- [Connect Your Account](#connect-your-account)
- [Add to Your README](#add-to-your-readme)
- [Example](#example)
- [Query Parameters](#query-parameters)
- [Running Locally](#running-locally)
- [Setting up Firebase](#setting-up-firebase)
- [Setting up Trakt](#setting-up-trakt)
- [Running Tests](#running-tests)
- [How to Contribute](#how-to-contribute)
- [Credit](#credit)

## How It Works

1. **Enable Trakt scrobbling in Stremio** - Go to Stremio Settings → Trakt Scrobbling → Connect your Trakt account
2. **Link your Trakt account here** - Authorize this app to read your watching activity
3. **Add the SVG to your GitHub README** - Shows what you're currently watching!

## Connect Your Account

Click the button below to connect your Trakt account:

[![Connect with Stremio](/img/btn-stremio.svg)](https://spotify-github-profile.kittinanx.com/api/login)

After authorizing, you'll receive your **uid** (your Trakt username).

## Add to Your README

Add this to your GitHub profile README (replace `YOUR_TRAKT_USERNAME` with your uid):

```markdown
![stremio-now-playing](https://spotify-github-profile.kittinanx.com/api/view?uid=YOUR_TRAKT_USERNAME&show_offline=true)
```

## Example

- Default theme (shows movie/TV poster with metadata)

![stremio-github-profile](/img/default.svg)

- Compact theme

![stremio-github-profile](/img/compact.svg)

## Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `uid` | (required) | Your Trakt username |
| `theme` | `default` | Card theme: `default`, `compact`, `natemoo-re`, `novatorem` |
| `show_offline` | `false` | Show "Offline" card when nothing is playing |
| `cover_image` | `true` | Display poster/cover image |
| `background_color` | `121212` | Background color (hex, no #) |
| `bar_color` | `53b14f` | Animation bar color (hex, no #) |

## Running Locally

### Prerequisites
- Python 3.10+
- A Firebase project with Cloud Firestore
- A Trakt API application

### Quick Start

1. Clone the repository and create a virtual environment:
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```sh
   pip install -r api/requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your credentials:
   ```sh
   cp .env.example .env
   ```

4. Run the application:
   ```sh
   python api/app.py
   ```

5. Visit http://localhost:3000/api/login to connect your Trakt account

## Setting up Firebase

1. Create [a new Firebase project](https://console.firebase.google.com/)
2. Enable Cloud Firestore (create a database in production or test mode)
3. Go to _Project Settings_ → _Service accounts_ → _Generate new private key_
4. Convert the JSON file content to BASE64:
   ```sh
   base64 -i your-firebase-key.json
   ```
5. Add the BASE64 string to your `.env` file as `FIREBASE`

## Setting up Trakt

1. Go to [Trakt API Applications](https://trakt.tv/oauth/applications)
2. Create a new application with:
   - **Name**: Your app name
   - **Redirect URI**: `http://localhost:3000/api/callback` (for local dev)
3. Copy the **Client ID** and **Client Secret** to your `.env` file:
   ```sh
   TRAKT_CLIENT_ID='your_client_id'
   TRAKT_CLIENT_SECRET='your_client_secret'
   ```

### Optional: TMDB API for Poster Images

To display movie/TV posters, get a free API key from [TMDB](https://www.themoviedb.org/settings/api):
```sh
TMDB_API_KEY='your_tmdb_api_key'
```

## Running Tests

```sh
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=api --cov-report=html
```

## How to Contribute

- Fork the repo and submit a pull request
- Report bugs on the [Issues](https://github.com/mianmuhammadse/stremio-github-profile.git/issues) page
- Suggest features with the label [Feature Suggestion]

## Credit

- Inspired by [natemoo-re](https://github.com/natemoo-re)
- Original Spotify version by [kittinan](https://github.com/kittinan/spotify-github-profile)
- Uses [Trakt API](https://trakt.tv) for playback detection
- Uses [TMDB API](https://www.themoviedb.org) for poster images
