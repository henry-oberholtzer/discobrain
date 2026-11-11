import os

import requests
from flask import (
    Blueprint,
    flash,
    redirect,
    request,
    session,
    url_for,
)
from oauthlib.oauth1 import OAuth1Error
from requests_oauthlib import OAuth1Session
from requests_oauthlib.oauth1_session import TokenRequestDenied
from werkzeug.wrappers.response import Response

DISCOGS_REQUEST_TOKEN_URL = "https://api.discogs.com/oauth/request_token"
DISCOGS_AUTHORIZE_URL = "https://www.discogs.com/oauth/authorize"
DISCOGS_ACCESS_TOKEN_URL = "https://api.discogs.com/oauth/access_token"
DISCOGS_IDENTITY_URL = "https://api.discogs.com/oauth/identity"

USER_AGENT = "Discobrain/0.0.1 ( henryoberholtzer@gmail.com )"

bp = Blueprint("discogs", __name__, url_prefix="/discogs")


def get_consumer_credentials() -> tuple[str, str]:
    consumer_key = os.getenv("DISCOGS_CONSUMER_KEY") or ""
    consumer_secret = os.getenv("DISCOGS_CONSUMER_SECRET") or ""
    return consumer_key, consumer_secret


@bp.route("/", methods=["GET"])
@bp.route("/connect", methods=["GET"])
def connect() -> Response:
    return redirect(url_for("settings"))


@bp.route("/token", methods=["POST"])
def token_auth() -> Response:
    token = request.form.get("token", "").strip()
    if not token:
        flash("Please enter a valid Discogs Personal Access Token.", "error")
        return redirect(url_for("settings"))

    try:
        resp = requests.get(
            DISCOGS_IDENTITY_URL,
            headers={
                "User-Agent": USER_AGENT,
                "Authorization": f"Discogs token={token}",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            user_data = resp.json()
            username = user_data.get("username", "Discogs User")
            session["discogs_user_token"] = token
            session["discogs_username"] = username
            session.pop("discogs_access_token", None)
            session.pop("discogs_access_token_secret", None)
            flash(
                f"Successfully connected to Discogs as {username} (60 requests/min).",
                "success",
            )
            return redirect(url_for("settings"))
        else:
            flash(
                "Invalid Discogs Personal Access Token. Please verify the token.",
                "error",
            )
            return redirect(url_for("settings"))
    except requests.RequestException as e:
        flash(f"Error validating token with Discogs: {e}", "error")
        return redirect(url_for("settings"))


@bp.route("/login", methods=["GET"])
@bp.route("/oauth", methods=["GET"])
def login() -> Response:
    consumer_key, consumer_secret = get_consumer_credentials()
    if not consumer_key or not consumer_secret:
        flash(
            "Discogs OAuth requires DISCOGS_CONSUMER_KEY and DISCOGS_CONSUMER_SECRET in your environment or .env file. Alternatively, connect using a Personal Access Token.",
            "warning",
        )
        return redirect(url_for("settings"))

    access_token = session.get("discogs_access_token")
    access_token_secret = session.get("discogs_access_token_secret")

    if access_token and access_token_secret:
        discogs = OAuth1Session(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )
        try:
            resp = discogs.get(
                DISCOGS_IDENTITY_URL, headers={"User-Agent": USER_AGENT}, timeout=10
            )
            if resp.status_code == 200:
                user_data = resp.json()
                username = user_data.get("username", "Discogs User")
                session["discogs_username"] = username
                flash(f"Already connected as {username}.", "info")
                return redirect(url_for("settings"))
        except requests.RequestException:
            pass

    discogs = OAuth1Session(
        client_key=consumer_key,
        client_secret=consumer_secret,
        callback_uri=url_for("discogs.auth", _external=True),
    )
    try:
        req_token_dict = discogs.fetch_request_token(
            DISCOGS_REQUEST_TOKEN_URL,
            headers={"User-Agent": USER_AGENT},
        )
        session["discogs_req_token"] = req_token_dict.get("oauth_token")
        session["discogs_req_token_secret"] = req_token_dict.get("oauth_token_secret")
        auth_url = discogs.authorization_url(DISCOGS_AUTHORIZE_URL)
        return redirect(auth_url)
    except (TokenRequestDenied, OAuth1Error, ValueError, requests.RequestException) as e:
        flash(f"Discogs OAuth initiation failed: {e}", "error")
        return redirect(url_for("settings"))


@bp.route("/auth", methods=["GET"])
def auth() -> Response:
    if request.args.get("denied"):
        session.pop("discogs_req_token", None)
        session.pop("discogs_req_token_secret", None)
        flash("Discogs authorization was cancelled.", "info")
        return redirect(url_for("settings"))

    consumer_key, consumer_secret = get_consumer_credentials()
    verifier = request.args.get("oauth_verifier")
    req_token = session.get("discogs_req_token")
    req_token_secret = session.get("discogs_req_token_secret")

    if not verifier or not req_token or not req_token_secret:
        flash(
            "Invalid OAuth verification flow. Please try authenticating again.",
            "error",
        )
        return redirect(url_for("settings"))

    try:
        discogs = OAuth1Session(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=req_token,
            resource_owner_secret=req_token_secret,
            verifier=verifier,
        )
        tokens = discogs.fetch_access_token(
            DISCOGS_ACCESS_TOKEN_URL,
            headers={"User-Agent": USER_AGENT},
        )
        session["discogs_access_token"] = tokens.get("oauth_token")
        session["discogs_access_token_secret"] = tokens.get("oauth_token_secret")
        session.pop("discogs_req_token", None)
        session.pop("discogs_req_token_secret", None)
        session.pop("discogs_user_token", None)

        resp = discogs.get(
            DISCOGS_IDENTITY_URL, headers={"User-Agent": USER_AGENT}, timeout=10
        )
        username = "Discogs User"
        if resp.status_code == 200:
            username = resp.json().get("username", "Discogs User")
        session["discogs_username"] = username

        flash(
            f"Successfully authenticated with Discogs as {username} (60 requests/min)!",
            "success",
        )
        return redirect(url_for("settings"))
    except (TokenRequestDenied, OAuth1Error, ValueError, requests.RequestException) as e:
        flash(f"Failed to obtain Discogs access token: {e}", "error")
        return redirect(url_for("settings"))


@bp.route("/logout", methods=["GET", "POST"])
def logout() -> Response:
    session.pop("discogs_access_token", None)
    session.pop("discogs_access_token_secret", None)
    session.pop("discogs_req_token", None)
    session.pop("discogs_req_token_secret", None)
    session.pop("discogs_user_token", None)
    session.pop("discogs_username", None)
    flash("Disconnected from Discogs.", "info")
    return redirect(request.referrer or url_for("settings"))
