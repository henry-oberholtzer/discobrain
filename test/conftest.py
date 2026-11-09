import pytest
from flask import Flask
from flask.testing import FlaskClient

from discobrain import app as discobrain_app


@pytest.fixture
def app() -> Flask:
    discobrain_app.config["TESTING"] = True
    discobrain_app.config["SECRET_KEY"] = "test-secret-key"
    discobrain_app.secret_key = "test-secret-key"
    return discobrain_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
