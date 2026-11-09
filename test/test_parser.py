from discobrain.parser import parse_discogs_id, parse_discogs_ids


def test_parse_discogs_id_integer():
    assert parse_discogs_id(13954) == 13954


def test_parse_discogs_id_numeric_string():
    assert parse_discogs_id("  13954  ") == 13954


def test_parse_discogs_id_full_url():
    url = "https://www.discogs.com/release/13954-DJ-Teebee-Through-The-Eyes-Of-A-Scorpion"
    assert parse_discogs_id(url) == 13954


def test_parse_discogs_id_short_url():
    assert parse_discogs_id("discogs.com/release/38348") == 38348


def test_parse_discogs_id_url_with_query_params():
    assert parse_discogs_id("https://www.discogs.com/release/631758?ev=item-vc") == 631758


def test_parse_discogs_id_bbcode_format():
    assert parse_discogs_id("[r765433]") == 765433
    assert parse_discogs_id("r765433") == 765433


def test_parse_discogs_id_comments_and_invalid():
    assert parse_discogs_id("# comment line") is None
    assert parse_discogs_id("") is None
    assert parse_discogs_id("   ") is None
    assert parse_discogs_id("not-a-release-url") is None


def test_parse_discogs_ids_multiline_and_deduplication():
    content = """
    # My vinyl import list
    https://www.discogs.com/release/13954-DJ-Teebee-Through-The-Eyes-Of-A-Scorpion
    38348
    https://www.discogs.com/release/13954
    [r765433]

    # another comment
    38348
    631758
    """
    results = parse_discogs_ids(content)
    assert results == [13954, 38348, 765433, 631758]
