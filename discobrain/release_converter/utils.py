from collections.abc import Sequence
from functools import lru_cache

import unicode_blocks
from isocodes import ISONamespaceRecord, script_names
from lingua import Language, LanguageDetector, LanguageDetectorBuilder

from discobrain.guess_case import guess_case

DEFAULT_LANGUAGES: tuple[Language, ...] = (
    Language.ENGLISH,
    Language.FRENCH,
    Language.GERMAN,
    Language.DUTCH,
    Language.ITALIAN,
    Language.SPANISH,
    Language.JAPANESE,
)

def mm_ss_to_ms(duration: str) -> int | None:
    if not duration:
        return None
    segments = duration.split(':')
    return (int(segments[0]) * 60 + int(segments[1]))*1000

def guess_iso_15924(text: str) -> str:
    """
    Takes in an input string, returns the most common
    unicode script in ISO code format.
    """
    blocks: dict[str, int] = {}
    for c in text:
        block = unicode_blocks.of(c).name
        if blocks.get(block):
            blocks[block] += 1
        else:
            blocks[block] = 1
    most_common = max(blocks.items(), key=lambda x: x[1])[0]
    if "Latin" in most_common:
        return "Latn"
    results = script_names.find(name=most_common.split(" ")[0])
    if isinstance(results, ISONamespaceRecord):
        alpha_4 = results.get("alpha_4")
        if alpha_4:
            return alpha_4
    return ""


@lru_cache(maxsize=8)
def _build_detector(languages: tuple[Language, ...]) -> LanguageDetector:
    return LanguageDetectorBuilder.from_languages(*languages).build()


def get_language_detector(
    languages: Sequence[Language] | None = None,
) -> LanguageDetector:
    """
    Returns a cached LanguageDetector configured with the specified languages
    (or DEFAULT_LANGUAGES if not specified).
    """
    langs = tuple(languages) if languages is not None else DEFAULT_LANGUAGES
    return _build_detector(langs)


def guess_iso_639_3(
    text: str,
    detector: LanguageDetector | None = None,
    languages: Sequence[Language] | None = None,
) -> str:
    """
    Guesses the ISO 639-3 3-letter language code of the input text.
    Returns an empty string if no language is detected or text is blank.
    """
    cleaned = text.strip()
    if not cleaned:
        return ""
    if detector is None:
        detector = get_language_detector(languages)
    detected = detector.detect_language_of(cleaned)
    if detected:
        return detected.iso_code_639_3.name.lower()
    return ""


def mb_title_case(text: str) -> str:
    if text.isnumeric() or text.islower():
        return text
    return guess_case(text, entity="release", keep_uppercased=True)
