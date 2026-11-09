from flask import flash, render_template_string


def test_user_loader_unauthenticated(client):
    with client:
        client.get("/")
        from flask import g
        assert g.user["authenticated"] is False
        assert g.user["rate_limit"] == 25
        assert g.user["username"] is None


def test_user_loader_authenticated_session(client):
    with client.session_transaction() as sess:
        sess["discogs_access_token"] = "mock_token"
        sess["discogs_username"] = "Alice"

    with client:
        client.get("/")
        from flask import g
        assert g.user["authenticated"] is True
        assert g.user["rate_limit"] == 60
        assert g.user["username"] == "Alice"


def test_user_loader_authenticated_session_user_token(client):
    with client.session_transaction() as sess:
        sess["discogs_user_token"] = "mock_user_token_abc"
        sess["discogs_username"] = "Bob"

    with client:
        client.get("/")
        from flask import g
        assert g.user["authenticated"] is True
        assert g.user["rate_limit"] == 60
        assert g.user["username"] == "Bob"


def test_user_loader_authenticated_env(client, monkeypatch):
    monkeypatch.setenv("DISCOGS_USER_TOKEN", "mock_user_token")
    with client:
        client.get("/")
        from flask import g
        assert g.user["authenticated"] is True
        assert g.user["rate_limit"] == 60


def test_logout_clears_session(client):
    with client.session_transaction() as sess:
        sess["discogs_access_token"] = "mock_token"
        sess["discogs_username"] = "Alice"

    resp = client.get("/discogs/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")

    with client.session_transaction() as sess:
        assert "discogs_access_token" not in sess
        assert "discogs_username" not in sess


def test_base_template_rendering(app):
    with app.test_request_context("/"):
        flash("Welcome to Discobrain!", "success")
        html = render_template_string(
            """
            {% extends "base.html" %}
            {% block title %}Test Title{% endblock %}
            {% block content %}
            <p>Main content rendered</p>
            {% endblock %}
            """
        )
        assert "Test Title - Discobrain" in html
        assert "Discobrain" in html
        assert "Discogs: Not Connected" in html
        assert "Welcome to Discobrain!" in html
        assert "alert-success" in html
        assert "Main content rendered" in html
