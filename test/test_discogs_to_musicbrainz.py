from release_converter.musicbrainz import MBArtistName
from release_converter.musicbrainz import MBName
from release_converter.musicbrainz import MBArtistCredit
from release_converter.musicbrainz import MBMedium
from release_converter.discogs import DiscogsTrack
from release_converter.musicbrainz import MBDate
from release_converter.musicbrainz import MBEvent, MBTrack
import json
from pathlib import Path
from typing import cast

import pytest
from pytest import MonkeyPatch

from release_converter import (
    ReleaseConverter,
)
from release_converter.converter import release_disambiguation, discogs_tracklist
from release_converter.discogs import DiscogsFormat, DiscogsRelease
from release_converter.musicbrainz import MBReleaseType

FILE_PATH = Path(__file__).absolute()

def load_json(id: int):
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

@pytest.mark.parametrize("given,expected", [
    (
        load_json(765433),
        [MBMedium(
            format='12" Vinyl',
            name=None,
            track=[
            MBTrack(
                name="End Game",
                number="A",
                length=(6*60+25)*1000,
                artist_credit=MBArtistCredit(
                    names=[
                        MBName(
                            name="Noisia",
                            mbid="ec22a32b-acab-432e-a88c-ffe6ae68fa16",
                            artist=MBArtistName(name="Noisia"),
                        )
                    ]
                )
            ),
            MBTrack(
                name="Unveil",
                number="AA",
                length=(6*60+4)*1000,
                artist_credit=MBArtistCredit(
                    names=[
                        MBName(
                            name="Noisia",
                            mbid="ec22a32b-acab-432e-a88c-ffe6ae68fa16",
                            artist=MBArtistName(name="Noisia"),
                            join_phrase=" Feat. "
                        ),
                        MBName(
                            name="Phace",
                            mbid="f43f6c18-2ac0-45c9-ad2e-cacc06f25187",
                            artist=MBArtistName(name="Phace")
                        )
                    ]
                )
            )
        ])]
    )
])
def test_discogs_tracklist(given: DiscogsRelease, expected: list[MBMedium]):
    assert discogs_tracklist(given['tracklist'], given['formats']) == expected


def test_discogs(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(ReleaseConverter, "_discogs_release_endpoint", lambda _, release_id: load_json(release_id))
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
    assert release.status == "official"
    # release.packaging
    note = ("Imported from https://www.discogs.com/release/13954 using Discobrain"
    " https://github.com/henry-oberholtzer/discobrain")
    assert release.edit_note == note
    # release.redirect_uri
    assert release.events
    assert len(release.events) == 1
    assert release.events[0] == MBEvent(
        date=MBDate(year=2001, month=10, day=15),
        country='GB')
    # release.labels
    # release.artist_credit
    # release.mediums


