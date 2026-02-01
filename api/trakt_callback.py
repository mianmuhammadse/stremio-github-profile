from flask import Flask, Response, render_template, request
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from util.firestore import get_firestore_db
from util import trakt

print("Starting Trakt Callback Server")

db = get_firestore_db()

app = Flask(__name__)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    code = request.args.get("code")

    if code is None:
        return Response("not ok")

    token_info = trakt.generate_token(code)
    access_token = token_info.get("access_token")

    # Get trakt user info to extract a stable uid
    trakt_user = trakt.get_user_profile(access_token)
    # Trakt returns 'username' for the user's handle
    user_id = trakt_user.get("username") or trakt_user.get("id")

    # Store token_info in Firestore similar to Spotify flow
    doc_ref = db.collection("users").document(user_id)
    # Add an expiry timestamp if expires_in present
    if token_info.get("expires_in"):
        from time import time

        token_info["expired_ts"] = int(time()) + int(token_info["expires_in"])

    doc_ref.set(token_info)

    rendered_data = {
        "uid": user_id,
        "BASE_URL": trakt.BASE_URL,
    }

    return render_template("trakt_callback.html.j2", **rendered_data)


if __name__ == "__main__":
    app.run(debug=True)
