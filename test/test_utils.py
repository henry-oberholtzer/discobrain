import pytest

from release_converter.musicbrainz import (
    MBReleaseType,
    mb_release_type_from_title,
    mb_release_type_from_tracks,
)
from release_converter.utils import guess_iso_15924


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
