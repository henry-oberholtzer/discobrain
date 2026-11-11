import re

from .constants import (
    APOSTROPHE_CHARS_REGEX,
    BRACKET_PAIR_MAPPING,
    LOWERCASE_BRACKET_WORDS_REGEX,
    PRE_BRACKET_SINGLE_WORDS_REGEX,
    PREP_BRACKET_WORDS_REGEX,
    PUNCTUATION_CHARS_REGEX,
    SENTENCE_STOP_CHARS_REGEX,
)


def safe_index[T](lst: list[T], idx: int, default: T | None = None) -> T | None:
    if 0 <= idx < len(lst):
        return lst[idx]
    return default


def clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def trim(text: str | None) -> str:
    cleaned = clean(text)
    cleaned = re.sub(r"([(\[])\s+", r"\1", cleaned)
    cleaned = re.sub(r"\s+([)\]])", r"\1", cleaned)
    return cleaned


def is_bracket_char(char: str | None) -> bool:
    if not char:
        return False
    return char in BRACKET_PAIR_MAPPING


def is_prep_bracket_single_word(word: str | None) -> bool:
    if not word:
        return False
    return bool(PRE_BRACKET_SINGLE_WORDS_REGEX.match(word))


def is_lowercase_bracket_word(word: str | None) -> bool:
    if not word:
        return False
    return bool(LOWERCASE_BRACKET_WORDS_REGEX.match(word))


is_lower_case_bracket_word = is_lowercase_bracket_word


def is_prep_bracket_word(word: str | None) -> bool:
    if not word:
        return False
    return bool(PREP_BRACKET_WORDS_REGEX.match(word)) or is_lowercase_bracket_word(word)


def is_sentence_stop_char(word: str | None) -> bool:
    if not word:
        return False
    return bool(SENTENCE_STOP_CHARS_REGEX.match(word))


def is_apostrophe(word: str | None) -> bool:
    if not word:
        return False
    return bool(APOSTROPHE_CHARS_REGEX.match(word))


def is_punctuation_char(word: str | None) -> bool:
    if not word:
        return False
    return bool(PUNCTUATION_CHARS_REGEX.match(word))
