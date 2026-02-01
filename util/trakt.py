from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import os
import requests
from time import time

TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")
TRAKT_CLIENT_SECRET = os.getenv("TRAKT_CLIENT_SECRET")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")  # Optional for poster images
BASE_URL = os.getenv("BASE_URL")

# Redirect path for Trakt OAuth callback
REDIRECT_URI = f"{BASE_URL}/trakt_callback"

TRAKT_TOKEN_URL = "https://api.trakt.tv/oauth/token"
TRAKT_API_BASE = "https://api.trakt.tv"
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w300"


def generate_token(authorization_code):
    data = {
        "code": authorization_code,
        "client_id": TRAKT_CLIENT_ID,
        "client_secret": TRAKT_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(TRAKT_TOKEN_URL, json=data)
    return response.json()


def refresh_token(refresh_token):
    data = {
        "refresh_token": refresh_token,
        "client_id": TRAKT_CLIENT_ID,
        "client_secret": TRAKT_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "refresh_token",
    }

    response = requests.post(TRAKT_TOKEN_URL, json=data)
    return response.json()


def get_user_profile(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "trakt-api-version": "2",
        "trakt-api-key": TRAKT_CLIENT_ID,
    }

    url = f"{TRAKT_API_BASE}/users/me"
    response = requests.get(url, headers=headers)
    return response.json()


def get_current_playback(access_token):
    """
    Attempt to fetch the user's currently watching item from Trakt.
    Returns a dict or empty dict when nothing is playing.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "trakt-api-version": "2",
        "trakt-api-key": TRAKT_CLIENT_ID,
    }

    url = f"{TRAKT_API_BASE}/users/me/watching"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code in (204, 404):
            return {}
        return resp.json()
    except Exception:
        return {}


def get_watch_history(access_token, limit=5):
    """
    Fetch the user's recent watch history from Trakt.
    Returns a list of recently watched items (movies and episodes).
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "trakt-api-version": "2",
        "trakt-api-key": TRAKT_CLIENT_ID,
    }

    url = f"{TRAKT_API_BASE}/users/me/history"
    params = {"limit": limit}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []


def get_tmdb_poster(tmdb_id, media_type="tv"):
    """
    Fetch poster image URL from TMDB API.
    media_type: 'tv' for shows, 'movie' for movies
    Returns poster URL or None if not found.
    """
    if not TMDB_API_KEY or not tmdb_id:
        return None
    
    try:
        url = f"{TMDB_API_BASE}/{media_type}/{tmdb_id}"
        params = {"api_key": TMDB_API_KEY}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            poster_path = data.get("poster_path")
            if poster_path:
                return f"{TMDB_IMAGE_BASE}{poster_path}"
    except Exception:
        pass
    return None


def get_tmdb_details(tmdb_id, media_type="tv"):
    """
    Fetch detailed info from TMDB API including genres, year, runtime, etc.
    media_type: 'tv' for shows, 'movie' for movies
    Returns dict with details or empty dict.
    """
    if not TMDB_API_KEY or not tmdb_id:
        return {}
    
    try:
        url = f"{TMDB_API_BASE}/{media_type}/{tmdb_id}"
        params = {"api_key": TMDB_API_KEY}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}
