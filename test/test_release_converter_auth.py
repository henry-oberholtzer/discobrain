from unittest.mock import MagicMock, patch

import pytest
import requests
from requests_oauthlib import OAuth1

from discobrain.release_converter import ReleaseConverter
from discobrain.release_converter.constants import USER_AGENT


def test_unauthenticated_fallback():
    converter = ReleaseConverter(auto_env=False)
    assert not converter.is_authenticated
    assert converter.auth_type is None
    assert "Authorization" not in converter.session.headers
    assert converter.session.auth is None
    assert converter.session.headers["User-Agent"] == USER_AGENT


def test_user_token_auth():
    converter = ReleaseConverter(user_token="tok_12345", auto_env=False)
    assert converter.is_authenticated
    assert converter.auth_type == "user_token"
    assert converter.session.headers["Authorization"] == "Discogs token=tok_12345"
    assert converter.session.headers["User-Agent"] == USER_AGENT


def test_api_key_alias_auth():
    converter = ReleaseConverter(api_key="api_key_abc", auto_env=False)
    assert converter.is_authenticated
    assert converter.auth_type == "user_token"
    assert converter.session.headers["Authorization"] == "Discogs token=api_key_abc"


def test_consumer_key_secret_auth():
    converter = ReleaseConverter(
        consumer_key="my_key",
        consumer_secret="my_secret",
        auto_env=False,
    )
    assert converter.is_authenticated
    assert converter.auth_type == "key_secret"
    assert converter.session.headers["Authorization"] == "Discogs key=my_key, secret=my_secret"


def test_oauth1_auth():
    converter = ReleaseConverter(
        consumer_key="c_key",
        consumer_secret="c_secret",
        oauth_token="o_token",
        oauth_token_secret="o_secret",
        auto_env=False,
    )
    assert converter.is_authenticated
    assert converter.auth_type == "oauth"
    assert isinstance(converter.session.auth, OAuth1)
    assert converter.session.auth.client.client_key == "c_key"
    assert converter.session.auth.client.resource_owner_key == "o_token"


def test_auto_env_user_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DISCOGS_USER_TOKEN", "env_user_token_999")
    monkeypatch.delenv("DISCOGS_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("DISCOGS_CONSUMER_SECRET", raising=False)
    converter = ReleaseConverter(auto_env=True)
    assert converter.is_authenticated
    assert converter.auth_type == "user_token"
    assert converter.session.headers["Authorization"] == "Discogs token=env_user_token_999"


def test_auto_env_oauth(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DISCOGS_USER_TOKEN", raising=False)
    monkeypatch.delenv("DISCOGS_API_KEY", raising=False)
    monkeypatch.setenv("DISCOGS_CONSUMER_KEY", "env_ckey")
    monkeypatch.setenv("DISCOGS_CONSUMER_SECRET", "env_csecret")
    monkeypatch.setenv("DISCOGS_OAUTH_TOKEN", "env_otoken")
    monkeypatch.setenv("DISCOGS_OAUTH_TOKEN_SECRET", "env_osecret")
    converter = ReleaseConverter(auto_env=True)
    assert converter.is_authenticated
    assert converter.auth_type == "oauth"
    assert isinstance(converter.session.auth, OAuth1)
    assert converter.session.auth.client.client_key == "env_ckey"
    assert converter.session.auth.client.resource_owner_key == "env_otoken"


def test_custom_session():
    custom = requests.Session()
    custom.headers["Custom-Header"] = "hello"
    converter = ReleaseConverter(
        user_token="tok_xyz",
        session=custom,
        auto_env=False,
    )
    assert converter.session is custom
    assert converter.session.headers["Custom-Header"] == "hello"
    assert converter.session.headers["Authorization"] == "Discogs token=tok_xyz"
    assert converter.session.headers["User-Agent"] == USER_AGENT


def test_discogs_release_endpoint_uses_session():
    converter = ReleaseConverter(user_token="test_tok", auto_env=False)
    fake_release = {"id": 1234, "title": "Test Release", "artists": [], "formats": [], "tracklist": [], "identifiers": [], "labels": []}
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_release
    mock_resp.raise_for_status.return_value = None

    with patch.object(converter.session, "get", return_value=mock_resp) as mock_get:
        release = converter._discogs_release_endpoint(1234)
        mock_get.assert_called_once_with("https://api.discogs.com/releases/1234")
        assert release["title"] == "Test Release"
