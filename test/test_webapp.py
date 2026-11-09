import io
import sqlite3
from unittest.mock import patch

from discobrain import get_batch_store, get_db_path, get_lookup
from discobrain.batch_store import BatchItemStatus, BatchStatus
from discobrain.pipeline import get_musicbrainz_lookup


def test_index_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Batch Import Releases to MusicBrainz" in html
    assert "raw_urls" in html
    assert "file" in html
    assert "Parse &amp; Begin Submissions" in html or "Parse & Begin Submissions" in html


def test_parse_empty_input_redirects_with_error(client):
    resp = client.post("/parse", data={"raw_urls": "   \n# comment\n  "}, follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Please provide at least one valid Discogs release URL or ID." in html


@patch("discobrain.process_batch")
def test_parse_valid_textarea_creates_batch(mock_process, client):
    data = {
        "raw_urls": "https://www.discogs.com/release/13954-DJ-Teebee\n38348\n13954"
    }
    resp = client.post("/parse", data=data)
    assert resp.status_code == 302
    assert "/submissions/" in resp.headers["Location"]

    batch_id = resp.headers["Location"].split("/submissions/")[-1]
    store = get_batch_store()
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.total_items == 2  # 13954 and 38348 (deduplicated)

    items = store.get_items(batch_id)
    assert len(items) == 2
    assert items[0].discogs_id == 13954
    assert items[1].discogs_id == 38348
    mock_process.assert_called_once()


@patch("discobrain.process_batch")
def test_parse_file_upload_creates_batch(mock_process, client):
    file_bytes = b"765433\nhttps://www.discogs.com/release/631758\n"
    data = {
        "raw_urls": "",
        "file": (io.BytesIO(file_bytes), "releases.txt"),
    }
    resp = client.post("/parse", data=data, content_type="multipart/form-data")
    assert resp.status_code == 302
    assert "/submissions/" in resp.headers["Location"]

    batch_id = resp.headers["Location"].split("/submissions/")[-1]
    store = get_batch_store()
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.total_items == 2
    items = store.get_items(batch_id)
    assert [item.discogs_id for item in items] == [765433, 631758]
    mock_process.assert_called_once()


@patch("discobrain.process_batch")
def test_parse_combined_textarea_and_file(mock_process, client):
    file_bytes = b"765433\n13954\n"
    data = {
        "raw_urls": "13954\n38348",
        "file": (io.BytesIO(file_bytes), "releases.txt"),
    }
    resp = client.post("/parse", data=data, content_type="multipart/form-data")
    assert resp.status_code == 302
    batch_id = resp.headers["Location"].split("/submissions/")[-1]

    store = get_batch_store()
    items = store.get_items(batch_id)
    assert [item.discogs_id for item in items] == [13954, 38348, 765433]
    mock_process.assert_called_once()


def test_submissions_view_renders_batch(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    store.add_item(
        batch_id,
        13954,
        title="Through The Eyes Of A Scorpion",
        artist="DJ Teebee",
        format='12" Vinyl',
        year=2001,
        status=BatchItemStatus.PENDING.value,
    )
    store.add_item(
        batch_id,
        765433,
        title="End Game",
        artist="Noisia",
        status=BatchItemStatus.DROPPED.value,
        mbid="ceccb90b-59f8-4856-ab15-c980ed653b1d",
    )

    resp = client.get(f"/submissions/{batch_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert f"Import Batch: {batch_id[:8]}" in html
    assert "Through The Eyes Of A Scorpion" in html
    assert "DJ Teebee" in html
    assert "Already in MusicBrainz" in html
    assert "https://musicbrainz.org/release/ceccb90b-59f8-4856-ab15-c980ed653b1d" in html


def test_submissions_view_not_found(client):
    resp = client.get("/submissions/nonexistent-batch-id", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Batch &#39;nonexistent-batch-id&#39; not found." in html or "Batch 'nonexistent-batch-id' not found." in html


def test_submissions_view_renders_seed_forms(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    store.add_item(
        batch_id,
        13954,
        title="Through The Eyes Of A Scorpion",
        artist="DJ Teebee",
        payload={
            "name": "Through The Eyes Of A Scorpion",
            "artist_credit.names.0.name": "DJ Teebee",
            "events.0.date.year": 2001,
            "redirect_uri": "http://localhost:5000/callback?batch_id=" + batch_id + "&discogs_id=13954",
        },
    )

    resp = client.get(f"/submissions/{batch_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert 'action="https://musicbrainz.org/release/add"' in html
    assert 'name="name" value="Through The Eyes Of A Scorpion"' in html
    assert 'name="artist_credit.names.0.name" value="DJ Teebee"' in html
    assert 'Submit to MusicBrainz ↗' in html
    assert 'Mark as Submitted' in html


def test_mark_submitted_action(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    item_id = store.add_item(batch_id, 13954, title="Through The Eyes Of A Scorpion")

    resp = client.post(
        f"/submissions/{batch_id}/items/{item_id}/mark-submitted",
        data={"mbid": "newly-seeded-mbid-123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Release marked as submitted." in html

    item = store.get_item(item_id)
    assert item is None
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.submitted_count == 1


def test_submissions_next_renders_seed_redirect(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    store.add_item(
        batch_id,
        13954,
        title="Through The Eyes Of A Scorpion",
        payload={"name": "Through The Eyes Of A Scorpion"},
    )

    resp = client.get(f"/submissions/{batch_id}/next")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Opening MusicBrainz Release Editor..." in html
    assert 'id="seed-form"' in html
    assert 'action="https://musicbrainz.org/release/add"' in html
    assert 'name="name" value="Through The Eyes Of A Scorpion"' in html
    assert "Proceed to MusicBrainz Release Editor" in html
    assert "form.submit();" in html


def test_submissions_next_empty_redirects_to_batch(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    # No pending items

    resp = client.get(f"/submissions/{batch_id}/next", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "All releases in this batch have been submitted!" in html


def test_submissions_next_sequential_mode_appends_mode(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    store.add_item(
        batch_id,
        13954,
        title="Through The Eyes Of A Scorpion",
        payload={
            "name": "Through The Eyes Of A Scorpion",
            "redirect_uri": f"http://localhost:5000/callback?batch_id={batch_id}&discogs_id=13954",
        },
    )

    resp = client.get(f"/submissions/{batch_id}/next?mode=sequential")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert f"redirect_uri&quot; value=&quot;http://localhost:5000/callback?batch_id={batch_id}&amp;discogs_id=13954&amp;mode=sequential&quot;" in html or f"redirect_uri\" value=\"http://localhost:5000/callback?batch_id={batch_id}&discogs_id=13954&mode=sequential\"" in html or "mode=sequential" in html


def test_callback_standalone_success(client, app):
    store = get_batch_store()
    batch_id = store.create_batch()
    item_id = store.add_item(batch_id, 13954, title="Through The Eyes Of A Scorpion")

    resp = client.get(
        f"/callback?batch_id={batch_id}&discogs_id=13954&release_mbid=newly-seeded-mbid-789"
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Release Successfully Seeded!" in html
    assert "newly-seeded-mbid-789" in html
    assert "Through The Eyes Of A Scorpion" in html

    # Verify batch item is dropped from database upon completion
    item = store.get_item(item_id)
    assert item is None
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.submitted_count == 1

    # Verify MusicBrainzLookUp SQLite cache
    db_path = app.config.get("DISCOBRAIN_DB")
    lookup = get_musicbrainz_lookup(db_path)
    assert (
        lookup.get_by_url("https://www.discogs.com/release/13954")
        == "newly-seeded-mbid-789"
    )


def test_callback_sequential_mode_advances_to_next(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    item1_id = store.add_item(batch_id, 13954, title="Release 1")
    item2_id = store.add_item(batch_id, 38348, title="Release 2")

    resp = client.get(
        f"/callback?batch_id={batch_id}&discogs_id=13954&release_mbid=mbid-rel-1&mode=sequential"
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(
        f"/submissions/{batch_id}/next?mode=sequential"
    )

    item1 = store.get_item(item1_id)
    assert item1 is None
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.submitted_count == 1

    item2 = store.get_item(item2_id)
    assert item2 is not None
    assert item2.status == BatchItemStatus.PENDING.value


def test_callback_sequential_mode_completes_batch(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    store.add_item(batch_id, 13954, title="Last Release")

    resp = client.get(
        f"/callback?batch_id={batch_id}&discogs_id=13954&release_mbid=mbid-final&mode=sequential",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "All releases in this batch have been successfully submitted!" in html

    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.status == BatchStatus.COMPLETED.value
    assert batch.submitted_count == 1


def test_callback_invalid_or_missing_parameters(client):
    resp = client.get("/callback", follow_redirects=True)
    assert resp.status_code == 200
    assert "Missing batch ID in callback parameter." in resp.data.decode("utf-8")

    resp2 = client.get("/callback?batch_id=nonexistent-id", follow_redirects=True)
    assert resp2.status_code == 200
    assert "Batch &#39;nonexistent-id&#39; not found." in resp2.data.decode(
        "utf-8"
    ) or "Batch 'nonexistent-id' not found." in resp2.data.decode("utf-8")


def test_end_to_end_sequential_submission_flow(client, app):
    store = get_batch_store()
    batch_id = store.create_batch()
    item1_id = store.add_item(
        batch_id,
        13954,
        title="Through The Eyes Of A Scorpion",
        artist="DJ Teebee",
        payload={
            "name": "Through The Eyes Of A Scorpion",
            "redirect_uri": f"http://localhost:5000/callback?batch_id={batch_id}&discogs_id=13954",
        },
    )
    item2_id = store.add_item(
        batch_id,
        765433,
        title="End Game",
        artist="Noisia",
        payload={
            "name": "End Game",
            "redirect_uri": f"http://localhost:5000/callback?batch_id={batch_id}&discogs_id=765433",
        },
    )

    # 1. View submissions dashboard
    resp = client.get(f"/submissions/{batch_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Submit All Sequentially" in html
    assert f"/submissions/{batch_id}/next?mode=sequential" in html

    # 2. Trigger sequential mode
    resp = client.get(f"/submissions/{batch_id}/next?mode=sequential")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Sequential Mode · 2 releases remaining" in html
    assert "Through The Eyes Of A Scorpion" in html
    assert "Proceed to MusicBrainz Release Editor →" in html
    assert "form.submit();" in html
    assert "mode=sequential" in html

    # 3. Simulate MusicBrainz callback for release 1
    resp = client.get(
        f"/callback?batch_id={batch_id}&discogs_id=13954&release_mbid=mbid-first-111&mode=sequential"
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/submissions/{batch_id}/next?mode=sequential")

    item1 = store.get_item(item1_id)
    assert item1 is None
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.submitted_count == 1

    # 4. Step 2 of sequential mode
    resp = client.get(resp.headers["Location"])
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Sequential Mode · 1 release remaining" in html
    assert "End Game" in html

    # 5. Simulate MusicBrainz callback for release 2 (completes batch)
    resp = client.get(
        f"/callback?batch_id={batch_id}&discogs_id=765433&release_mbid=mbid-second-222&mode=sequential",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "All releases in this batch have been successfully submitted!" in html
    assert "Completed" in html

    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.status == BatchStatus.COMPLETED.value
    assert batch.pending_count == 0
    assert batch.submitted_count == 2

    item2 = store.get_item(item2_id)
    assert item2 is None


def test_mark_submitted_completes_batch(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    item_id = store.add_item(batch_id, 13954, title="Single Release")

    client.post(
        f"/submissions/{batch_id}/items/{item_id}/mark-submitted",
        data={"mbid": "manual-mbid-123"},
        follow_redirects=True,
    )
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.status == BatchStatus.COMPLETED.value
    assert batch.pending_count == 0
    assert batch.submitted_count == 1
    assert store.get_item(item_id) is None


def test_resume_banner_on_index_page(client):
    store = get_batch_store()
    batch = store.get_or_create_batch()
    store.add_item(batch.id, 13954, title="Pending Scorpion")

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Batch in Progress:" in html
    assert "Resume Submissions →" in html


def test_clear_batch_action(client):
    store = get_batch_store()
    batch = store.get_or_create_batch()
    store.add_item(batch.id, 13954, title="Release 1")
    store.add_item(batch.id, 38348, title="Release 2")

    resp = client.post("/batch/clear", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Batch queue cleared successfully." in html

    # Items cleared
    items = store.get_items(batch.id)
    assert len(items) == 0


def test_clear_cache_action(client, app):
    db_path = app.config.get("DISCOBRAIN_DB")
    lookup = get_musicbrainz_lookup(db_path)
    lookup.store("https://www.discogs.com/release/9999", "mbid-9999", "release")
    assert lookup.get_cache_count() >= 1

    resp = client.post("/cache/clear", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "MusicBrainz URL/MBID cache cleared successfully." in html
    assert lookup.get_cache_count() == 0


def test_footer_displays_batch_size_and_cache_count(client, app):
    store = get_batch_store()
    batch = store.get_or_create_batch()
    store.add_item(batch.id, 13954, title="Release In Batch")

    db_path = app.config.get("DISCOBRAIN_DB")
    lookup = get_musicbrainz_lookup(db_path)
    lookup.store("https://www.discogs.com/release/123", "mbid-123", "release")

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "in batch" in html
    assert "mbids cached" in html
    assert "Clear Batch" in html
    assert "Clear Cache" in html


def test_db_path_consistency_and_cache_table_creation(app, monkeypatch, tmp_path):
    # Temporarily remove DISCOBRAIN_DB from app.config and env
    app.config.pop("DISCOBRAIN_DB", None)
    monkeypatch.delenv("DISCOBRAIN_DB", raising=False)

    # Point instance_path to a temporary directory for isolation
    monkeypatch.setattr(app, "instance_path", str(tmp_path / "instance"))

    db_path = get_db_path()
    assert db_path.endswith("discobrain.db")
    assert db_path != ":memory:"

    store = get_batch_store()
    lookup = get_lookup()

    # Both store and lookup must point to the same database file
    assert store.db_path == db_path
    assert lookup.db_path == db_path

    # Verify that cache table was created on disk
    conn = sqlite3.connect(db_path)
    tables = [row[0] for row in conn.cursor().execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()

    assert "batches" in tables
    assert "batch_items" in tables
    assert "cache" in tables
