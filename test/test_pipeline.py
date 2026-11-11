import json
from pathlib import Path
from unittest.mock import MagicMock

from discobrain.batch_store import BatchItemStatus, BatchStore
from discobrain.pipeline import (
    build_converter,
    process_batch,
    reevaluate_pending_items,
)
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

    errors = process_batch(
        batch_id=batch_id,
        batch_store=store,
        lookup=lookup,
        converter=converter,
        base_url="http://localhost:5000",
    )

    item = store.get_item(item_id)
    assert item is None  # Should not persist in the batch
    assert len(errors) == 1
    assert "Discogs 404 Not Found" in errors[0]
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.total_items == 0


def test_reevaluate_pending_items_populates_newly_cached_mbids(tmp_path):
    db_file = tmp_path / "test_pipeline.db"
    store = BatchStore(db_file)
    lookup = MusicBrainzLookUp("TestAgent/1.0", db_file=db_file)
    lookup.get_url_resources = MagicMock(return_value=[])

    batch_id = store.create_batch()
    item_id = store.add_item(batch_id, 765433)

    fixture_data = load_fixture(765433)
    converter = ReleaseConverter(lookup=lookup, auto_env=False)
    converter._discogs_release_endpoint = MagicMock(return_value=fixture_data)

    # Initial batch processing
    process_batch(
        batch_id=batch_id,
        batch_store=store,
        lookup=lookup,
        converter=converter,
        base_url="http://localhost:5000",
    )

    item_before = store.get_item(item_id)
    assert item_before is not None
    assert item_before.payload is not None
    # Noisia's artist mbid was not yet in cache, so it should not be in the payload
    assert "artist_credit.names.0.mbid" not in item_before.payload
    assert item_before.raw_data is not None

    # Now simulate finding or caching Noisia's MusicBrainz ID
    noisia_artist_url = "https://www.discogs.com/artist/100457"
    noisia_mbid = "b8a82cf9-5415-46ee-aa54-ee054174df87"
    lookup.store(noisia_artist_url, noisia_mbid, relationship="artist")

    # Reset endpoint mock to ensure re-evaluation uses raw_data without refetching from Discogs
    converter._discogs_release_endpoint.reset_mock()

    # Run re-evaluation
    updated_items = reevaluate_pending_items(
        batch_id=batch_id,
        batch_store=store,
        lookup=lookup,
        converter=converter,
        base_url="http://localhost:5000",
    )

    assert len(updated_items) == 1
    item_after = store.get_item(item_id)
    assert item_after is not None
    assert item_after.payload is not None
    assert item_after.payload.get("artist_credit.names.0.mbid") == noisia_mbid

    # Verify Discogs network endpoint was not called during re-evaluation (raw_data was used)
    converter._discogs_release_endpoint.assert_not_called()
