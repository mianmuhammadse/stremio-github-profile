from flask import Flask, Response, render_template, request
from dotenv import load_dotenv, find_dotenv
import traceback
import logging

load_dotenv(find_dotenv())

from util.firestore import get_firestore_db
from util import trakt

print("Starting Trakt Callback Server")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = get_firestore_db()

app = Flask(__name__)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    code = request.args.get("code")

    if code is None:
        return Response("not ok")

    try:
        logger.info(f"Processing callback with code: {code[:10]}...")
        
        token_info = trakt.generate_token(code)
        logger.info(f"Token response keys: {list(token_info.keys()) if token_info else 'None'}")
        
        access_token = token_info.get("access_token")
        if not access_token:
            logger.error(f"No access_token in response: {token_info}")
            return Response(f"Token exchange failed: {token_info.get('error', 'Unknown error')}", status=400)
        logger.info(f"Got access token: {access_token[:10]}...")

        # Get trakt user info to extract a stable uid
        trakt_user = trakt.get_user_profile(access_token)
        logger.info(f"User profile response: {trakt_user}")
        
        # Trakt returns 'username' for the user's handle
        user_id = trakt_user.get("username") or trakt_user.get("id")
        logger.info(f"Extracted user_id: {user_id}")

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
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error in Trakt callback: {e}")
        logger.error(f"Full traceback:\n{error_details}")
        print(f"ERROR: {e}\nTraceback:\n{error_details}")
        return Response(f"error processing trakt callback: {str(e)}", status=400)


if __name__ == "__main__":
    app.run(debug=True)
