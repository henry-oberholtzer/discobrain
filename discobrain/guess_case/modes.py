"""
A Python port of the MusicBrainz `guess-case` module.

Original JavaScript implementation:
Copyright (C) 2005 Stefan Kestenholz (keschte)
Copyright (C) 2010-2024 MetaBrainz Foundation and contributors
Source: https://github.com/metabrainz/musicbrainz-server/tree/master/root/static/scripts/guess-case
Licensed under GPL-2.0-or-later.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from .constants import (
    EXCLUDED_ROMAN_NUMERALS_REGEX,
    LOWER_CASE_WORDS_REGEX,
    LOWER_CASE_WORDS_TURKISH_REGEX,
    ROMAN_NUMERALS_REGEX,
    UPPER_CASE_WORDS_REGEX,
)
from .types import ModeName
from .utils import (
    is_prep_bracket_single_word,
    is_prep_bracket_word,
    safe_index,
)

GUESS_CASE_MODES: list[ModeName] = ["English", "French", "Sentence", "Turkish"]


def is_guess_case_mode_name(mode_name: str) -> bool:
    return mode_name in GUESS_CASE_MODES


FixRule = tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]]

PREPROCESS_FIXES: list[FixRule] = [
    # spaces after opening brackets
    (
        re.compile(r"(^|\s)([({[])\s+($|\b)", flags=re.IGNORECASE),
        r"\g<1>\g<2>\g<3>",
    ),
    # spaces before closing brackets
    (
        re.compile(r"(\b|^)\s+([)}\]])($|\b)", flags=re.IGNORECASE),
        r"\g<1>\g<2>\g<3>",
    ),
    # vinyl
    (
        re.compile(r"(\s|^|\()(\d+)''(\s|$)", flags=re.IGNORECASE),
        r'\g<1>\g<2>"\g<3>',
    ),
    (
        re.compile(r"(\s|^|\()(\d+)in(ch)?(\s|$)", flags=re.IGNORECASE),
        r'\g<1>\g<2>"\g<4>',
    ),
    # combined word hacks
    (
        re.compile(r"(\b|^)a\s?c+ap+el+a(\b)", flags=re.IGNORECASE),
        r"\g<1>a_cappella\g<2>",
    ),
    (
        re.compile(r"(\b|^)oc\sremix(\b)", flags=re.IGNORECASE),
        r"\g<1>oc_remix\g<2>",
    ),
    (
        re.compile(r"(\b|^)re-edit(\b)", flags=re.IGNORECASE),
        r"\g<1>re_edit\g<2>",
    ),
    (
        re.compile(r"(\b|^)a/k/a(\b)", flags=re.IGNORECASE),
        r"\g<1>a_k_a_\g<2>",
    ),
    (
        re.compile(r"(\b|^)a\.k\.a\.(\s)", flags=re.IGNORECASE),
        r"\g<1>a_k_a_\g<2>",
    ),
]

POSTPROCESS_FIXES: list[FixRule] = [
    # a_cappella inside brackets
    (
        re.compile(r"(\b|^)a_cappella(\b)"),
        r"\g<1>a cappella\g<2>",
    ),
    # a_cappella outside brackets
    (
        re.compile(r"(\b|^)A_cappella(\b)"),
        r"\g<1>A Cappella\g<2>",
    ),
    # oc_remix
    (
        re.compile(r"(\b|^)oc_remix(\b)", flags=re.IGNORECASE),
        r"\g<1>OC ReMix\g<2>",
    ),
    # re_edit inside brackets
    (
        re.compile(r"(\b|^)re_edit(\b)"),
        r"\g<1>re-edit\g<2>",
    ),
    # re_edit outside brackets
    (
        re.compile(r"(\b|^)Re_edit(\b)"),
        r"\g<1>Re-Edit\g<2>",
    ),
    # a.k.a. lowercase
    (
        re.compile(r"(\b|^)a_k_a_(\b|$)", flags=re.IGNORECASE),
        r"\g<1>a.k.a.\g<2>",
    ),
    # aka lowercase
    (
        re.compile(r"(\b|^)aka(\b|$)", flags=re.IGNORECASE),
        r"\g<1>aka\g<2>",
    ),
    # Santa Fe
    (
        re.compile(r"(\b|^)Santa fe(\b|$)"),
        r"\g<1>Santa Fe\g<2>",
    ),
    # R&B
    (
        re.compile(r"(\b|^)R\s*&\s*B(\b)", flags=re.IGNORECASE),
        r"\g<1>R&B\g<2>",
    ),
    # [live]
    (
        re.compile(r"(\b|^)\[live\](\b)", flags=re.IGNORECASE),
        r"\g<1>(live)\g<2>",
    ),
    # DJs
    (
        re.compile(r"(\b|^)Djs(\b)", flags=re.IGNORECASE),
        r"\g<1>DJs\g<2>",
    ),
    # Apple products
    (
        re.compile(r"(\b|^)imac(\b)", flags=re.IGNORECASE),
        r"\g<1>iMac\g<2>",
    ),
    (
        re.compile(r"(\b|^)ipad(\b)", flags=re.IGNORECASE),
        r"\g<1>iPad\g<2>",
    ),
    (
        re.compile(r"(\b|^)iphone(\b)", flags=re.IGNORECASE),
        r"\g<1>iPhone\g<2>",
    ),
    (
        re.compile(r"(\b|^)ipod(\b)", flags=re.IGNORECASE),
        r"\g<1>iPod\g<2>",
    ),
    (
        re.compile(r"(\b|^)itunes(\b)", flags=re.IGNORECASE),
        r"\g<1>iTunes\g<2>",
    ),
    # TikTok & YouTube
    (
        re.compile(r"(\b|^)tiktok(\b)", flags=re.IGNORECASE),
        r"\g<1>TikTok\g<2>",
    ),
    (
        re.compile(r"(\b|^)youtube(\b)", flags=re.IGNORECASE),
        r"\g<1>YouTube\g<2>",
    ),
    # Rock 'n' Roll
    (
        re.compile(r"(\s|^)Rock '?n'? Roll(\s|$)", flags=re.IGNORECASE),
        r"\g<1>Rock 'n' Roll\g<2>",
    ),
    # w/o should be lowercase
    (
        re.compile(r"(\b)w([/／])o(\b)", flags=re.IGNORECASE),
        r"\g<1>w\g<2>o\g<3>",
    ),
    # f. and f/ should be lowercase
    (
        re.compile(r"(\b)f([.．/／])(\b)", flags=re.IGNORECASE),
        r"\g<1>f\g<2>\g<3>",
    ),
]


def run_fixes(input_string: str, fixes: list[FixRule]) -> str:
    output = input_string
    for pattern, repl in fixes:
        output = pattern.sub(repl, output)
    return output


class GuessCaseMode:
    name: ModeName = "English"
    description: str = ""

    def do_word(self) -> bool:
        return False

    def fix_vinyl_sizes(self, input_string: str) -> str:
        s = re.sub(
            r"(\s+|\()(7|10|12)(?:inch\b|in\b|'|''|\")([^s]|$)",
            r'\g<1>\g<2>"\g<3>',
            input_string,
            flags=re.IGNORECASE,
        )
        s = re.sub(
            r"((?:\s+|\()(?:7|10|12)\")([^),\s])",
            r"\g<1> \g<2>",
            s,
        )
        return s

    def is_lower_case_word(self, word: str) -> bool:
        return bool(LOWER_CASE_WORDS_REGEX.match(word))

    def is_roman_numeral(self, word: str, roman: bool = False) -> bool:
        return bool(
            roman
            and ROMAN_NUMERALS_REGEX.match(word)
            and not EXCLUDED_ROMAN_NUMERALS_REGEX.match(word)
        )

    def is_sentence_caps(self) -> bool:
        return True

    def is_upper_case_word(self, word: str) -> bool:
        return bool(UPPER_CASE_WORDS_REGEX.match(word))

    def prep_extra_title_info(self, words: list[str]) -> list[str]:
        output_words = list(words)
        last_word = len(output_words) - 1
        word_index = last_word
        handle_pre_process = False

        while word_index >= 0:
            w = output_words[word_index]
            prev_w = safe_index(output_words, word_index - 1)
            next_w = safe_index(output_words, word_index + 1)

            if w == " ":
                word_index -= 1
                continue

            if w == '"' and prev_w in ("7", "12"):
                handle_pre_process = True
                word_index -= 1
                continue

            if next_w == '"' and w in ("7", "12"):
                handle_pre_process = True
                word_index -= 1
                continue

            if is_prep_bracket_word(w):
                handle_pre_process = True
                word_index -= 1
                continue

            break

        if word_index < last_word:
            word_index += 1
            while word_index < last_word and output_words[word_index] == " ":
                word_index += 1

            probe = output_words[last_word]
            if word_index == last_word and is_prep_bracket_single_word(probe):
                handle_pre_process = False

            if handle_pre_process and 0 < word_index <= last_word:
                new_words = list(output_words[:word_index])

                if new_words and new_words[-1] == "(":
                    new_words.pop()
                if new_words and new_words[-1] == "-":
                    new_words.pop()

                new_words.append("(")
                new_words.extend(output_words[word_index:])
                new_words.append(")")
                output_words = new_words

        return output_words

    def pre_process_titles(self, input_string: str) -> str:
        return run_fixes(input_string, PREPROCESS_FIXES)

    def run_post_process(self, input_string: str) -> str:
        return run_fixes(input_string, POSTPROCESS_FIXES)

    def to_lower_case(self, s: str) -> str:
        return s.lower()

    def to_upper_case(self, s: str) -> str:
        return s.upper()


class English(GuessCaseMode):
    name: ModeName = "English"

    def is_sentence_caps(self) -> bool:
        return False

    def run_post_process(self, input_string: str) -> str:
        output = super().run_post_process(input_string)

        def classical_replace(match: re.Match[str]) -> str:
            p1 = match.group(1).upper()
            p2 = f"-{match.group(2).lower()}" if match.group(2) else ""
            p3 = match.group(3).lower()
            return f"in {p1}{p2} {p3}"

        output = re.sub(
            r"\bin ([a-g])(?:[\s-]([Ff]lat|[Ss]harp))?\s(dorian|lydian|major|minor|mixolydian)(?:\b|$)",
            classical_replace,
            output,
            flags=re.IGNORECASE,
        )
        return output


class French(GuessCaseMode):
    name: ModeName = "French"

    def run_post_process(self, input_string: str) -> str:
        output = super().run_post_process(input_string)
        output = re.sub(r"([!?;:]+)", r" \g<1>", output)
        output = re.sub(r"([«]+)", r"\g<1> ", output)
        output = re.sub(r"([»]+)", r" \g<1>", output)

        def french_article(m: re.Match[str]) -> str:
            m1 = m.group(1).replace("'", "’")
            m2 = m.group(2)
            return m1 + m2[:1].upper() + m2[1:]

        output = re.sub(
            r"^(Le\s|La\s|Les\s|L[’'])(\S+)$",
            french_article,
            output,
            flags=re.IGNORECASE,
        )
        return output


class Sentence(GuessCaseMode):
    name: ModeName = "Sentence"


class Turkish(GuessCaseMode):
    name: ModeName = "Turkish"

    def is_lower_case_word(self, word: str) -> bool:
        return bool(
            LOWER_CASE_WORDS_REGEX.match(word)
            or LOWER_CASE_WORDS_TURKISH_REGEX.match(word)
        )

    def is_sentence_caps(self) -> bool:
        return False

    def to_lower_case(self, s: str) -> str:
        t = s.replace("I\u0307", "i").replace("I", "ı").replace("İ", "i")
        return t.lower()

    def to_upper_case(self, s: str) -> str:
        t = s.replace("i", "İ")
        return t.upper()


_MODES: dict[str, GuessCaseMode] = {
    "English": English(),
    "French": French(),
    "Sentence": Sentence(),
    "Turkish": Turkish(),
}


def get_mode(mode_name: str | ModeName) -> GuessCaseMode:
    return _MODES.get(mode_name, _MODES["English"])
