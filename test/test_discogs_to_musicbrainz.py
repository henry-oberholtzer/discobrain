import json
from pathlib import Path
from typing import cast

import pytest
from pytest import MonkeyPatch

from release_converter import (
    ReleaseConverter,
)
from release_converter.converter import release_disambiguation
from release_converter.discogs import DiscogsFormat, DiscogsRelease
from release_converter.musicbrainz import MBReleaseType

FILE_PATH = Path(__file__).absolute()

def load_json(_, id: int):
    with FILE_PATH.parent.joinpath(f"discogs/{id}.json").open() as f:
        object = json.load(f)
        return cast(DiscogsRelease, object)

@pytest.mark.parametrize("given,expected", [
    ("https://www.discogs.com/release/13954-DJ-Teebee-Through-The-Eyes-Of-A-Scorpion", 13954),
    ("https://www.discogs.com/release/13954", 13954),
    ("discogs.com/release/13954", 13954),
    ("13954", 13954),
    ])
def test_discogs_id_extract(given: str, expected: int):
    assert ReleaseConverter()._discogs_id_extract(given) == expected

def test_discogs_e2e():
    release = ReleaseConverter()._discogs_release_endpoint(13954)
    assert release is not None
    assert release['title'] == "Through The Eyes Of A Scorpion"

@pytest.mark.parametrize("given,expected", [
    (
        [{
            "name": "Vinyl",
            "quantity": "1",
            "descriptions": [ '12"', "33 1/3 RPM", "45 RPM", "EP", "Limited Edition", "Repress"],
            "text": "Orange"
            }],
        "orange, repress"
        )
    ])
def test_release_disambiguation(given: list[DiscogsFormat], expected: str):
    assert release_disambiguation(given) == expected

def test_discogs(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(ReleaseConverter, "_discogs_release_endpoint", load_json)
    release = ReleaseConverter().discogs(13954)
    assert release.name == "Through the Eyes of a Scorpion"
    assert release.urls
    assert len(release.urls) == 1
    assert release.urls[0].url == "https://www.discogs.com/release/13954"
    assert release.urls[0].link_type == 76
    assert release.barcode == "5033826056260"
    assert release.type == MBReleaseType.ALBUM
    assert release.comment == ""
    assert release.language == "eng"
    assert release.script == "Latn"
    # release.annotation
    # release.status
    # release.packaging
    # release.edit_note
    # release.redirect_uri
    # release.events
    # release.labels
    # release.artist_credit
    # release.mediums

