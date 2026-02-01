from flask import Flask, redirect
from util import trakt

app = Flask(__name__)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    # Trakt authorize URL
    trakt_auth_url = f"https://trakt.tv/oauth/authorize?response_type=code&client_id={trakt.TRAKT_CLIENT_ID}&redirect_uri={trakt.REDIRECT_URI}"
    return redirect(trakt_auth_url)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
