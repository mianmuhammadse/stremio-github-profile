from flask import Flask, Response, jsonify, render_template, redirect, request
from base64 import b64decode, b64encode
from dotenv import load_dotenv, find_dotenv

from util.firestore import get_firestore_db
from util.profanity import profanity_check

load_dotenv(find_dotenv())

from sys import getsizeof
from PIL import Image, ImageFile

from time import time

import io
from util import trakt
import random
import requests
import functools
import colorgram
import math
import html

ImageFile.LOAD_TRUNCATED_IMAGES = True

print("Starting Server")

db = get_firestore_db()
CACHE_TOKEN_INFO = {}

app = Flask(__name__)


@functools.lru_cache(maxsize=128)
def generate_css_bar(num_bar=75):
    css_bar = ""
    left = 1
    for i in range(1, num_bar + 1):

        anim = random.randint(350, 500)
        css_bar += (
            ".bar:nth-child({})  {{ left: {}px; animation-duration: {}ms; }}".format(
                i, left, anim
            )
        )
        left += 4

    return css_bar


@functools.lru_cache(maxsize=128)
def load_image(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error loading image from {url}: {e}")
        # Return a placeholder or None to handle gracefully
        return None
    except Exception as e:
        print(f"Unexpected error loading image: {e}")
        return None


def to_img_b64(content):
    if content is None:
        return ""
    return b64encode(content).decode("ascii")


def load_image_b64(url):
    return to_img_b64(load_image(url))


def isLightOrDark(rgbColor=[0, 128, 255], threshold=127.5):
    # https://stackoverflow.com/a/58270890
    [r, g, b] = rgbColor
    hsp = math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b))
    if hsp > threshold:
        return "light"
    else:
        return "dark"


def encode_html_entities(text):
    return html.escape(text)


def format_time_ms(milliseconds):
    """Convert milliseconds to MM:SS format"""
    if milliseconds is None or milliseconds < 0:
        return "0:00"

    seconds = milliseconds // 1000
    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes}:{seconds:02d}"


def calculate_progress_data(progress_ms, duration_ms):
    """Calculate progress percentage and formatted times"""
    if not progress_ms or not duration_ms or duration_ms <= 0:
        return {
            "progress_percentage": 0,
            "current_time": "0:00",
            "remaining_time": "0:00",
        }

    # Ensure progress doesn't exceed duration
    progress_ms = min(progress_ms, duration_ms)

    # Calculate percentage
    progress_percentage = (progress_ms / duration_ms) * 100

    # Format times
    current_time = format_time_ms(progress_ms)
    remaining_ms = duration_ms - progress_ms
    remaining_time = f"-{format_time_ms(remaining_ms)}"

    return {
        "progress_percentage": progress_percentage,
        "current_time": current_time,
        "remaining_time": remaining_time,
    }


# @functools.lru_cache(maxsize=128)
def make_svg(
    media_info,
    media_title,
    img,
    is_now_playing,
    cover_image,
    theme,
    bar_color,
    show_offline,
    background_color,
    mode,
    progress_ms=None,
    duration_ms=None,
    recents=None,
):
    height = 0
    num_bar = 75
    
    if recents is None:
        recents = []

    # Sanitize input
    media_info = encode_html_entities(media_info)
    media_title = encode_html_entities(media_title)

    # Calculate extra height for recents section
    recents_height = 0
    if recents and len(recents) > 0:
        # Title (30px) + items (48px each) + padding (20px)
        recents_height = 50 + (len(recents) * 48)

    # Use taller height for movie poster images
    if theme == "compact":
        if cover_image:
            height = 550 + recents_height
        else:
            height = 100 + recents_height
    elif theme == "natemoo-re":
        height = 84 + recents_height
        num_bar = 100
    elif theme == "novatorem":
        height = 100 + recents_height
        num_bar = 100
    elif theme == "stremio-embed":
        # stremio-embed has a compact fixed base height
        height = 140 + recents_height
    else:
        if cover_image:
            # Movie posters are taller (2:3 ratio)
            height = 560 + recents_height
        else:
            height = 145 + recents_height

    if is_now_playing:
        title_text = "Now playing"
        content_bar = "".join(["<div class='bar'></div>" for i in range(num_bar)])
        css_bar = generate_css_bar(num_bar)
    elif show_offline:
        title_text = "Not playing"
        content_bar = ""
        css_bar = None
    else:
        title_text = "Recently played"
        content_bar = ""
        css_bar = generate_css_bar(num_bar)

    # Calculate progress data
    progress_data = {}
    if duration_ms is not None:
        if is_now_playing and progress_ms is not None:
            # Currently playing - show real progress
            progress_data = calculate_progress_data(progress_ms, duration_ms)
        else:
            # Recently played - show 0 progress but real duration
            progress_data = calculate_progress_data(0, duration_ms)

    rendered_data = {
        "height": height,
        "num_bar": num_bar,
        "content_bar": content_bar,
        "css_bar": css_bar,
        "title_text": title_text,
        "media_info": media_info,
        "media_title": media_title,
        "img": img,
        "cover_image": cover_image,
        "bar_color": bar_color,
        "background_color": background_color,
        "mode": mode,
        "is_now_playing": is_now_playing,
        "progress_data": progress_data,
        "recents": recents,
        # Stremio-specific aliases
        "title": media_title,
        "subtitle": media_info,
        "meta_info": title_text,
    }

    # Use stremio template
    return render_template(f"stremio.{theme}.html.j2", **rendered_data)


def get_trakt_media_info(uid, show_offline):
    """
    Retrieve playback info for a Trakt-linked user stored in Firestore under `uid`.
    Returns item, is_now_playing, progress_ms, duration_ms
    """
    # Load token from firebase
    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()

    if not doc.exists:
        return None, False, None, None

    token_info = doc.to_dict()

    current_ts = int(time())
    access_token = token_info.get("access_token")

    # Refresh if expired
    expired_ts = token_info.get("expired_ts")
    if expired_ts is None or current_ts >= expired_ts:
        refresh_token = token_info.get("refresh_token")
        if not refresh_token:
            return None, False, None, None

        new_token = trakt.refresh_token(refresh_token)

        # If Trakt returns error, drop token
        if new_token.get("error"):
            doc_ref.delete()
            return None, False, None, None

        expired_ts = int(time()) + int(new_token.get("expires_in", 0))
        update_data = {
            "access_token": new_token.get("access_token"),
            "refresh_token": new_token.get("refresh_token", refresh_token),
            "expired_ts": expired_ts,
        }
        doc_ref.update(update_data)
        access_token = update_data["access_token"]

    # Query Trakt for current playback
    data = trakt.get_current_playback(access_token)

    item = None
    is_now_playing = False
    progress_ms = None
    duration_ms = None

    if data:
        is_now_playing = True
        kind = data.get("type", "movie")

        if kind == "episode":
            # Trakt episode structure: {show: {title}, episode: {title, season, number}}
            show_info = data.get("show", {})
            episode_info = data.get("episode", {})
            show_title = show_info.get("title", "")
            show_year = show_info.get("year", "")
            episode_title = episode_info.get("title", "")
            season = episode_info.get("season", 0)
            episode_num = episode_info.get("number", 0)
            
            # Format: "S01E05 - Episode Title"
            episode_label = f"S{season:02d}E{episode_num:02d}"
            if episode_title:
                episode_label = f"{episode_label} - {episode_title}"
            
            # Get TMDB ID and fetch actual poster
            tmdb_id = show_info.get("ids", {}).get("tmdb")
            poster_url = trakt.get_tmdb_poster(tmdb_id, "tv")
            
            # Get additional metadata from TMDB
            tmdb_details = trakt.get_tmdb_details(tmdb_id, "tv")
            genres = ", ".join([g.get("name", "") for g in tmdb_details.get("genres", [])[:2]])
            
            # Build show title with year
            media_info = show_title
            if show_year:
                media_info = f"{show_title} ({show_year})"
            if genres:
                media_info = f"{media_info} • {genres}"
            
            item = {
                "currently_playing_type": "episode",
                "name": episode_label,
                "show": {"publisher": media_info},
                # Provide safe image structure
                "images": [{"url": poster_url}, {"url": poster_url}] if poster_url else [],
            }
        else:
            # Trakt movie structure: {movie: {title, year, ids}}
            movie_info = data.get("movie", {})
            movie_title = movie_info.get("title", data.get("title", ""))
            movie_year = movie_info.get("year", "")
            
            # Get TMDB ID and fetch actual poster
            tmdb_id = movie_info.get("ids", {}).get("tmdb")
            poster_url = trakt.get_tmdb_poster(tmdb_id, "movie")
            
            # Get additional metadata from TMDB
            tmdb_details = trakt.get_tmdb_details(tmdb_id, "movie")
            genres = ", ".join([g.get("name", "") for g in tmdb_details.get("genres", [])[:2]])
            runtime = tmdb_details.get("runtime", 0)
            
            # Build display title
            display_title = movie_title
            
            # Build artist name with year and genres
            media_info = "Movie"
            if movie_year:
                media_info = f"{movie_year}"
            if genres:
                media_info = f"{media_info} • {genres}"
            if runtime:
                hours = runtime // 60
                mins = runtime % 60
                if hours:
                    media_info = f"{media_info} • {hours}h {mins}m"
                else:
                    media_info = f"{media_info} • {mins}m"
            
            item = {
                "currently_playing_type": "movie",
                "name": display_title,
                "artists": [{"name": media_info}],
                "album": {"images": [{"url": poster_url}, {"url": poster_url}]} if poster_url else {"images": []},
            }

        # Trakt doesn't provide progress/duration in watching endpoint
        progress_ms = None
        duration_ms = None
    elif show_offline:
        return None, False, None, None
    else:
        return None, False, None, None

    return item, is_now_playing, progress_ms, duration_ms


def get_watch_history(uid, limit=5):
    """
    Fetch recent watch history for a user.
    Returns a list of processed history items with title, info, and poster.
    """
    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()

    if not doc.exists:
        return []

    token_info = doc.to_dict()
    access_token = token_info.get("access_token")

    if not access_token:
        return []

    # Fetch history from Trakt
    history = trakt.get_watch_history(access_token, limit=limit)
    
    processed_history = []
    for item in history:
        item_type = item.get("type", "movie")
        watched_at = item.get("watched_at", "")
        
        if item_type == "episode":
            show = item.get("show", {})
            episode = item.get("episode", {})
            show_title = show.get("title", "")
            season = episode.get("season", 0)
            ep_num = episode.get("number", 0)
            ep_title = episode.get("title", "")
            
            title = f"S{season:02d}E{ep_num:02d}"
            if ep_title:
                title = f"{title} - {ep_title}"
            info = show_title
            
            # Get poster
            tmdb_id = show.get("ids", {}).get("tmdb")
            poster_url = trakt.get_tmdb_poster(tmdb_id, "tv") if tmdb_id else None
            
        elif item_type == "movie":
            movie = item.get("movie", {})
            title = movie.get("title", "")
            year = movie.get("year", "")
            info = f"{year}" if year else "Movie"
            
            # Get poster
            tmdb_id = movie.get("ids", {}).get("tmdb")
            poster_url = trakt.get_tmdb_poster(tmdb_id, "movie") if tmdb_id else None
        else:
            continue
        
        processed_history.append({
            "title": title,
            "info": info,
            "poster_url": poster_url,
            "type": item_type,
            "watched_at": watched_at,
        })
    
    return processed_history


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    uid = request.args.get("uid")
    cover_image = request.args.get("cover_image", default="true") == "true"
    is_redirect = request.args.get("redirect", default="false") == "true"
    theme = request.args.get("theme", default="default")
    bar_color = request.args.get("bar_color", default="53b14f")
    background_color = request.args.get("background_color", default="121212")
    is_bar_color_from_cover = (
        request.args.get("bar_color_cover", default="false") == "true"
    )
    show_offline = request.args.get("show_offline", default="false") == "true"
    interchange = request.args.get("interchange", default="false") == "true"
    mode = request.args.get("mode", default="light")
    is_enable_profanity = request.args.get("profanity", default="false") == "true"
    show_recents = request.args.get("show_recents", default="false") == "true"
    recents_limit = int(request.args.get("recents_limit", default="5"))

    # Handle invalid request
    if not uid:
        return Response("not ok")

    # Fetch recent watch history if enabled
    recents = []
    if show_recents:
        try:
            recents = get_watch_history(uid, limit=recents_limit)
        except Exception:
            recents = []

    try:
        item, is_now_playing, progress_ms, duration_ms = get_trakt_media_info(
            uid, show_offline
        )
    except Exception:
        return Response(
            "Error: Invalid Trakt access_token or refresh_token. Possibly the token revoked. Please re-login at /api/login"
        )

    if (show_offline and not is_now_playing) or (item is None):
        if interchange:
            media_info = "Currently not playing on Stremio"
            media_title = "Offline"
        else:
            media_info = "Offline"
            media_title = "Currently not playing on Stremio"
        img_b64 = ""
        cover_image = False
        svg = make_svg(
            media_info,
            media_title,
            img_b64,
            is_now_playing,
            cover_image,
            theme,
            bar_color,
            show_offline,
            background_color,
            mode,
            progress_ms,
            duration_ms,
            recents,
        )
        resp = Response(svg, mimetype="image/svg+xml")
        resp.headers["Cache-Control"] = "s-maxage=1"
        return resp

    currently_playing_type = item.get("currently_playing_type", "track")

    if is_redirect:
        return redirect(item["uri"], code=302)

    img = None
    img_b64 = ""
    if cover_image:

        try:
            if currently_playing_type == "track":
                img = load_image(item["album"]["images"][1]["url"])
            elif currently_playing_type == "episode":
                images = item.get("images", [])
                if len(images) > 1 and images[1].get("url"):
                    img = load_image(images[1]["url"])
            elif currently_playing_type == "movie":
                images = item.get("album", {}).get("images", [])
                if len(images) > 1 and images[1].get("url"):
                    img = load_image(images[1]["url"])
        except (KeyError, IndexError, TypeError) as e:
            print(f"Error loading cover image: {e}")
            img = None

        # Only convert to base64 if image was successfully loaded
        if img is not None:
            img_b64 = to_img_b64(img)

    # Extract cover image color
    if is_bar_color_from_cover and img is not None:

        is_skip_dark = False
        if theme in ["default"]:
            is_skip_dark = True

        try:
            pil_img = Image.open(io.BytesIO(img))
            colors = colorgram.extract(pil_img, 5)
        except Exception as e:
            print(f"Error extracting colors from image: {e}")
            colors = []

        for color in colors:

            rgb = color.rgb

            light_or_dark = isLightOrDark([rgb.r, rgb.g, rgb.b], threshold=80)

            if light_or_dark == "dark" and is_skip_dark:
                # Skip to use bar in dark color
                continue

            bar_color = "%02x%02x%02x" % (rgb.r, rgb.g, rgb.b)
            break

    # Find media_info and media_title
    if currently_playing_type == "track":
        media_info = item["artists"][0]["name"]
        media_title = item["name"]

    elif currently_playing_type == "episode":
        media_info = item["show"]["publisher"]
        media_title = item["name"]

    elif currently_playing_type == "movie":
        # For Stremio/Trakt movies, use title as media_title and generic label as media_info
        media_info = item.get("artists", [{}])[0].get("name", "Movie")
        media_title = item.get("name", "")

    else:
        # Fallback for any other type
        media_info = "Unknown"
        media_title = item.get("name", "")

    # Handle profanity filtering
    if is_enable_profanity:
        media_info = profanity_check(media_info)
        media_title = profanity_check(media_title)

    if interchange:
        x = media_info
        media_info = media_title
        media_title = x

    svg = make_svg(
        media_info,
        media_title,
        img_b64,
        is_now_playing,
        cover_image,
        theme,
        bar_color,
        show_offline,
        background_color,
        mode,
        progress_ms,
        duration_ms,
        recents,
    )

    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "s-maxage=1"

    print("cache size:", getsizeof(CACHE_TOKEN_INFO))

    return resp


if __name__ == "__main__":

    app.run(debug=True, port=5003)
