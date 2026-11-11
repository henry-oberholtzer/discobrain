import tempfile
from pathlib import Path

from discobrain.batch_store import (
    BatchItemStatus,
    BatchStatus,
    BatchStore,
)


def test_create_and_get_batch():
    store = BatchStore()
    batch_id = store.create_batch()
    assert batch_id is not None

    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.id == batch_id
    assert batch.status == BatchStatus.ACTIVE.value
    assert batch.total_items == 0
    assert batch.pending_count == 0
    assert batch.dropped_count == 0
    assert batch.submitted_count == 0
    assert batch.error_count == 0


def test_get_nonexistent_batch():
    store = BatchStore()
    assert store.get_batch("does-not-exist") is None


def test_add_and_retrieve_items():
    store = BatchStore()
    batch_id = store.create_batch()

    item_id_1 = store.add_item(
        batch_id,
        discogs_id=101,
        title="Release One",
        artist="Artist A",
        format='12" Vinyl',
        year=2001,
        payload={"name": "Release One", "language": "eng"},
    )
    assert item_id_1 > 0

    item_id_2 = store.add_item(
        batch_id,
        discogs_id=102,
        status=BatchItemStatus.DROPPED.value,
        mbid="mbid-existing-123",
        title="Release Two",
        artist="Artist B",
    )
    assert item_id_2 > item_id_1

    # Verify counts
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.total_items == 2
    assert batch.pending_count == 1
    assert batch.dropped_count == 1

    # Retrieve all items
    all_items = store.get_items(batch_id)
    assert len(all_items) == 2
    assert all_items[0].discogs_id == 101
    assert all_items[0].payload == {"name": "Release One", "language": "eng"}
    assert all_items[1].discogs_id == 102
    assert all_items[1].mbid == "mbid-existing-123"

    # Retrieve filtered items
    pending_items = store.get_items(batch_id, status=BatchItemStatus.PENDING.value)
    assert len(pending_items) == 1
    assert pending_items[0].id == item_id_1

    dropped_items = store.get_items(batch_id, status=BatchItemStatus.DROPPED.value)
    assert len(dropped_items) == 1
    assert dropped_items[0].id == item_id_2

    # Retrieve by discogs_id
    item_by_discogs = store.get_item_by_discogs_id(batch_id, 101)
    assert item_by_discogs is not None
    assert item_by_discogs.title == "Release One"


def test_get_next_pending_item():
    store = BatchStore()
    batch_id = store.create_batch()

    # Empty batch returns None
    assert store.get_next_pending_item(batch_id) is None

    store.add_item(batch_id, 101, status=BatchItemStatus.DROPPED.value)
    store.add_item(batch_id, 102, status=BatchItemStatus.PENDING.value)
    store.add_item(batch_id, 103, status=BatchItemStatus.PENDING.value)

    first_pending = store.get_next_pending_item(batch_id)
    assert first_pending is not None
    assert first_pending.discogs_id == 102

    # After marking 102 as submitted, next pending should be 103
    store.update_item_status(first_pending.id, BatchItemStatus.SUBMITTED.value, mbid="new-mbid-456")
    second_pending = store.get_next_pending_item(batch_id)
    assert second_pending is not None
    assert second_pending.discogs_id == 103

    # After marking 103 as submitted, next pending should be None
    store.update_item_status(second_pending.id, BatchItemStatus.SUBMITTED.value)
    assert store.get_next_pending_item(batch_id) is None


def test_update_item_payload():
    store = BatchStore()
    batch_id = store.create_batch()
    item_id = store.add_item(batch_id, 201, payload={"step": 1})

    item = store.get_item(item_id)
    assert item is not None
    assert item.payload == {"step": 1}

    store.update_item_payload(item_id, {"step": 2, "artist_mbid": "xyz"})
    updated = store.get_item(item_id)
    assert updated is not None
    assert updated.payload == {"step": 2, "artist_mbid": "xyz"}


def test_update_batch_status():
    store = BatchStore()
    batch_id = store.create_batch()
    store.update_batch_status(batch_id, BatchStatus.COMPLETED.value)
    batch = store.get_batch(batch_id)
    assert batch is not None
    assert batch.status == BatchStatus.COMPLETED.value


def test_add_and_update_raw_data():
    store = BatchStore()
    batch_id = store.create_batch()
    item_id = store.add_item(
        batch_id,
        discogs_id=301,
        title="Initial",
        raw_data={"id": 301, "title": "Raw Title"},
    )
    item = store.get_item(item_id)
    assert item is not None
    assert item.raw_data == {"id": 301, "title": "Raw Title"}

    store.update_item_details(
        item_id,
        title="Updated Title",
        raw_data={"id": 301, "title": "Updated Raw Title", "formats": []},
    )
    updated = store.get_item(item_id)
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.raw_data == {"id": 301, "title": "Updated Raw Title", "formats": []}


def test_get_or_create_batch():
    store = BatchStore()
    b1 = store.get_or_create_batch()
    assert b1.id == "default"
    assert b1.submitted_count == 0

    # Calling again returns same batch
    b2 = store.get_or_create_batch()
    assert b2.id == "default"


def test_complete_item_drops_from_db_and_increments_counter():
    store = BatchStore()
    b = store.get_or_create_batch()
    item_id = store.add_item(b.id, 101, title="Test Release")

    # Before completion: 1 total item, 0 submitted count
    batch_before = store.get_batch(b.id)
    assert batch_before is not None
    assert batch_before.total_items == 1
    assert batch_before.submitted_count == 0

    # Complete the item
    store.complete_item(item_id)

    # Item should no longer exist in batch_items
    assert store.get_item(item_id) is None
    assert store.get_items(b.id) == []

    # Batch submitted_count should now be 1, total remaining 0
    batch_after = store.get_batch(b.id)
    assert batch_after is not None
    assert batch_after.total_items == 0
    assert batch_after.pending_count == 0
    assert batch_after.submitted_count == 1


def test_delete_item_removes_from_db_without_incrementing_submitted():
    store = BatchStore()
    b = store.get_or_create_batch()
    item_id = store.add_item(b.id, 101, title="Errored Release")

    batch_before = store.get_batch(b.id)
    assert batch_before is not None
    assert batch_before.total_items == 1
    assert batch_before.submitted_count == 0

    # Delete item
    store.delete_item(item_id)

    # Item should no longer exist in batch_items
    assert store.get_item(item_id) is None
    assert store.get_items(b.id) == []

    # Submitted count must NOT be incremented
    batch_after = store.get_batch(b.id)
    assert batch_after is not None
    assert batch_after.total_items == 0
    assert batch_after.submitted_count == 0


def test_clear_batch_removes_items_and_preserves_submitted_count():
    store = BatchStore()
    b = store.get_or_create_batch()
    item1 = store.add_item(b.id, 101, title="Release 1")
    store.add_item(b.id, 102, title="Release 2")

    # Complete item1
    store.complete_item(item1)
    batch_mid = store.get_batch(b.id)
    assert batch_mid is not None
    assert batch_mid.submitted_count == 1
    assert batch_mid.total_items == 1  # item 2 remains

    # Clear batch
    store.clear_batch(b.id)

    # All items cleared, but submitted_count preserved
    batch_cleared = store.get_batch(b.id)
    assert batch_cleared is not None
    assert batch_cleared.total_items == 0
    assert batch_cleared.submitted_count == 1
    assert store.get_items(b.id) == []


def test_file_backed_persistence():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_file = Path(temp_dir) / "test_batches.db"
        store1 = BatchStore(db_file)
        batch_id = store1.create_batch()
        store1.add_item(batch_id, 999, title="Persisted Release")
        store1.close()

        # Reopen with new instance
        store2 = BatchStore(db_file)
        batch = store2.get_batch(batch_id)
        assert batch is not None
        assert batch.total_items == 1
        items = store2.get_items(batch_id)
        assert len(items) == 1
        assert items[0].title == "Persisted Release"
        store2.close()


def test_complete_item_stores_all_release_metadata():
    store = BatchStore()
    b = store.get_or_create_batch()
    item_id = store.add_item(
        b.id,
        12345,
        title="Selected Ambient Works 85-92",
        artist="Aphex Twin",
        format="Vinyl",
        year=1992,
    )

    store.complete_item(item_id, mbid="11111111-2222-3333-4444-555555555555")

    # Item dropped from queue
    assert store.get_item(item_id) is None

    # Stored in submitted_releases
    submitted = store.get_submitted_releases(b.id)
    assert len(submitted) == 1
    record = submitted[0]
    assert record.discogs_id == 12345
    assert record.title == "Selected Ambient Works 85-92"
    assert record.artist == "Aphex Twin"
    assert record.format == "Vinyl"
    assert record.year == 1992
    assert record.mbid == "11111111-2222-3333-4444-555555555555"
    assert record.submitted_at != ""

    assert store.get_total_submitted_count() == 1


def test_record_submitted_release_direct():
    store = BatchStore()
    batch_id = store.create_batch("batch_custom")
    rec_id = store.record_submitted_release(
        batch_id,
        99999,
        mbid="mbid-custom-123",
        artist="Underworld",
        title="Dubnobasswithmyheadman",
        year=1994,
        format="CD",
    )
    assert rec_id > 0

    submitted = store.get_submitted_releases()
    assert len(submitted) == 1
    assert submitted[0].discogs_id == 99999
    assert submitted[0].artist == "Underworld"
    assert submitted[0].title == "Dubnobasswithmyheadman"
    assert submitted[0].year == 1994
    assert submitted[0].format == "CD"
    assert submitted[0].mbid == "mbid-custom-123"
