from flask import Flask, redirect

# Import handlers directly (works with Gunicorn)
from api.view import catch_all as view_handler
from api.trakt_login import catch_all as trakt_login_handler
from api.trakt_callback import catch_all as trakt_callback_handler

view_svg_handler = view_handler  # view.svg.py is identical to view.py

app = Flask(__name__)


@app.route("/")
def index():
    return redirect("/api/login")


@app.route("/api/login", defaults={"path": ""})
@app.route("/api/login/<path:path>")
def login(path):
    """Redirect to Trakt login for Stremio integration"""
    return trakt_login_handler(path)


@app.route("/api/callback", defaults={"path": ""})
@app.route("/api/callback/<path:path>")
def callback(path):
    """Handle Trakt OAuth callback"""
    return trakt_callback_handler(path)


@app.route("/api/view", defaults={"path": ""})
@app.route("/api/view/<path:path>")
def view(path):
    return view_handler(path)


@app.route("/api/view.svg", defaults={"path": ""})
@app.route("/api/view.svg/<path:path>")
def view_svg(path):
    return view_svg_handler(path)


@app.route("/api/trakt_login", defaults={"path": ""})
@app.route("/api/trakt_login/<path:path>")
def trakt_login(path):
    return trakt_login_handler(path)


@app.route("/api/trakt_callback", defaults={"path": ""})
@app.route("/api/trakt_callback/<path:path>")
def trakt_callback(path):
    return trakt_callback_handler(path)


if __name__ == "__main__":
    app.run(debug=True, port=3000)
