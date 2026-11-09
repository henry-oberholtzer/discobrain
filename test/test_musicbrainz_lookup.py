import datetime
import os
import sqlite3
import tempfile
from collections.abc import Generator

import pytest
from pytest import MonkeyPatch
from requests_ratelimiter import LimiterSession

from release_converter.musicbrainz import MUSICBRAINZ_API_ROOT, MusicBrainzLookUp

TEST_AGENT = "DiscobrainTest/0.0.1 ( henryoberholtzer@gmail.com )"

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

def test__init_tables():
    mb = MusicBrainzLookUp(TEST_AGENT, init_tables=False)
    cursor = mb.db.cursor()
    # Get all tables
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    assert tables.fetchone() is None
    mb.init_tables()
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    assert len(tables.fetchall()) == 1
    cursor.close()

def test_insert():
    mb = MusicBrainzLookUp(TEST_AGENT)
    url = "https://discogs.com/123"
    mbid = "abcd"
    artist = "artist"
    mb.store(url, mbid, artist)
    cursor = mb.db.cursor()
    rows = cursor.execute("SELECT * FROM cache").fetchall()
    cursor.close()
    assert len(rows) == 1
    assert rows[0][0] == url
    assert rows[0][1] == mbid
    assert rows[0][2] == artist
    assert rows[0][3].endswith('Z')
    assert datetime.datetime.fromisoformat(rows[0][3]).timestamp() == pytest.approx(datetime.datetime.now(datetime.UTC).timestamp())

@pytest.mark.parametrize("url,table,expected", [
    ("https://discogs.com/release/1234", "release", None),
    ("https://discogs.com/release/123", "release", "abcd")
])
def test_get_mbid(url, table, expected):
    mb = MusicBrainzLookUp(TEST_AGENT)
    mb.store("https://discogs.com/release/123", "abcd", "release")
    """
    Test that an existing entry is returned, and a non existing one returns None
    """
    result = mb.get_mbid(url, table)
    assert result == expected

def test_get_url_resources_single(monkeypatch: MonkeyPatch):
    timestamp = "2026-11-07T05:40:52.744880Z"
    monkeypatch.setattr(MusicBrainzLookUp, "zulu_timestamp", timestamp)
    mb = MusicBrainzLookUp(TEST_AGENT)
    response = mb.get_url_resources(["https://www.discogs.com/release/13954"])
    assert response == [("https://www.discogs.com/release/13954", "ceccb90b-59f8-4856-ab15-c980ed653b1d", "release", timestamp)]

def test_get_url_resources_multiple(monkeypatch: MonkeyPatch):
    timestamp = "2026-11-07T05:40:52.744880Z"
    monkeypatch.setattr(MusicBrainzLookUp, "zulu_timestamp", timestamp)
    mb = MusicBrainzLookUp(TEST_AGENT)
    response = mb.get_url_resources(["https://www.discogs.com/release/13954", "https://www.discogs.com/label/1"])
    assert response == [
            ("https://www.discogs.com/release/13954", "ceccb90b-59f8-4856-ab15-c980ed653b1d", "release", timestamp),
            ("https://www.discogs.com/label/1", "a0fb31fd-1faa-42fd-9bbe-7da22b83a42e", "label", timestamp),
    ]

