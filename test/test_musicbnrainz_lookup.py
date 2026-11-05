import os
import sqlite3
import tempfile
from collections.abc import Generator

import pytest
from requests_ratelimiter import LimiterSession

from release_converter.musicbrainz import MUSICBRAINZ_API_ROOT, MusicBrainzLookUp

TEST_AGENT = "USER AGENT"

@pytest.fixture
def tempdb() -> Generator[str, None, None]:
    _, file = tempfile.mkstemp(suffix=".db")
    yield file
    os.remove(file)

def test_non_required():
    mb = MusicBrainzLookUp(
        user_agent=TEST_AGENT,
            )
    assert mb.user_agent == TEST_AGENT
    assert mb.api_root == MUSICBRAINZ_API_ROOT
    assert mb.db_path == ":memory:"

def test_init(tempdb):
    api = "https://api.personal.org"
    mb = MusicBrainzLookUp(
        user_agent=TEST_AGENT,
        db_file=tempdb,
        api_root=api
            )
    assert mb.user_agent == TEST_AGENT
    assert mb.db_path == tempdb
    assert mb.db_path.endswith(".db")
    assert mb.api_root == api

def test_db():
    mb = MusicBrainzLookUp(TEST_AGENT)
    assert isinstance(mb.db, sqlite3.Connection)

def test_session():
    mb = MusicBrainzLookUp(TEST_AGENT)
    assert isinstance(mb.session, LimiterSession)
    assert mb.session.headers["User-Agent"] == TEST_AGENT
