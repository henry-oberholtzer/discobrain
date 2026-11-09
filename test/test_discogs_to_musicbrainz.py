import json
from pathlib import Path
from typing import cast

import pytest
from pytest import MonkeyPatch

from discobrain.release_converter import (
    ReleaseConverter,
)
from discobrain.release_converter.converter import (
    build_artist,
    build_label,
    discogs_strip_disambiguation,
    discogs_tracklist,
    release_disambiguation,
)
from discobrain.release_converter.discogs import (
    DiscogsFormat,
    DiscogsLabel,
    DiscogsRelease,
    DiscogsReleaseArtist,
)
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
from test.test_musicbrainz_lookup import TEST_AGENT

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
    release = ReleaseConverter(lookup=MusicBrainzLookUp(TEST_AGENT)).discogs(13954)
    assert not isinstance(release, list)
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

@pytest.mark.parametrize("given,expected", [
    pytest.param(
        {
            "id": 194
        },
        MBName(mbid="89ad4ac3-39f7-470e-963a-56509c546377"),
        id="Various -> Various Artists"
    ),
    pytest.param(
        {
        "id": 355
        },
        MBName(mbid="125ec42a-7229-4250-afc5-e057484327fe"),
        id="Unknown Artist -> [unknown]"
    ),
    pytest.param(
        {
            "id": 1
        },
        MBName(mbid="https://www.discogs.com/artist/1"),
        id="Minimal artist"
    ),
    pytest.param(
        {
            "name": "The Persuader",
            "anv": "Persuader",
            "join": ",",
            "id": 1
        },
        MBName(
            name="Persuader",
            artist=MBArtistName(name="The Persuader"),
            mbid="https://www.discogs.com/artist/1",
            join_phrase=", "
        ),
        id="Full artist"
    )
])
def test_build_artist(given: DiscogsReleaseArtist, expected: MBName):
    assert build_artist(given) == expected

@pytest.mark.parametrize("given,expected", [
    pytest.param(
        {
        "name": "Not On Label (Depeche Mode)",
        },
        MBLabel(
            mbid="157afde4-4bf5-4039-8ad2-5a15acc85176"
        ),
        id="Not On Label -> [no label]"
    ),
    pytest.param(
        {
        "name": "Integral Records (2)",
        "id" : 87299,
        "catno": "INT 005"
        },
        MBLabel(
            name="Integral Records",
            mbid="https://www.discogs.com/label/87299",
            catalog_number="INT 005"
        ),
        id="Full label w/ Disambiguation"
    )
])
def test_build_label(given: DiscogsLabel, expected: MBLabel):
    assert build_label(given) == expected


def test_discogs_converter_replaces_or_clears_discogs_ids():
    lookup = MusicBrainzLookUp(TEST_AGENT, db_file=":memory:")
    # Store a known artist
    lookup.store(
        "https://www.discogs.com/artist/100457",
        "ec22a32b-acab-432e-a88c-ffe6ae68fa16",
        "artist",
    )
    # Mock network call in clear_queue
    def mock_get_url_resources(resources: list[str]):
        return []

    def mock_endpoint(release_id: int) -> DiscogsRelease:
        return load_json(765433)

    lookup.get_url_resources = mock_get_url_resources

    converter = ReleaseConverter(lookup=lookup, auto_env=False)
    converter._discogs_release_endpoint = mock_endpoint

    release = converter.discogs(765433)
    assert not isinstance(release, list)
    assert release.artist_credit is not None
    assert release.labels is not None

    # Known artist (Noisia) replaced with MBID
    assert release.artist_credit.names[0].mbid == "ec22a32b-acab-432e-a88c-ffe6ae68fa16"

    # Unknown label, master, and extra artists set to None
    assert release.release_group is None
    assert release.labels[0].mbid is None

    # Flattened payload must NOT have any Discogs URLs in mbid fields
    flat = release.flatten()
    for key, val in flat.items():
        if "mbid" in key:
            assert not str(val).startswith("https://www.discogs.com")
            assert not str(val).startswith("https://discogs.com")
            # Should be a valid UUID
            import re
            assert re.match(r"[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}", str(val))

