from flask import Flask, redirect
import importlib

# Import handlers (order matters for Firebase init)
view_module = importlib.import_module("view")
trakt_login_module = importlib.import_module("trakt_login")
trakt_callback_module = importlib.import_module("trakt_callback")

view_handler = view_module.catch_all
view_svg_handler = view_handler  # view.svg.py is identical to view.py
trakt_login_handler = trakt_login_module.catch_all
trakt_callback_handler = trakt_callback_module.catch_all

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
