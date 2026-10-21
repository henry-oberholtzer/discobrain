from discogs_musicbrainz_cli.mb_release import MBArtistName, MBName, MBArtistCredit

def test_post_str():
    artist_name = MBArtistName(name="name").post()
    assert artist_name["name"] == "name"

def test_post_none():
    artist_name = MBArtistName().post()
    assert artist_name.get("name") is None

def test_post_list():
    names = MBArtistCredit(names=[
        MBName(name="name_one"),
        MBName(name="name_two")
    ]).post()
    print(names)
    assert names["names.0.name"] == "name_one"
    assert names["names.1.name"] == "name_two"
