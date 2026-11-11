import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import requests

from discobrain.tagger import (
    build_tag_submission_xml,
    extract_discogs_tags,
    submit_release_tags,
)


def test_extract_discogs_tags_empty():
    assert extract_discogs_tags(None) == []
    assert extract_discogs_tags({}) == []
    assert extract_discogs_tags({"genres": [], "styles": []}) == []


def test_extract_discogs_tags_non_electronic_fallback():
    raw_data = {
        "genres": ["Rock", " Rock "],
        "styles": ["Indie Rock", "rock", "Alternative", "", "   "],
    }
    tags = extract_discogs_tags(raw_data)
    assert tags == ["Rock", "Indie Rock", "Alternative"]


def test_extract_discogs_tags_electronic_mapped():
    raw_data = {
        "genres": ["Electronic"],
        "styles": ["Acid", "Techno"],
    }
    tags = extract_discogs_tags(raw_data)
    assert "acid techno" in tags
    assert "techno" in tags
    assert "electronic" in tags


def test_build_tag_submission_xml():
    release_mbid = "12345678-1234-1234-1234-123456789abc"
    tags = ["Electronic", "Rock & Roll", "<Special>"]
    xml_str = build_tag_submission_xml(release_mbid, tags)

    assert "<?xml version='1.0' encoding='utf-8'?>" in xml_str or '<?xml version="1.0" encoding="utf-8"?>' in xml_str
    assert 'xmlns="http://musicbrainz.org/ns/mmd-2.0#"' in xml_str
    assert f'id="{release_mbid}"' in xml_str
    assert "Rock &amp; Roll" in xml_str
    assert "&lt;Special&gt;" in xml_str

    root = ET.fromstring(xml_str)
    assert root.tag == "{http://musicbrainz.org/ns/mmd-2.0#}metadata"
    release = root.find("{http://musicbrainz.org/ns/mmd-2.0#}release-list/{http://musicbrainz.org/ns/mmd-2.0#}release")
    assert release is not None
    assert release.attrib["id"] == release_mbid
    tag_names = [el.text for el in release.findall(".//{http://musicbrainz.org/ns/mmd-2.0#}name")]
    assert tag_names == ["Electronic", "Rock & Roll", "<Special>"]


def test_submit_release_tags_missing_mbid():
    res = submit_release_tags("", ["Electronic"])
    assert res.status == "skipped"
    assert res.error == "Missing release MBID"


def test_submit_release_tags_empty_tags():
    res = submit_release_tags("mbid_123", [])
    assert res.status == "skipped"
    assert res.tags == []


def test_submit_release_tags_unauthenticated(monkeypatch, app):
    with app.test_request_context("/"):
        monkeypatch.setattr("discobrain.tagger.is_musicbrainz_authenticated", lambda: False)
        res = submit_release_tags("mbid_123", ["Electronic"])
        assert res.status == "skipped"
        assert res.error is not None
        assert "not authenticated" in res.error.lower()


def test_submit_release_tags_success():
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_session.post.return_value = mock_resp

    res = submit_release_tags("mbid_123", ["Electronic", "Jungle"], session=mock_session)
    assert res.status == "submitted"
    assert res.tags == ["Electronic", "Jungle"]
    assert res.error is None

    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    assert "https://musicbrainz.org/ws/2/tag?client=Discobrain-0.0.1" in call_args[0][0]
    assert call_args[1]["headers"]["Content-Type"] == "application/xml; charset=utf-8"
    assert b"<user-tag><name>Electronic</name></user-tag>" in call_args[1]["data"]


def test_submit_release_tags_http_error():
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mock_session.post.return_value = mock_resp

    res = submit_release_tags("mbid_123", ["Electronic"], session=mock_session)
    assert res.status == "failed"
    assert res.error is not None
    assert "401" in res.error


def test_submit_release_tags_request_exception():
    mock_session = MagicMock()
    mock_session.post.side_effect = requests.RequestException("Connection timeout")

    res = submit_release_tags("mbid_123", ["Electronic"], session=mock_session)
    assert res.status == "failed"
    assert res.error is not None
    assert "Connection timeout" in res.error


def test_callback_with_tags_authenticated(client, monkeypatch):
    from discobrain import get_batch_store

    store = get_batch_store()
    batch_id = store.create_batch()
    store.add_item(
        batch_id,
        13954,
        title="Through The Eyes Of A Scorpion",
        raw_data={"genres": ["Electronic"], "styles": ["Drum n Bass"]},
    )

    with client.session_transaction() as sess:
        sess["musicbrainz_oauth_token"] = "valid_mb_token"
        sess["musicbrainz_username"] = "mb_tester"

    with patch("discobrain.submit_release_tags") as mock_submit:
        from discobrain.tagger import TagSubmissionResult
        mock_submit.return_value = TagSubmissionResult(
            status="submitted",
            tags=["drum and bass", "electronic"],
        )

        resp = client.get(
            f"/callback?batch_id={batch_id}&discogs_id=13954&release_mbid=new-seeded-mbid-001"
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Tags Submitted to MusicBrainz:" in html
        assert "drum and bass" in html
        assert "electronic" in html
        mock_submit.assert_called_once_with("new-seeded-mbid-001", ["drum and bass", "electronic"])


def test_callback_with_tags_unauthenticated(client):
    from discobrain import get_batch_store

    store = get_batch_store()
    batch_id = store.create_batch()
    store.add_item(
        batch_id,
        765433,
        title="Test Album",
        raw_data={"genres": ["Rock"], "styles": ["Indie Rock"]},
    )

    resp = client.get(
        f"/callback?batch_id={batch_id}&discogs_id=765433&release_mbid=new-seeded-mbid-002"
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Tags Not Submitted:" in html
    assert "Not connected to MusicBrainz" in html
