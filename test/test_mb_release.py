from discogs_musicbrainz_cli.mb_release import (
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


def test_post_flatten():
    artist_name = MBArtistName(name="name").flatten()
    assert artist_name["name"] == "name"

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
    assert names["names.0.name"] == "name_one"
    assert names["names.0.join_phrase"] == " & "
    assert names["names.1.name"] == "name_two"

def test_release_flatten():
    name = "Release Name"
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
        language="English",
        script="Latin",
        packaging=packaging,
        events=[MBEvent(date=MBDate(year=1998, month=12, day=31), country="NL")],
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
    assert release["name"] == name
    assert release["type"] == "album"
    assert release["release_group"] == release_group
    assert release["urls.0.url"] == url
    assert release["urls.0.link_type"] == 0
    assert release["comment"] == comment
    assert release["annotation"] == comment
    assert release["barcode"] == barcode
    assert release["language"] == "English"
    assert release["script"] == "Latin"
    assert release["packaging"] == packaging
    assert release["events.0.date.year"] == 1998
    assert release["events.0.date.month"] == 12
    assert release["events.0.date.day"] == 31
    assert release["events.0.country"] == "NL"
    assert release["labels.0.mbid"] == "abcd"
    assert release["labels.0.catalog_number"] == "TEST 123"
    assert release["labels.0.name"] == "LABEL NAME"
    assert release["artist_credit.names.0.mbid"] == "1234"
    assert release["artist_credit.names.0.name"] == "name_one"
    assert release["artist_credit.names.0.join_phrase"] == " & "
    assert release["artist_credit.names.0.artist.name"] == "Artist Name"
    assert release["artist_credit.names.1.name"] == "name_two"
    assert release["mediums.0.format"] == "Vinyl"
    assert release["mediums.0.name"] == "Medium Name"
    assert release["mediums.0.track.0.name"] == "Track One"
    assert release["mediums.0.track.0.number"] == "A"
    assert release["mediums.0.track.0.recording"] == "fghj"
    assert release["mediums.0.track.0.length"] == 120
    assert release["mediums.0.track.0.artist_credit.names.0.mbid"] == "1234"
    assert release["mediums.0.track.0.artist_credit.names.0.name"] == "name_one"
    assert release["mediums.0.track.0.artist_credit.names.0.join_phrase"] == " & "
    assert release["mediums.0.track.0.artist_credit.names.0.artist.name"] == "Artist Name"
    assert release["mediums.0.track.0.artist_credit.names.1.name"] == "name_two"
    assert release["mediums.1.format"] == "CD"



