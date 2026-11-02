import json
from pathlib import Path
from typing import cast

import pytest
from pytest import MonkeyPatch

from discobrain.discogs_release import DiscogsFormat, DiscogsRelease
from discobrain.mb_release import MBReleaseType
from discobrain.release_converter import (
    ReleaseConverter,
    release_disambiguation,
    type_from_title,
    type_from_tracks,
)

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
    ("The Big Bang LP", MBReleaseType.ALBUM),
    ("A Problem Joe Nicely (E.P.)", MBReleaseType.EP),
    ("Acid Techno in the Modern Era E.P. Vol 1", MBReleaseType.EP)
    ])
def test_from_title(given: str, expected: str):
    assert type_from_title(given) == expected

@pytest.mark.parametrize("tracks,expected", [
    (1, MBReleaseType.SINGLE),
    (2, MBReleaseType.SINGLE),
    (3, MBReleaseType.SINGLE),
    (4, MBReleaseType.EP),
    (5, MBReleaseType.EP),
    (6, MBReleaseType.EP),
    (7, MBReleaseType.ALBUM),
    (8, MBReleaseType.ALBUM)
    ])
def test_from_tracks(tracks: int, expected: str):
    assert type_from_tracks(tracks) == expected

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

