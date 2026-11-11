import os
from typing import Any

import requests
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for,
)
from oauthlib.oauth2 import OAuth2Error
from requests_oauthlib import OAuth2Session
from requests_ratelimiter import LimiterAdapter
from werkzeug.wrappers.response import Response

MUSICBRAINZ_AUTHORIZE_URL = "https://musicbrainz.org/oauth2/authorize"
MUSICBRAINZ_TOKEN_URL = "https://musicbrainz.org/oauth2/token"
MUSICBRAINZ_USERINFO_URL = "https://musicbrainz.org/oauth2/userinfo"
MUSICBRAINZ_SCOPES = ["profile", "tag"]

USER_AGENT = "Discobrain/0.0.1 ( henryoberholtzer@gmail.com )"

# Allow HTTP redirect in development/test environments
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

bp = Blueprint("musicbrainz", __name__, url_prefix="/musicbrainz")


def get_musicbrainz_client_credentials() -> tuple[str, str]:
    client_id = (
        current_app.config.get("MUSICBRAINZ_CLIENT_ID")
        or os.getenv("MUSICBRAINZ_CLIENT_ID")
        or ""
    )
    client_secret = (
        current_app.config.get("MUSICBRAINZ_CLIENT_SECRET")
        or os.getenv("MUSICBRAINZ_CLIENT_SECRET")
        or ""
    )
    return client_id, client_secret


def get_musicbrainz_access_token() -> str | None:
    return session.get("musicbrainz_oauth_token")


def get_musicbrainz_refresh_token() -> str | None:
    return session.get("musicbrainz_refresh_token")


def is_musicbrainz_authenticated() -> bool:
    return bool(session.get("musicbrainz_oauth_token"))


def get_musicbrainz_username() -> str | None:
    return session.get("musicbrainz_username")


def clear_musicbrainz_session() -> None:
    session.pop("musicbrainz_oauth_token", None)
    session.pop("musicbrainz_refresh_token", None)
    session.pop("musicbrainz_token", None)
    session.pop("musicbrainz_username", None)
    session.pop("musicbrainz_oauth_state", None)


def get_musicbrainz_session() -> OAuth2Session | None:
    access_token = session.get("musicbrainz_oauth_token")
    if not access_token:
        return None

    client_id, client_secret = get_musicbrainz_client_credentials()
    refresh_token = session.get("musicbrainz_refresh_token")
    token = session.get("musicbrainz_token") or {
        "access_token": access_token,
        "token_type": "Bearer",
        "refresh_token": refresh_token,
    }

    def token_updater(new_token: dict[str, Any]) -> None:
        session["musicbrainz_token"] = new_token
        session["musicbrainz_oauth_token"] = new_token.get("access_token")
        if "refresh_token" in new_token:
            session["musicbrainz_refresh_token"] = new_token.get("refresh_token")

    extra = {"client_id": client_id, "client_secret": client_secret}
    has_refresh = bool(refresh_token or (isinstance(token, dict) and token.get("refresh_token")))
    auto_refresh_url = MUSICBRAINZ_TOKEN_URL if (client_id and client_secret and has_refresh) else None
    oauth = OAuth2Session(
        client_id=client_id,
        token=token,
        auto_refresh_kwargs=extra,
        auto_refresh_url=auto_refresh_url,
        token_updater=token_updater,
    )
    oauth.headers.update({"User-Agent": USER_AGENT})
    oauth.mount("https://", LimiterAdapter(per_second=1))
    return oauth


@bp.route("/login", methods=["GET"])
@bp.route("/oauth", methods=["GET"])
def login() -> Response:
    client_id, client_secret = get_musicbrainz_client_credentials()
    if not client_id or not client_secret:
        flash(
            "MusicBrainz OAuth requires MUSICBRAINZ_CLIENT_ID and MUSICBRAINZ_CLIENT_SECRET "
            "in your environment or .env file.",
            "warning",
        )
        return redirect(url_for("settings"))

    access_token = session.get("musicbrainz_oauth_token")
    if access_token:
        try:
            resp = requests.get(
                MUSICBRAINZ_USERINFO_URL,
                headers={
                    "User-Agent": USER_AGENT,
                    "Authorization": f"Bearer {access_token}",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                user_data = resp.json()
                username = (
                    user_data.get("sub")
                    or user_data.get("username")
                    or user_data.get("name")
                    or "MusicBrainz User"
                )
                session["musicbrainz_username"] = username
                flash(f"Already connected to MusicBrainz as {username}.", "info")
                return redirect(url_for("settings"))
        except requests.RequestException:
            pass

    redirect_uri = url_for("musicbrainz.callback", _external=True)
    mb_oauth = OAuth2Session(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=MUSICBRAINZ_SCOPES,
    )
    try:
        auth_url, state = mb_oauth.authorization_url(
            MUSICBRAINZ_AUTHORIZE_URL,
            access_type="offline",
        )
        session["musicbrainz_oauth_state"] = state
        return redirect(auth_url)
    except (OAuth2Error, ValueError, requests.RequestException) as e:
        flash(f"MusicBrainz OAuth initiation failed: {e}", "error")
        return redirect(url_for("settings"))


@bp.route("/callback", methods=["GET"])
def callback() -> Response:
    error = request.args.get("error")
    if error:
        error_desc = request.args.get("error_description", error)
        session.pop("musicbrainz_oauth_state", None)
        flash(f"MusicBrainz authorization error: {error_desc}", "error")
        return redirect(url_for("settings"))

    expected_state = session.pop("musicbrainz_oauth_state", None)
    returned_state = request.args.get("state")
    if not expected_state or expected_state != returned_state:
        flash("Invalid OAuth state. Please try authenticating again.", "error")
        return redirect(url_for("settings"))

    code = request.args.get("code")
    if not code:
        flash("Authorization code missing from MusicBrainz response.", "error")
        return redirect(url_for("settings"))

    client_id, client_secret = get_musicbrainz_client_credentials()
    redirect_uri = url_for("musicbrainz.callback", _external=True)

    try:
        mb_oauth = OAuth2Session(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=expected_state,
        )
        token = mb_oauth.fetch_token(
            MUSICBRAINZ_TOKEN_URL,
            client_secret=client_secret,
            code=code,
            headers={"User-Agent": USER_AGENT},
        )
        session["musicbrainz_token"] = token
        session["musicbrainz_oauth_token"] = token.get("access_token")
        session["musicbrainz_refresh_token"] = token.get("refresh_token")

        resp = mb_oauth.get(
            MUSICBRAINZ_USERINFO_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        username = "MusicBrainz User"
        if resp.status_code == 200:
            user_data = resp.json()
            username = (
                user_data.get("sub")
                or user_data.get("username")
                or user_data.get("name")
                or "MusicBrainz User"
            )
        session["musicbrainz_username"] = username

        flash(
            f"Successfully authenticated with MusicBrainz as {username}!",
            "success",
        )
        return redirect(url_for("settings"))
    except (OAuth2Error, ValueError, requests.RequestException) as e:
        flash(f"Failed to obtain MusicBrainz access token: {e}", "error")
        return redirect(url_for("settings"))


@bp.route("/logout", methods=["GET", "POST"])
@bp.route("/disconnect", methods=["GET", "POST"])
def logout() -> Response:
    clear_musicbrainz_session()
    flash("Disconnected from MusicBrainz.", "info")
    return redirect(request.referrer or url_for("settings"))
