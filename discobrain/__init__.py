import os
from typing import TypedDict

from dotenv import load_dotenv
from flask import Flask, g, session

from . import auth

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("DISCOBRAIN_SECRET_KEY", "dev-secret-key-change-me")
app.register_blueprint(auth.bp)


class AppUser(TypedDict):
    authenticated: bool
    username: str | None
    rate_limit: int


@app.before_request
def load_user():
    user: AppUser = {
        "authenticated": False,
        "username": None,
        "rate_limit": 25,
    }
    if session.get("discogs_access_token"):
        user["authenticated"] = True
        user["username"] = session.get("discogs_username") or "Discogs User"
        user["rate_limit"] = 60
    elif os.getenv("DISCOGS_USER_TOKEN") or os.getenv("DISCOGS_API_KEY"):
        user["authenticated"] = True
        user["username"] = "API Token User"
        user["rate_limit"] = 60
    g.user = user

@app.route("/")
def index():
    return "Hello"


@app.route("/submit")
def form():
    html = """
    <html>
        <form id="form" action="https://musicbrainz.org/release/add" method="post" target="_blank">
            <input type="submit" value="Submit to MusicBrainz">
        </form>
        <button
    </html>
    """
    return html
