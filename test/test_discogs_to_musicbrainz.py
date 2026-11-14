import json
from pathlib import Path
from typing import cast

import pytest
from pytest import MonkeyPatch

from discobrain.release_converter import (
    ReleaseConverter,
)
from discobrain.release_converter.converter import (
    build_label,
    discogs_append_extra_artists,
    discogs_build_artist,
    discogs_build_artists,
    discogs_build_mediums,
    discogs_strip_disambiguation,
    discogs_tracklist,
    release_disambiguation,
)
from discobrain.release_converter.discogs import (
    DiscogsFormat,
    DiscogsLabel,
    DiscogsRelease,
    DiscogsReleaseArtist,
    DiscogsTrack,
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
            "name": "vinyl",
            "quantity": "1",
            "descriptions": [ '12"', "33 1/3 rpm", "45 rpm", "EP", "Limited Edition", "Repress"],
            "text": "orange"
            }],
        "orange, repress"
    ),
    (
        [{
            "name": "File",
            "quantity": "6",
            "descriptions": [ "AAC", "MP3", "WAV"],
            "text": "320 Kbps"
            }],
        None
        )
    ])
def test_release_disambiguation(given: list[DiscogsFormat], expected: str):
    assert release_disambiguation(given) == expected

@pytest.mark.parametrize("given,expected", [
    pytest.param(
        [
            {
            "name": "File",
            "descriptions": "MP3",
            "qty": 37
            },
            {
             "name": "File",
             "descriptions": "WAV",
             "qty": 2
            }
        ],
        [
            MBMedium(format="Digital Media")
        ],
        id="Digital Media is always 1 medium"
    )
])
def test_discogs_build_medium(given: list[DiscogsFormat], expected: list[MBMedium]):
    assert discogs_build_mediums(given) == expected

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
                            join_phrase=" feat. "
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
    ),
    (
        load_json(199467),
        [
            MBMedium(
                format='12" Vinyl',
                name=None,
                track=[
                    MBTrack(
                        name="Let Me Be Your Underwear (Superstar mix)",
                        number="A1",
                        length=540000,
                        artist_credit=MBArtistCredit(
                            names=[
                                MBName(
                                    name="Club 69",
                                    mbid="https://www.discogs.com/artist/216",
                                    artist=MBArtistName(name="Club 69")
                                )
                            ]
                            )
                    ),
                    MBTrack(
                        name="Let Me Be Your Underwear (vocal club mix)",
                        number="A2",
                        length=(5*60+35)*1000,
                        artist_credit=MBArtistCredit(
                            names=[
                                MBName(
                                    name="Club 69",
                                    mbid="https://www.discogs.com/artist/216",
                                    artist=MBArtistName(name="Club 69")
                                )
                            ]
                            )
                    ),
                    MBTrack(
                        name="Always Unique (Peter's Disko Trip)",
                        number="B1",
                        length=(7*60+57)*1000,
                        artist_credit=MBArtistCredit(
                            names=[
                                MBName(
                                    name="Club 69",
                                    mbid="https://www.discogs.com/artist/216",
                                    artist=MBArtistName(name="Club 69")
                                )
                            ]
                            )
                    ),
                    MBTrack(
                        name="Always Unique (Cevin's Disko Trip)",
                        number="B2",
                        length=(6*60+15)*1000,
                        artist_credit=MBArtistCredit(
                            names=[
                                MBName(
                                    name="Club 69",
                                    mbid="https://www.discogs.com/artist/216",
                                    artist=MBArtistName(name="Club 69")
                                )
                            ]
                            )
                    )
                ]
            )
        ]
    ),
    (
            load_json(21483373),
            [
                MBMedium(
                    format="CD",
                    track=[
                        MBTrack(
                            name="Piano Trio in G minor, Op. 17: Allegro Moderato / Scherzo: Tempo di Menuetto / Andante / Allegretto",
                            length=((11*60+31)+(4*60+51)+(5*60+10)+(7*60+39))*1000,
                            artist_credit=MBArtistCredit(
                                names=[
                                    MBName(
                                        name="Clara Schumann",
                                        mbid="https://www.discogs.com/artist/933317",
                                        join_phrase=", ",
                                        artist=MBArtistName(name="Clara Schumann")
                                    ),
                                    MBName(
                                        name="Robert Schumann",
                                        mbid="https://www.discogs.com/artist/578727",
                                        join_phrase=" - ",
                                        artist=MBArtistName(name="Robert Schumann")
                                    ),
                                    MBName(
                                        name="The Atlantis Trio",
                                        mbid="https://www.discogs.com/artist/11420129",
                                        artist=MBArtistName(name="The Atlantis Trio")
                                    ),
                                ]
                            )
                        ),
                        MBTrack(
                            name="Piano Trio No. 1 in D minor, Op. 63: Mit Energie und Leidenschaft / Lebhaft, Doch Nicht Zu Rasch / Langsam Mit Inniger Empfindung / Mit Feuer",
                            length=((13*60+3)+(5*60+1)+(6*60+32)+(8*60+57))*1000,
                            artist_credit=MBArtistCredit(
                                names=[
                                    MBName(
                                        name="Clara Schumann",
                                        mbid="https://www.discogs.com/artist/933317",
                                        join_phrase=", ",
                                        artist=MBArtistName(name="Clara Schumann")
                                    ),
                                    MBName(
                                        name="Robert Schumann",
                                        mbid="https://www.discogs.com/artist/578727",
                                        join_phrase=" - ",
                                        artist=MBArtistName(name="Robert Schumann")
                                    ),
                                    MBName(
                                        name="The Atlantis Trio",
                                        mbid="https://www.discogs.com/artist/11420129",
                                        artist=MBArtistName(name="The Atlantis Trio")
                                    ),
                                ]
                            )
                        )
                    ]
                )
            ]
    )
])
def test_discogs_tracklist(given: DiscogsRelease, expected: list[MBMedium]):
    mediums = discogs_build_mediums(given['formats'])
    album_artist = discogs_build_artists(given['artists'])
    assert discogs_tracklist(mediums, album_artist, given['tracklist']) == expected

def test_discogs_tracklist_titled_multidisc():
    mediums = [MBMedium(), MBMedium()]
    album_artist = MBArtistCredit()
    discogs_tracks: list[DiscogsTrack] = [
        {
            "type_": "heading",
            "title": "First Disc Title ",
            "duration": "",
            "position": ""
        },
        {
            "type_": "track",
            "title": "Test Track",
            "duration": "",
            "position": "1-1"
        },
        {
            "type_": "heading",
            "title": "Second Disc Title",
            "duration": "",
            "position": ""
        },
        {
            "type_": "track",
            "title": "Test Track",
            "duration": "",
            "position": "2-1"
        }
    ]
    discogs_tracklist(mediums, album_artist, discogs_tracks)
    assert mediums[0].name == "First Disc Title"
    assert mediums[1].name == "Second Disc Title"

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
    assert release.comment == None
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
def test_discogs_build_artist(given: DiscogsReleaseArtist, expected: MBName):
    assert discogs_build_artist(given) == expected

@pytest.mark.parametrize("given_artist,given_extra,expected", [
    pytest.param(
        MBArtistCredit(
            names=[
                MBName(
                    mbid="1",
                    name="Nick The Kid", join_phrase=" & "),
                MBName(
                    mbid="2",
                    name="Kitchen Disco", join_phrase=" feat. "),
                MBName(
                    mbid="https://www.discogs.com/artist/3",
                    name="Anna McDonalds"
                )
            ]
        ),
        [{
            "id": 3,
            "name": "Anna McDonalds",
            "role": "Featuring"
        }],
        MBArtistCredit(
            names=[
                MBName(
                    mbid="1",
                    name="Nick The Kid", join_phrase=" & "),
                MBName(
                    mbid="2",
                    name="Kitchen Disco", join_phrase=" feat. "),
                MBName(
                    mbid="https://www.discogs.com/artist/3",
                    name="Anna McDonalds"
                )
            ]
        ),
        id="Duplicate featured artists"
    ) 
])
def test_discogs_append_extra_artists(given_artist: MBArtistCredit, given_extra: list[DiscogsReleaseArtist], expected: MBArtistCredit):
    assert expected == discogs_append_extra_artists(given_artist, given_extra)

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

