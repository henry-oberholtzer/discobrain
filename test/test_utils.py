import pytest
from lingua import Language

from discobrain.release_converter.musicbrainz import (
    MBReleaseType,
    mb_release_type_from_title,
    mb_release_type_from_tracks,
)
from discobrain.release_converter.utils import (
    DEFAULT_LANGUAGES,
    get_language_detector,
    guess_iso_639_3,
    guess_iso_15924,
)


@pytest.mark.parametrize("text,script", [(
    "This is a sentence in a latin script",
    "Latn"
),
(
    "Это предложение, написанное кириллицей.",
    "Cyrl"
),
(
    "\u067E",
    "Arab"
),
(
    "\u067E\u067EЭ",
    "Arab"
)
])
def test_most_common_script(text: str, script: str):
    assert guess_iso_15924(text) == script

@pytest.mark.parametrize("given,expected", [
    ("The Big Bang LP", MBReleaseType.ALBUM),
    ("A Problem Joe Nicely (E.P.)", MBReleaseType.EP),
    ("Acid Techno in the Modern Era E.P. Vol 1", MBReleaseType.EP)
    ])
def test_from_title(given: str, expected: str):
    assert mb_release_type_from_title(given) == expected

@pytest.mark.parametrize("tracks,expected", [
    (1, MBReleaseType.SINGLE),
    (2, MBReleaseType.SINGLE),
    (3, MBReleaseType.SINGLE),
    (4, MBReleaseType.EP),
    (5, MBReleaseType.EP),
    (6, MBReleaseType.EP),
    (7, MBReleaseType.ALBUM),
    (8, MBReleaseType.ALBUM)
    ])
def test_from_tracks(tracks: int, expected: str):
    assert mb_release_type_from_tracks(tracks) == expected


@pytest.mark.parametrize(
    "text,expected_lang",
    [
        ("Nevermind Smells Like Teen Spirit In Bloom Come as You Are", "eng"),
        ("Aux sommets des cieux et la terre", "fra"),
        ("Kraftwerk Die Mensch-Maschine Das Model", "deu"),
        ("Het leven is mooi en wij drinken bier op het terras", "nld"),
        ("Una mattina mi son svegliato e ho trovato l'invasor", "ita"),
        ("Canción del mariachi en la noche de luna llena", "spa"),
        ("初音ミクの消失 炉心融解 メルト ワールドイズマイン", "jpn"),
        ("", ""),
        ("   ", ""),
        ("1234567890", ""),
        ("Это предложение, написанное кириллицей.", ""),
    ],
)
def test_guess_iso_639_3(text: str, expected_lang: str):
    assert guess_iso_639_3(text) == expected_lang


def test_default_languages_contains_target_subset():
    expected = {
        Language.ENGLISH,
        Language.FRENCH,
        Language.GERMAN,
        Language.DUTCH,
        Language.ITALIAN,
        Language.SPANISH,
        Language.JAPANESE,
    }
    assert set(DEFAULT_LANGUAGES) == expected


def test_guess_iso_639_3_with_custom_languages():
    text = "Это предложение, написанное кириллицей."
    assert guess_iso_639_3(text) == ""

    # When Russian is explicitly configured, it should be detected as 'rus'
    custom_langs = (Language.RUSSIAN, Language.ENGLISH)
    custom_detector = get_language_detector(custom_langs)
    assert guess_iso_639_3(text, detector=custom_detector) == "rus"
    assert guess_iso_639_3(text, languages=custom_langs) == "rus"

