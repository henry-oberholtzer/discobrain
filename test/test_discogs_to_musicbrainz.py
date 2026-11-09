import json
from pathlib import Path
from typing import cast

import pytest
from pytest import MonkeyPatch

from discobrain.release_converter import (
    ReleaseConverter,
)
from discobrain.release_converter.converter import (
    discogs_strip_disambiguation,
    discogs_tracklist,
    release_disambiguation,
)
from discobrain.release_converter.discogs import DiscogsFormat, DiscogsRelease
from discobrain.release_converter.musicbrainz import (
    MBURL,
    MBArtistCredit,
    MBArtistName,
    MBDate,
    MBEvent,
    MBLabel,
    MBMedium,
    MBName,
    MBReleaseType,
    MBTrack,
    MusicBrainzLookUp,
)

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
                            mbid="https://www.discogs.com/artist/100457",
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
                            mbid="https://www.discogs.com/artist/100457",
                            artist=MBArtistName(name="Noisia"),
                            join_phrase=" Feat. "
                        ),
                        MBName(
                            name="Phace",
                            mbid="https://www.discogs.com/artist/132592",
                            artist=MBArtistName(name="Phace")
                        )
                    ]
                )
            )
        ])]
    )
])
def test_discogs_tracklist(given: DiscogsRelease, expected: list[MBMedium]):
    assert discogs_tracklist(given) == expected


def test_discogs_teebee(monkeypatch: MonkeyPatch):
    mapping = {
        "https://www.discogs.com/artist/22979": "33299664-1156-4888-a01e-f12797aa1941",
        "https://www.discogs.com/label/161": "39c4dc0c-badb-4ac3-b810-e4f374dff6d9",
        "https://www.discogs.com/master/29822": "6d902f27-8a49-354b-ba99-735e3b570262"
    }
    def fake_lookup(key: str) -> str | None:
        return mapping.get(key)

    monkeypatch.setattr(MusicBrainzLookUp, "get_by_url", lambda _, url: fake_lookup(url))
    monkeypatch.setattr(ReleaseConverter, "_discogs_release_endpoint", lambda _, release_id: load_json(release_id))
    release = ReleaseConverter().discogs(13954)
    assert release.name == "Through the Eyes of a Scorpion"
    assert release.urls == [MBURL(url="https://www.discogs.com/release/13954", link_type=76)]
    assert release.release_group == "6d902f27-8a49-354b-ba99-735e3b570262"
    assert release.barcode == "5033826056260"
    assert release.type == MBReleaseType.ALBUM
    assert release.comment == ""
    assert release.language == "eng"
    assert release.script == "Latn"
    assert release.status == "official"
    note = ("Imported from https://www.discogs.com/release/13954 using Discobrain"
    " https://github.com/henry-oberholtzer/discobrain")
    assert release.edit_note == note
    assert release.events == [MBEvent(
        date=MBDate(year=2001, month=10, day=15),
        country='GB')]
    assert release.labels == [MBLabel(
        name="Certificate 18",
        mbid="39c4dc0c-badb-4ac3-b810-e4f374dff6d9",
        catalog_number="CERT18 LP014"
    )]
    teebee_credit = MBArtistCredit(
        names=[
        MBName(
            name="DJ Teebee",
            mbid="33299664-1156-4888-a01e-f12797aa1941",
            artist=MBArtistName(name="Teebee")
        )
    ]
    )
    assert release.artist_credit == teebee_credit
    assert release.mediums == [
            MBMedium(
                format='12" Vinyl',
                track=[
                    MBTrack(
                        name="Silent Depths",
                        number="A",
                        artist_credit=teebee_credit
                    ),
                    MBTrack(
                        name="Revelations",
                        number="B",
                        artist_credit=teebee_credit
            )]),
            MBMedium(
                format='12" Vinyl',
                track=[
                    MBTrack(
                        name="Frequencies",
                        number="C",
                        artist_credit=teebee_credit
                    ),
                    MBTrack(
                        name="Behind the Sun",
                        number="D",
                        artist_credit=teebee_credit
            )]),
            MBMedium(
                format='12" Vinyl',
                track=[
                    MBTrack(
                        name="Severed Dreams",
                        number="E",
                        artist_credit=teebee_credit
                    ),
                    MBTrack(
                        name="Retaliation",
                        number="F",
                        artist_credit=teebee_credit
            )]),
            MBMedium(
                format='12" Vinyl',
                track=[
                    MBTrack(
                        name="Rave Alarm",
                        number="G",
                        artist_credit=teebee_credit
                    ),
                    MBTrack(
                        name="Lost Souls",
                        number="H",
                        artist_credit=teebee_credit
            )])
    ]

@pytest.mark.parametrize("given,expected", [("Artist (9)", "Artist"), ("Artist Name 123  (4)", "Artist Name 123")])
def test_discogs_strip_disambiguation(given: str, expected: str):
    assert discogs_strip_disambiguation(given) == expected
