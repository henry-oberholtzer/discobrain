from unittest.mock import MagicMock, patch

from discobrain.mb_auth import (
    clear_musicbrainz_session,
    get_musicbrainz_session,
    get_musicbrainz_username,
    is_musicbrainz_authenticated,
)


def test_mb_settings_page_renders_without_client_credentials(client, monkeypatch):
    monkeypatch.delenv("MUSICBRAINZ_CLIENT_ID", raising=False)
    monkeypatch.delenv("MUSICBRAINZ_CLIENT_SECRET", raising=False)
    resp = client.get("/settings")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Settings" in html
    assert "MusicBrainz" in html
    assert "OAuth 2.0 Authorization" in html
    assert "OAuth Unavailable" in html


def test_mb_connect_redirects_to_settings(client):
    resp = client.get("/musicbrainz/connect")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/settings")


def test_mb_settings_page_renders_with_client_credentials(client, monkeypatch):
    monkeypatch.setenv("MUSICBRAINZ_CLIENT_ID", "mb_client_123")
    monkeypatch.setenv("MUSICBRAINZ_CLIENT_SECRET", "mb_secret_456")

    resp = client.get("/settings")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Authorize with MusicBrainz" in html


def test_mb_settings_page_shows_authenticated_state(client):
    with client.session_transaction() as sess:
        sess["musicbrainz_oauth_token"] = "valid_mb_token"
        sess["musicbrainz_username"] = "music_editor"

    resp = client.get("/settings")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "music_editor" in html
    assert "Disconnect MusicBrainz" in html


def test_mb_login_missing_credentials(client, monkeypatch):
    monkeypatch.delenv("MUSICBRAINZ_CLIENT_ID", raising=False)
    monkeypatch.delenv("MUSICBRAINZ_CLIENT_SECRET", raising=False)

    resp = client.get("/musicbrainz/login", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "MusicBrainz OAuth requires MUSICBRAINZ_CLIENT_ID and MUSICBRAINZ_CLIENT_SECRET" in html


def test_mb_login_already_authenticated(client, monkeypatch):
    monkeypatch.setenv("MUSICBRAINZ_CLIENT_ID", "mock_id")
    monkeypatch.setenv("MUSICBRAINZ_CLIENT_SECRET", "mock_secret")

    with client.session_transaction() as sess:
        sess["musicbrainz_oauth_token"] = "existing_access_token"

    with patch("discobrain.mb_auth.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"sub": "existing_user"}
        mock_get.return_value = mock_resp

        resp = client.get("/musicbrainz/login", follow_redirects=True)
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Already connected to MusicBrainz as existing_user." in html


def test_mb_login_initiates_oauth(client, monkeypatch):
    monkeypatch.setenv("MUSICBRAINZ_CLIENT_ID", "env_client_id")
    monkeypatch.setenv("MUSICBRAINZ_CLIENT_SECRET", "env_client_secret")

    with patch("discobrain.mb_auth.OAuth2Session") as mock_oauth_cls:
        mock_oauth = MagicMock()
        mock_oauth_cls.return_value = mock_oauth
        mock_oauth.authorization_url.return_value = (
            "https://musicbrainz.org/oauth2/authorize?client_id=123",
            "mock_state_abc",
        )

        resp = client.get("/musicbrainz/login")
        assert resp.status_code == 302
        assert resp.headers["Location"].startswith("https://musicbrainz.org/oauth2/authorize")

        with client.session_transaction() as sess:
            assert sess["musicbrainz_oauth_state"] == "mock_state_abc"


def test_mb_callback_error(client):
    resp = client.get(
        "/musicbrainz/callback?error=access_denied&error_description=User+denied",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "MusicBrainz authorization error: User denied" in html


def test_mb_callback_invalid_state(client):
    with client.session_transaction() as sess:
        sess["musicbrainz_oauth_state"] = "expected_state_123"

    resp = client.get("/musicbrainz/callback?code=code_abc&state=wrong_state", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Invalid OAuth state." in html


def test_mb_callback_missing_code(client):
    with client.session_transaction() as sess:
        sess["musicbrainz_oauth_state"] = "state_123"

    resp = client.get("/musicbrainz/callback?state=state_123", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Authorization code missing from MusicBrainz response." in html


def test_mb_callback_success(client, monkeypatch):
    monkeypatch.setenv("MUSICBRAINZ_CLIENT_ID", "cid")
    monkeypatch.setenv("MUSICBRAINZ_CLIENT_SECRET", "csecret")

    with client.session_transaction() as sess:
        sess["musicbrainz_oauth_state"] = "valid_state_123"

    with patch("discobrain.mb_auth.OAuth2Session") as mock_oauth_cls:
        mock_oauth = MagicMock()
        mock_oauth_cls.return_value = mock_oauth
        mock_oauth.fetch_token.return_value = {
            "access_token": "mb_access_tok",
            "refresh_token": "mb_refresh_tok",
            "token_type": "Bearer",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"sub": "mb_superuser"}
        mock_oauth.get.return_value = mock_resp

        resp = client.get("/musicbrainz/callback?code=valid_code&state=valid_state_123")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/settings")

        with client.session_transaction() as sess:
            assert sess["musicbrainz_oauth_token"] == "mb_access_tok"
            assert sess["musicbrainz_refresh_token"] == "mb_refresh_tok"
            assert sess["musicbrainz_username"] == "mb_superuser"


def test_mb_logout(client):
    with client.session_transaction() as sess:
        sess["musicbrainz_oauth_token"] = "mb_access_tok"
        sess["musicbrainz_username"] = "mb_superuser"

    resp = client.get("/musicbrainz/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/settings")

    with client.session_transaction() as sess:
        assert "musicbrainz_oauth_token" not in sess
        assert "musicbrainz_username" not in sess


def test_mb_helper_functions(app):
    with app.test_request_context("/"):
        from flask import session
        assert is_musicbrainz_authenticated() is False
        assert get_musicbrainz_username() is None
        assert get_musicbrainz_session() is None

        session["musicbrainz_oauth_token"] = "tok_123"
        session["musicbrainz_username"] = "user_abc"
        assert is_musicbrainz_authenticated() is True
        assert get_musicbrainz_username() == "user_abc"

        mb_sess = get_musicbrainz_session()
        assert mb_sess is not None
        assert mb_sess.token.get("access_token") == "tok_123"

        clear_musicbrainz_session()
        assert is_musicbrainz_authenticated() is False
        assert get_musicbrainz_username() is None


def test_user_loader_musicbrainz_integration(client):
    with client:
        client.get("/")
        from flask import g
        assert g.musicbrainz["authenticated"] is False
        assert g.musicbrainz["username"] == "None" or g.musicbrainz["username"] is None

    with client.session_transaction() as sess:
        sess["musicbrainz_oauth_token"] = "session_token"
        sess["musicbrainz_username"] = "session_user"

    with client:
        client.get("/")
        from flask import g
        assert g.musicbrainz["authenticated"] is True
        assert g.musicbrainz["username"] == "session_user"
