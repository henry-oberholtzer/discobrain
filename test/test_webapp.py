import io

from discobrain import get_batch_store


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


def test_parse_valid_textarea_creates_batch(client):
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


def test_parse_file_upload_creates_batch(client):
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


def test_parse_combined_textarea_and_file(client):
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


def test_submissions_view_renders_batch(client):
    store = get_batch_store()
    batch_id = store.create_batch()
    store.add_item(batch_id, 13954, title="Through The Eyes Of A Scorpion", artist="DJ Teebee")
    store.add_item(batch_id, 765433, title="End Game", artist="Noisia")

    resp = client.get(f"/submissions/{batch_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert f"Import Batch: {batch_id[:8]}" in html
    assert "Through The Eyes Of A Scorpion" in html
    assert "Noisia" in html
    assert "Discogs Release #13954" in html
    assert "Discogs Release #765433" in html


def test_submissions_view_not_found(client):
    resp = client.get("/submissions/nonexistent-batch-id", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Batch &#39;nonexistent-batch-id&#39; not found." in html or "Batch 'nonexistent-batch-id' not found." in html
