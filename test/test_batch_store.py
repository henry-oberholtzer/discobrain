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
