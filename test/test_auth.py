from unittest.mock import MagicMock, patch


def test_connect_page_renders_without_consumer_keys(client, monkeypatch):
    monkeypatch.delenv("DISCOGS_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("DISCOGS_CONSUMER_SECRET", raising=False)
    resp = client.get("/discogs/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Connect Discogs Account" in html
    assert "Option 1: Personal Access Token" in html
    assert "Option 2: OAuth 1.0a" in html
    assert "OAuth Unavailable (Keys Missing)" in html


def test_connect_page_renders_with_consumer_keys(client, monkeypatch):
    monkeypatch.setenv("DISCOGS_CONSUMER_KEY", "mock_key")
    monkeypatch.setenv("DISCOGS_CONSUMER_SECRET", "mock_secret")

    resp = client.get("/discogs/connect")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Authorize via Discogs OAuth" in html


def test_token_auth_empty_input(client):
    resp = client.post("/discogs/token", data={"token": "   "}, follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Please enter a valid Discogs Personal Access Token." in html


def test_token_auth_success(client):
    with patch("discobrain.auth.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"username": "vinyl_enthusiast"}
        mock_get.return_value = mock_resp

        resp = client.post("/discogs/token", data={"token": "valid_user_token_abc"})
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/")

        with client.session_transaction() as sess:
            assert sess["discogs_user_token"] == "valid_user_token_abc"
            assert sess["discogs_username"] == "vinyl_enthusiast"


def test_token_auth_invalid(client):
    with patch("discobrain.auth.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        resp = client.post(
            "/discogs/token", data={"token": "bad_token_123"}, follow_redirects=True
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Invalid Discogs Personal Access Token." in html

        with client.session_transaction() as sess:
            assert "discogs_user_token" not in sess


def test_oauth_login_missing_consumer_keys(client, monkeypatch):
    monkeypatch.delenv("DISCOGS_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("DISCOGS_CONSUMER_SECRET", raising=False)

    resp = client.get("/discogs/login", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Discogs OAuth requires DISCOGS_CONSUMER_KEY and DISCOGS_CONSUMER_SECRET" in html


def test_oauth_login_initiates_oauth(client, monkeypatch):
    monkeypatch.setenv("DISCOGS_CONSUMER_KEY", "env_ckey")
    monkeypatch.setenv("DISCOGS_CONSUMER_SECRET", "env_csecret")

    with patch("discobrain.auth.OAuth1Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.fetch_request_token.return_value = {
            "oauth_token": "req_token_123",
            "oauth_token_secret": "req_secret_456",
        }
        mock_session.authorization_url.return_value = (
            "https://www.discogs.com/oauth/authorize?oauth_token=req_token_123"
        )

        resp = client.get("/discogs/login")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "https://www.discogs.com/oauth/authorize?oauth_token=req_token_123"

        with client.session_transaction() as sess:
            assert sess["discogs_req_token"] == "req_token_123"
            assert sess["discogs_req_token_secret"] == "req_secret_456"


def test_oauth_callback_denied(client):
    with client.session_transaction() as sess:
        sess["discogs_req_token"] = "req_token_123"
        sess["discogs_req_token_secret"] = "req_secret_456"

    resp = client.get("/discogs/auth?denied=req_token_123", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Discogs authorization was cancelled." in html

    with client.session_transaction() as sess:
        assert "discogs_req_token" not in sess
        assert "discogs_req_token_secret" not in sess


def test_oauth_callback_stores_tokens_and_username(client, monkeypatch):
    monkeypatch.setenv("DISCOGS_CONSUMER_KEY", "env_ckey")
    monkeypatch.setenv("DISCOGS_CONSUMER_SECRET", "env_csecret")

    with client.session_transaction() as sess:
        sess["discogs_req_token"] = "req_token_123"
        sess["discogs_req_token_secret"] = "req_secret_456"

    with patch("discobrain.auth.OAuth1Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.fetch_access_token.return_value = {
            "oauth_token": "access_token_abc",
            "oauth_token_secret": "access_secret_xyz",
        }
        mock_identity_resp = MagicMock()
        mock_identity_resp.status_code = 200
        mock_identity_resp.json.return_value = {"username": "oauth_user"}
        mock_session.get.return_value = mock_identity_resp

        resp = client.get("/discogs/auth?oauth_verifier=verifier_789")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/")

        with client.session_transaction() as sess:
            assert sess["discogs_access_token"] == "access_token_abc"
            assert sess["discogs_access_token_secret"] == "access_secret_xyz"
            assert sess["discogs_username"] == "oauth_user"
            assert "discogs_req_token" not in sess


def test_logout_clears_session(client):
    with client.session_transaction() as sess:
        sess["discogs_user_token"] = "token_xyz"
        sess["discogs_username"] = "Alice"

    resp = client.get("/discogs/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")

    with client.session_transaction() as sess:
        assert "discogs_user_token" not in sess
        assert "discogs_username" not in sess
