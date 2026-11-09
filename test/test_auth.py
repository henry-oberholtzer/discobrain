from unittest.mock import MagicMock, patch

from discobrain import app


def test_auth_login_initiates_oauth():
    app.config["TESTING"] = True
    client = app.test_client()

    with patch("discobrain.auth.OAuth1Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.fetch_request_token.return_value = {
            "oauth_token": "req_token_123",
            "oauth_token_secret": "req_secret_456",
        }
        mock_session.authorization_url.return_value = "https://discogs.com/oauth/authorize?oauth_token=req_token_123"

        resp = client.get("/discogs/")
        assert resp.status_code == 200
        assert b"https://discogs.com/oauth/authorize?oauth_token=req_token_123" in resp.data


def test_auth_callback_stores_tokens():
    app.config["TESTING"] = True
    client = app.test_client()

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

        resp = client.get("/discogs/auth?oauth_verifier=verifier_789")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/discogs/")

        with client.session_transaction() as sess:
            assert sess["discogs_access_token"] == "access_token_abc"
            assert sess["discogs_access_token_secret"] == "access_secret_xyz"
