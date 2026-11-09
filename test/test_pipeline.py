import json
from pathlib import Path
from unittest.mock import MagicMock

from discobrain.batch_store import BatchItemStatus, BatchStore
from discobrain.pipeline import build_converter, process_batch
from discobrain.release_converter.converter import ReleaseConverter
from discobrain.release_converter.discogs import DiscogsRelease
from discobrain.release_converter.musicbrainz import MusicBrainzLookUp

FIXTURES_DIR = Path(__file__).parent / "discogs"


def load_fixture(release_id: int) -> DiscogsRelease:
    with open(FIXTURES_DIR / f"{release_id}.json", encoding="utf-8") as f:
        return json.load(f)


def test_build_converter_with_session():
    session_data = {
        "discogs_access_token": "sess_token",
        "discogs_access_token_secret": "sess_secret",
    }
    converter = build_converter(session_data=session_data)
    assert converter.oauth_token == "sess_token"
    assert converter.oauth_token_secret == "sess_secret"


def test_process_batch_drops_existing_releases(tmp_path):
    db_file = tmp_path / "test_pipeline.db"
    store = BatchStore(db_file)
    lookup = MusicBrainzLookUp("TestAgent/1.0", db_file=db_file)

    # Seed the cache with a known MBID
    lookup.store(
        "https://www.discogs.com/release/13954",
        "existing-mbid-13954",
        "release",
    )

    batch_id = store.create_batch()
    item_id = store.add_item(batch_id, 13954)

    mock_converter = MagicMock(spec=ReleaseConverter)

    # Mock get_url_resources so it doesn't make live HTTP calls
    lookup.get_url_resources = MagicMock(return_value=[])

    process_batch(
        batch_id=batch_id,
        batch_store=store,
        lookup=lookup,
        converter=mock_converter,
        base_url="http://localhost:5000",
    )

    item = store.get_item(item_id)
    assert item is not None
    assert item.status == BatchItemStatus.DROPPED.value
    assert item.mbid == "existing-mbid-13954"

    # Converter should never have been called since it was dropped
    mock_converter.discogs.assert_not_called()


def test_process_batch_converts_unseeded_release(tmp_path):
    db_file = tmp_path / "test_pipeline.db"
    store = BatchStore(db_file)
    lookup = MusicBrainzLookUp("TestAgent/1.0", db_file=db_file)
    lookup.get_url_resources = MagicMock(return_value=[])

    batch_id = store.create_batch()
    item_id = store.add_item(batch_id, 765433)

    # Use real converter with mocked Discogs endpoint returning local fixture
    converter = ReleaseConverter(lookup=lookup, auto_env=False)
    converter._discogs_release_endpoint = MagicMock(return_value=load_fixture(765433))

    process_batch(
        batch_id=batch_id,
        batch_store=store,
        lookup=lookup,
        converter=converter,
        base_url="http://localhost:5000",
    )

    item = store.get_item(item_id)
    assert item is not None
    assert item.status == BatchItemStatus.PENDING.value
    assert item.title == "End Game / Unveil"
    assert "Noisia" in (item.artist or "")
    assert item.format == '12" Vinyl'
    assert item.year == 2006
    assert item.payload is not None
    assert item.payload["name"] == "End Game / Unveil"
    assert "redirect_uri" in item.payload
    assert f"batch_id={batch_id}" in item.payload["redirect_uri"]
    assert "language" in item.payload


def test_process_batch_handles_conversion_errors(tmp_path):
    db_file = tmp_path / "test_pipeline.db"
    store = BatchStore(db_file)
    lookup = MusicBrainzLookUp("TestAgent/1.0", db_file=db_file)
    lookup.get_url_resources = MagicMock(return_value=[])

    batch_id = store.create_batch()
    item_id = store.add_item(batch_id, 999999)

    converter = ReleaseConverter(lookup=lookup, auto_env=False)
    converter._discogs_release_endpoint = MagicMock(side_effect=RuntimeError("Discogs 404 Not Found"))

    process_batch(
        batch_id=batch_id,
        batch_store=store,
        lookup=lookup,
        converter=converter,
        base_url="http://localhost:5000",
    )

    item = store.get_item(item_id)
    assert item is not None
    assert item.status == BatchItemStatus.ERROR.value
    assert "Discogs 404 Not Found" in (item.error_message or "")
