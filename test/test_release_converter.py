import json
from pathlib import Path
from typing import cast

import pytest
from pytest import MonkeyPatch

from discobrain.discogs_release import DiscogsRelease
from discobrain.mb_release import MBReleaseType
from discobrain.release_converter import ReleaseConverter, type_from_title

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

