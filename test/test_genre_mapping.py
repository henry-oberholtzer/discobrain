from discobrain.genre_mapping import (
    DISCOGS_ELECTRONIC_STYLE_MAP,
    MB_GENRE_PARENTS,
    map_discogs_electronic_styles,
)


def test_non_electronic_genre_ignored():
    assert map_discogs_electronic_styles(["Rock"], ["Acid", "Techno"]) == []
    assert map_discogs_electronic_styles(["Hip Hop"], ["Boom Bap"]) == []
    assert map_discogs_electronic_styles([], ["Techno"]) == []
    assert map_discogs_electronic_styles(None, ["Techno"]) == []


def test_electronic_without_styles():
    assert map_discogs_electronic_styles(["Electronic"], []) == ["electronic"]
    assert map_discogs_electronic_styles(["Electronic"], None) == ["electronic"]


def test_compound_acid_techno():
    tags = map_discogs_electronic_styles(["Electronic"], ["Acid", "Techno"])
    assert "acid techno" in tags
    assert "techno" in tags
    assert "electronic" in tags


def test_compound_acid_house():
    tags = map_discogs_electronic_styles(["Electronic"], ["Acid", "House"])
    assert "acid house" in tags
    assert "house" in tags
    assert "electronic" in tags


def test_compound_dub_techno():
    tags = map_discogs_electronic_styles(["Electronic"], ["Dub", "Techno"])
    assert "dub techno" in tags
    assert "techno" in tags
    assert "ambient" in tags
    assert "electronic" in tags


def test_compound_minimal_house_microhouse():
    tags = map_discogs_electronic_styles(["Electronic"], ["Minimal", "House"])
    assert "microhouse" in tags
    assert "house" in tags
    assert "minimal techno" in tags
    assert "techno" in tags
    assert "electronic" in tags


def test_standalone_styles_and_casing():
    # Drum n Bass -> drum and bass
    dnb_tags = map_discogs_electronic_styles(["Electronic"], ["Drum n Bass"])
    assert "drum and bass" in dnb_tags
    assert "electronic" in dnb_tags

    # Jungle inherits drum and bass
    jungle_tags = map_discogs_electronic_styles(["Electronic"], ["Jungle"])
    assert "jungle" in jungle_tags
    assert "drum and bass" in jungle_tags
    assert "electronic" in jungle_tags

    # IDM
    idm_tags = map_discogs_electronic_styles(["electronic"], ["IDM"])
    assert "idm" in idm_tags
    assert "electronic" in idm_tags


def test_multiple_styles_combination():
    tags = map_discogs_electronic_styles(["Electronic"], ["Acid", "Techno", "Ambient"])
    assert "acid techno" in tags
    assert "techno" in tags
    assert "ambient" in tags
    assert "electronic" in tags


def test_modifier_without_base():
    # 'Acid' alone doesn't have a standalone mapping; should safely fall back to 'electronic'
    tags = map_discogs_electronic_styles(["Electronic"], ["Acid"])
    assert tags == ["electronic"]


def test_hierarchy_coverage():
    # Verify that every parent referenced in MB_GENRE_PARENTS is a non-empty string
    for child, parents in MB_GENRE_PARENTS.items():
        assert isinstance(child, str) and child
        assert isinstance(parents, tuple) and len(parents) > 0
        for p in parents:
            assert isinstance(p, str) and p

    # Verify DISCOGS_ELECTRONIC_STYLE_MAP keys are frozensets
    for key, values in DISCOGS_ELECTRONIC_STYLE_MAP.items():
        assert isinstance(key, frozenset)
        assert len(key) >= 1
        assert isinstance(values, tuple) and len(values) > 0
