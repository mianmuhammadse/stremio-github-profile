import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path to import the api module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set TESTING env so Firestore returns a mock
os.environ["TESTING"] = "true"


@pytest.fixture
def client():
    """Create a test client for the view Flask application."""
    from api.view import app
    app.config.update({"TESTING": True})

    with app.test_client() as client:
        yield client


# -------------------------------------------------------------------
# util/trakt.py unit tests
# -------------------------------------------------------------------


def test_generate_token():
    """Test that generate_token calls Trakt API correctly."""
    with patch("util.trakt.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "access_token": "abc",
            "refresh_token": "def",
            "expires_in": 7200,
        }

        from util import trakt

        result = trakt.generate_token("auth_code_123")

        assert result["access_token"] == "abc"
        mock_post.assert_called_once()
        call_json = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1]["json"]
        assert call_json["code"] == "auth_code_123"


def test_refresh_token():
    """Test that refresh_token calls Trakt API correctly."""
    with patch("util.trakt.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "access_token": "new_abc",
            "refresh_token": "new_def",
            "expires_in": 7200,
        }

        from util import trakt

        result = trakt.refresh_token("old_refresh_token")

        assert result["access_token"] == "new_abc"
        mock_post.assert_called_once()


def test_get_user_profile():
    """Test that get_user_profile fetches user from Trakt."""
    with patch("util.trakt.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"username": "trakt_user"}

        from util import trakt

        result = trakt.get_user_profile("access_tok")

        assert result["username"] == "trakt_user"
        mock_get.assert_called_once()


def test_get_current_playback_playing():
    """Test that get_current_playback returns data when user is watching."""
    with patch("util.trakt.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "type": "movie",
            "title": "Inception",
        }

        from util import trakt

        result = trakt.get_current_playback("access_tok")

        assert result["title"] == "Inception"


def test_get_current_playback_nothing():
    """Test that get_current_playback returns {} on 204."""
    with patch("util.trakt.requests.get") as mock_get:
        mock_get.return_value.status_code = 204

        from util import trakt

        result = trakt.get_current_playback("access_tok")

        assert result == {}


# -------------------------------------------------------------------
# api/view.py Trakt integration tests (source=stremio)
# -------------------------------------------------------------------


@patch("api.view.get_trakt_media_info")
@patch("api.view.make_svg")
def test_view_stremio_source_now_playing(mock_make_svg, mock_get_trakt, client):
    """Test that source=stremio routes to get_trakt_media_info."""
    mock_item = {
        "currently_playing_type": "movie",
        "name": "Inception",
        "artists": [{"name": "Inception"}],
        "album": {"images": [{}, {"url": None}]},
    }
    mock_get_trakt.return_value = (mock_item, True, 60000, 120000)
    mock_make_svg.return_value = "<svg>trakt now playing</svg>"

    response = client.get("/?uid=trakt_user&source=stremio")

    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    mock_get_trakt.assert_called_once()
    mock_make_svg.assert_called_once()


@patch("api.view.get_trakt_media_info")
@patch("api.view.make_svg")
def test_view_stremio_offline(mock_make_svg, mock_get_trakt, client):
    """Test Stremio offline scenario."""
    mock_get_trakt.return_value = (None, False, None, None)
    mock_make_svg.return_value = "<svg>offline</svg>"

    response = client.get("/?uid=trakt_user&source=stremio&show_offline=true")

    assert response.status_code == 200
    mock_make_svg.assert_called_once()
    args, _ = mock_make_svg.call_args
    assert "Offline" in args[0] or "Offline" in args[1]


@patch("api.view.get_trakt_media_info")
def test_view_stremio_invalid_token(mock_get_trakt, client):
    """Test handling of exception from Trakt flow."""
    mock_get_trakt.side_effect = Exception("Token error")

    response = client.get("/?uid=trakt_user&source=stremio")

    assert response.status_code == 200
    assert b"Invalid Trakt access_token" in response.data


# -------------------------------------------------------------------
# api/trakt_login.py tests
# -------------------------------------------------------------------


def test_trakt_login_redirect():
    """Test that trakt_login redirects to Trakt authorize URL."""
    from api.trakt_login import app

    app.config.update({"TESTING": True})

    with app.test_client() as test_client:
        response = test_client.get("/")

    assert response.status_code == 302
    assert "trakt.tv/oauth/authorize" in response.headers["Location"]


# -------------------------------------------------------------------
# api/trakt_callback.py tests
# -------------------------------------------------------------------


@patch("api.trakt_callback.trakt.generate_token")
@patch("api.trakt_callback.trakt.get_user_profile")
@patch("api.trakt_callback.db")
def test_trakt_callback_stores_token(mock_db, mock_profile, mock_gen_token):
    """Test that trakt_callback stores token in Firestore and renders template."""
    mock_gen_token.return_value = {
        "access_token": "at",
        "refresh_token": "rt",
        "expires_in": 7200,
    }
    mock_profile.return_value = {"username": "trakt_user"}
    mock_doc_ref = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_doc_ref

    from api.trakt_callback import app

    app.config.update({"TESTING": True})

    with app.test_client() as test_client:
        response = test_client.get("/?code=auth_code")

    assert response.status_code == 200
    mock_doc_ref.set.assert_called_once()
    stored = mock_doc_ref.set.call_args[0][0]
    assert stored["access_token"] == "at"
    assert "expired_ts" in stored
