import datetime
import os
import sqlite3
import tempfile
from collections.abc import Generator

import pytest
from pytest import MonkeyPatch
from requests_ratelimiter import LimiterSession

from discobrain.release_converter.musicbrainz import (
    MUSICBRAINZ_API_ROOT,
    MusicBrainzLookUp,
)

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
    monkeypatch.setattr(
        mb,
        "get",
        lambda endpoint, params: {
            "resource": "https://www.discogs.com/release/13954",
            "relations": [
                {"target-type": "release", "release": {"id": "ceccb90b-59f8-4856-ab15-c980ed653b1d"}}
            ],
        },
    )
    response = mb.get_url_resources(["https://www.discogs.com/release/13954"])
    assert response == [("https://www.discogs.com/release/13954", "ceccb90b-59f8-4856-ab15-c980ed653b1d", "release", timestamp)]

def test_get_url_resources_multiple(monkeypatch: MonkeyPatch):
    timestamp = "2026-11-07T05:40:52.744880Z"
    monkeypatch.setattr(MusicBrainzLookUp, "zulu_timestamp", timestamp)
    mb = MusicBrainzLookUp(TEST_AGENT)
    monkeypatch.setattr(
        mb,
        "get",
        lambda endpoint, params: {
            "urls": [
                {
                    "resource": "https://www.discogs.com/release/13954",
                    "relations": [
                        {"target-type": "release", "release": {"id": "ceccb90b-59f8-4856-ab15-c980ed653b1d"}}
                    ],
                },
                {
                    "resource": "https://www.discogs.com/label/1",
                    "relations": [
                        {"target-type": "label", "label": {"id": "a0fb31fd-1faa-42fd-9bbe-7da22b83a42e"}}
                    ],
                },
            ]
        },
    )
    response = mb.get_url_resources(["https://www.discogs.com/release/13954", "https://www.discogs.com/label/1"])
    assert response == [
            ("https://www.discogs.com/release/13954", "ceccb90b-59f8-4856-ab15-c980ed653b1d", "release", timestamp),
            ("https://www.discogs.com/label/1", "a0fb31fd-1faa-42fd-9bbe-7da22b83a42e", "label", timestamp),
    ]


def test_clear_cache_and_get_cache_count():
    mb = MusicBrainzLookUp(TEST_AGENT)
    assert mb.get_cache_count() == 0

    mb.store("https://discogs.com/release/1", "mbid-1", "release")
    mb.store("https://discogs.com/label/1", "mbid-2", "label")
    assert mb.get_cache_count() == 2

    mb.clear_cache()
    assert mb.get_cache_count() == 0
    assert mb.get_by_url("https://discogs.com/release/1") is None


def test_clear_queue():
    mb = MusicBrainzLookUp(TEST_AGENT)
    mb.queue = ["https://www.discogs.com/artist/123", "https://www.discogs.com/label/456"]

    def mock_get_url_resources(resources: list[str]):
        return []

    mb.get_url_resources = mock_get_url_resources
    mb.clear_queue()
    assert mb.queue == []


def test_get_mbids_replaces_known_and_clears_unknown():
    from discobrain.release_converter.musicbrainz import (
        MBArtistCredit,
        MBArtistName,
        MBLabel,
        MBMedium,
        MBName,
        MBRelease,
        MBTrack,
    )

    mb = MusicBrainzLookUp(TEST_AGENT)
    # Store a known artist
    mb.store("https://www.discogs.com/artist/100", "11111111-1111-1111-1111-111111111111", "artist")

    release = MBRelease(
        name="Test Album",
        release_group="https://www.discogs.com/master/999",  # unknown master
        artist_credit=MBArtistCredit(
            names=[
                MBName(name="Known", mbid="https://www.discogs.com/artist/100", artist=MBArtistName(name="Known")),
                MBName(name="Unknown", mbid="https://www.discogs.com/artist/200", artist=MBArtistName(name="Unknown")),
            ]
        ),
        labels=[
            MBLabel(name="Unknown Label", mbid="https://www.discogs.com/label/300"),
        ],
        mediums=[
            MBMedium(
                track=[
                    MBTrack(
                        name="Track 1",
                        artist_credit=MBArtistCredit(
                            names=[
                                MBName(name="Unknown Track Artist", mbid="https://www.discogs.com/artist/400")
                            ]
                        ),
                    )
                ]
            )
        ],
    )

    # First pass: enqueue=True should enqueue unknown URLs
    mb.get_mbids(release, enqueue=True)
    assert "https://www.discogs.com/artist/100" not in mb.queue  # known, not enqueued
    assert "https://www.discogs.com/master/999" in mb.queue
    assert "https://www.discogs.com/artist/200" in mb.queue
    assert "https://www.discogs.com/label/300" in mb.queue
    assert "https://www.discogs.com/artist/400" in mb.queue

    # Known artist is immediately replaced
    assert release.artist_credit is not None
    assert release.artist_credit.names[0].mbid == "11111111-1111-1111-1111-111111111111"

    # Second pass: enqueue=False should set unknown URLs to None
    mb.get_mbids(release, enqueue=False)
    assert release.release_group is None
    assert release.artist_credit is not None
    assert release.labels is not None
    assert release.mediums is not None
    assert release.mediums[0].track[0].artist_credit is not None
    assert release.artist_credit.names[0].mbid == "11111111-1111-1111-1111-111111111111"
    assert release.artist_credit.names[1].mbid is None
    assert release.labels[0].mbid is None
    assert release.mediums[0].track[0].artist_credit.names[0].mbid is None

    # Verify flattened release has no Discogs URLs in mbid fields
    flat = release.flatten()
    for key, val in flat.items():
        if "mbid" in key:
            assert not str(val).startswith("https://www.discogs.com")
            assert not str(val).startswith("https://discogs.com")


