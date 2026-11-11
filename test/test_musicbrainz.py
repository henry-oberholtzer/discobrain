import pytest

from discobrain.release_converter.musicbrainz import (
    MBURL,
    MBArtistCredit,
    MBArtistName,
    MBDate,
    MBEvent,
    MBLabel,
    MBMedium,
    MBName,
    MBRelease,
    MBTrack,
)
from discobrain.release_converter.utils import mb_title_case


def test_post_flatten():
    artist_name = MBArtistName(name="name").flatten()
    assert artist_name["name"] == "Name"

def test_flatten_none():
    artist_name = MBArtistName().flatten()
    assert artist_name.get("name") is None

def test_flatten_list():
    names = MBArtistCredit(
        names=[
        MBName(
            name="name_one",
            join_phrase=" & "
            ),
        MBName(name="name_two")
    ]).flatten()
    assert names["names.0.name"] == "Name_one"
    assert names["names.0.join_phrase"] == " & "
    assert names["names.1.name"] == "Name_two"

def test_release_flatten():
    name = "It's The Release Name"
    release_group = "123"
    url = "https://example.com"
    comment = "a comment"
    barcode = "123456"
    packaging = "Cardboard/Paper Sleeve"
    artist_credit=MBArtistCredit(names=[
    MBName(
        name="name_one",
        mbid="1234",
        artist=MBArtistName(name="Artist Name"),
        join_phrase=" & "
        ),
    MBName(name="name_two")
    ])
    release = MBRelease(
        name=name,
        urls=[MBURL(url=url, link_type=0)],
        release_group=release_group,
        type="album",
        comment=comment,
        annotation=comment,
        barcode=barcode,
        packaging=packaging,
        events=[MBEvent(date=MBDate(year=1998, month=12, day=31), country="Netherlands")],
        labels=[MBLabel(mbid="abcd", catalog_number="TEST 123", name="LABEL NAME")],
        artist_credit=artist_credit,
        mediums=[
            MBMedium(
                format="Vinyl",
                name="Medium Name",
                track=[
                    MBTrack(
                    name="Track One",
                    number="A",
                    recording="fghj",
                    length=120,
                    artist_credit=artist_credit
                )]
            ),
            MBMedium(format="CD")]
    ).flatten()
    assert release["name"] == "It's the Release Name"
    assert release["type"] == "album"
    assert release["release_group"] == release_group
    assert release["urls.0.url"] == url
    assert release["urls.0.link_type"] == 0
    assert release["comment"] == comment
    assert release["annotation"] == comment
    assert release["barcode"] == barcode
    assert release["language"] == "eng"
    assert release["script"] == "Latn"
    assert release["packaging"] == packaging
    assert release["events.0.date.year"] == 1998
    assert release["events.0.date.month"] == 12
    assert release["events.0.date.day"] == 31
    assert release["events.0.country"] == "NL"
    assert release["labels.0.mbid"] == "abcd"
    assert release["labels.0.catalog_number"] == "TEST 123"
    assert release["labels.0.name"] == "LABEL NAME"
    assert release["artist_credit.names.0.mbid"] == "1234"
    assert release["artist_credit.names.0.name"] == "Name_one"
    assert release["artist_credit.names.0.join_phrase"] == " & "
    assert release["artist_credit.names.0.artist.name"] == "Artist Name"
    assert release["artist_credit.names.1.name"] == "Name_two"
    assert release["mediums.0.format"] == "Vinyl"
    assert release["mediums.0.name"] == "Medium Name"
    assert release["mediums.0.track.0.name"] == "Track One"
    assert release["mediums.0.track.0.number"] == "A"
    assert release["mediums.0.track.0.recording"] == "fghj"
    assert release["mediums.0.track.0.length"] == 120
    assert release["mediums.0.track.0.artist_credit.names.0.mbid"] == "1234"
    assert release["mediums.0.track.0.artist_credit.names.0.name"] == "Name_one"
    assert release["mediums.0.track.0.artist_credit.names.0.join_phrase"] == " & "
    assert release["mediums.0.track.0.artist_credit.names.0.artist.name"] == "Artist Name"
    assert release["mediums.0.track.0.artist_credit.names.1.name"] == "Name_two"
    assert release["mediums.1.format"] == "CD"

def test_country_known():
    event = MBEvent(country="United States")
    assert event.country == "US"

def test_country_unknown():
    event = MBEvent(country="UNKNOWN")
    assert event.country == "UNKNOWN"

@pytest.mark.parametrize("text,expected", [
    ("Spirit Of Adventure", "Spirit of Adventure"),
    ("The Artist", "The Artist"),
    ("The Anthem (Original Mix)", "The Anthem (original mix)"),
    ("The Anthem (Kemal Remix)", "The Anthem (Kemal remix)"),
    ("Born To Be Slytherin", "Born to Be Slytherin"),
    ("A Special Person", "A Special Person"),
    ("The Work Of Art In The Age Of Cultural Overproduction", "The Work of Art in the Age of Cultural Overproduction"),
    ("Something Else... The Bleeps Tune", "Something Else... The Bleeps Tune"),
    ("ALL IN UPPERCASE", "ALL IN UPPERCASE"),
    ("a title in lowercase", "a title in lowercase"),
    ("2 For Da Time", "2 for da Time"),
])
def test_titlecase(text: str, expected: str):
    assert mb_title_case(text) == expected


def test_mb_base_entity_guess_case():
    artist = MBArtistName(name="the prodigy & tom morello")
    assert artist.name == "The Prodigy & Tom Morello"

    name_entry = MBName(name="dj shadow")
    assert name_entry.name == "DJ Shadow"

    label = MBLabel(name="da! heard it records")
    assert label.name == "Da! Heard It Records"

    track = MBTrack(name="some song (club mix)")
    assert track.name == "Some Song (club mix)"

    release = MBRelease(name="all the piano sonatas")
    assert release.name == "All the Piano Sonatas"

