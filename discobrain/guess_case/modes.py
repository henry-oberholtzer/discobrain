"""
A port of `guess-case` from MetaBrainz to Python

Original code:
Copyright (c) 2005 Stefan Kestenholz
Copyright (c) 2010 MetaBrainz Foundation
https://github.com/metabrainz/musicbrainz-server/tree/master/root/static/scripts/guess-case

Port:

Copyright (c) 2026 Henry Oberholtzer

"""

import re
from collections.abc import Callable
from re import Pattern
from typing import NamedTuple

from .word_checker import is_prep_bracket_single_word, is_prep_bracket_word

from .utils import safe_index

GUESS_CASE_MODES = ["English", "French", "Sentence", "Turkish"]

def is_guess_case_mode_name(mode_name: str) -> bool:
    return mode_name in GUESS_CASE_MODES

LOWERCASE_WORDS = re.compile(
    r"^(a|an|and|as|at|but|by|da|de|di|fe|fi|for|in|ina|inna|n|nor|o|of|on|or|tha|the|to)$") 
LOWERCASE_WORDS_TURKISH = re.compile("^(ve|ile|ya|veya|yahut|ki|mı|mi|mu|mü|mısın|musun|mudur|mıdır|midir|miyim|misin|misiniz|mısınız|müsün|müyüm|müsünüz|mıyım|muyum|musunuz|miyiz|mıyız|muyuz|müyüz|müdür)$")


UPPERCASE_WORDS = re.compile(
    r"^(dj|mc|tv|mtv|ep|lp|ymca|nyc|ny|ussr|usa|r&b|bbc|fm|bc|ac|dc|uk|bpm|ok|nba|rza|gza|odb|dmx|2xlc)$")

ROMAN_NUMERALS = re.compile(r"^m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$")

# Roman numerals that are also common words.
EXCLUDED_ROMAN_NUMERALS = re.compile(r"^(?:mi|mix)$")

class Fix(NamedTuple):
    regex: re.Pattern[str]
    repl: str | Callable[[re.Match[str]], str]
    re_global: bool = True

PREPOCESS_FIXLIST = [
    # trim spaces after opening brackets
    Fix(regex=re.compile(r"(^|\s)([({[])\s+($|\b)", flags=re.IGNORECASE), repl='\2', re_global=False),
    # trim spaces before closing brackets
    Fix(regex=re.compile(r"(\b|^)\s+([)}\]])($|\b)", flags=re.IGNORECASE), repl='\2', re_global=False),
    # vinyl 12'' -> 12"
    Fix(regex=re.compile(r"(\s|^|\()(\d+)''(\s|$)", flags=re.IGNORECASE), repl='\2"', re_global=False),
    # vinyl 12in -> 12"
    Fix(regex=re.compile(r"(\s|^|\()(\d+)in(ch)?(\s|$)", flags=re.IGNORECASE), repl='\2"', re_global=False),
    # combined word hacks, 
    # e.g. replace spaces with underscores ("a cappella" -> a_capella)
    # such that it can be handled correctly in post-processing.
    # A Capella preprocess
    Fix(regex=re.compile(r"(\b|^)a\s?c+ap+el+a(\b)", flags=re.IGNORECASE), repl='a_cappella'), 
    # OC ReMix preprocess
    Fix(regex=re.compile(r"(\b|^)oc\sremix(\b)", flags=re.IGNORECASE), repl='oc_remix'),
    # re-edit preprocess
    Fix(regex=re.compile(r"(\b|^)re-edit(\b)", flags=re.IGNORECASE), repl='re_edit'),
    # a.k.a. preprocess
    Fix(regex=re.compile(r"(\b|^)a\/k\/a(\b)", flags=re.IGNORECASE), repl='a_k_a_'),
    Fix(regex=re.compile(r"(\b|^)a\.k\.a\.(\s)", flags=re.IGNORECASE), repl='a_k_a_'),
]

POSTPROCESS_FIXLIST = [
    # a_cappella inside brackets
    Fix(regex=
      re.compile(r"(\b|^)a_cappella(\b)", flags=re.IGNORECASE), 
      repl='a cappella'
    ),
    # a_cappella outside brackets
    Fix(regex=
        re.compile(r"(\b|^)A_cappella(\b)", flags=re.IGNORECASE),
        repl='A Cappella'
    ),
    # oc_remix
    Fix(regex=
        re.compile(r"(\b|^)oc_remix(\b)", flags=re.IGNORECASE),
        repl='OC ReMix'
    ),
    # re_edit inside brackets
    Fix(regex=
        re.compile(r"(\b|^)re_edit(\b)"),
        repl='re-edit'
    ),
    # re_edit outside brackets
    Fix(regex=
        re.compile(r"(\b|^)Re_edit(\b)"),
        repl='Re-Edit'
    ),
    # a.k.a. lowercase
    Fix(regex=
        re.compile(r"(\b|^)a_k_a_(\b|$)", flags=re.IGNORECASE),
        repl='a.k.a.'
    ),
    # aka lowercase
    Fix(regex=
        re.compile(r"(\b|^)aka(\b|$)", flags=re.IGNORECASE),
        repl='aka'
    ),
# "fe" is considered a lowercase word, but "Santa Fe" is very common in
# song titles, so change that "fe" back into "Fe".
    Fix(regex=
        re.compile(r"(\b|^)Santa fe(\b|$)"),
        repl='Santa Fe'),
    Fix(regex=
        re.compile(r"(\b|^)R\s*&\s*B(\b)", flags=re.IGNORECASE),
        repl='R&B'),
    Fix(regex=
        re.compile(r"(\b|^)\[live\)(\b)", flags=re.IGNORECASE),
        repl='(live)',
        re_global=False
    ),
    Fix(regex=
        re.compile(r"(\b|^)Djs(\b)", flags=re.IGNORECASE),
        repl='DJs'
    ),
    # Apple products
    Fix(regex=
        re.compile(r"(\b|^)imac(\b)", flags=re.IGNORECASE),
        repl='iMac'
    ),
    Fix(regex=
        re.compile(r"(\b|^)ipad(\b)", flags=re.IGNORECASE),
        repl='iPad'
    ),
    Fix(regex=
        re.compile(r"(\b|^)iphone(\b)", flags=re.IGNORECASE),
        repl='iPhone'
    ),
    Fix(regex=
        re.compile(r"(\b|^)ipod(\b)", flags=re.IGNORECASE),
        repl='iPod'
    ),
    Fix(regex=
        re.compile(r"(\b|^)itunes(\b)", flags=re.IGNORECASE),
        repl='iTunes'
    ),
    Fix(regex=
        re.compile(r"(\b|^)tiktok(\b)", flags=re.IGNORECASE),
        repl='TikTok'
    ),
    Fix(regex=
        re.compile(r"(\b|^)youtube(\b)", flags=re.IGNORECASE),
        repl='YouTube'
    ),
    Fix(regex=
        re.compile(r"(\s|^)Rock '?n'? Roll(\s|$)", flags=re.IGNORECASE),
        repl="Rock 'n' Roll"),
    # w/o should be lowercase
    Fix(regex=
        re.compile(r"(\b)w([/／])o(\b)", flags=re.IGNORECASE),
        repl='w\2o',
        re_global=False
    ),
    # f. and f/ should be lowercase
    Fix(regex=
        re.compile(r"(\b)f([.．/／])(\b)", flags=re.IGNORECASE),
        repl='f\2',
        re_global=False
    ),
]

VINYL_SIZE_FIXES = [
    Fix(
        regex=re.compile(r"(\s+|\()(7|10|12)(?:inch\b|in\b|'|''|\")([^s]|$)", flags=re.IGNORECASE),
        repl='\1\2"\3'
    ),
    Fix(
        regex=re.compile(r"((?:\s+|\()(?:7|10|12)\")([^),\s])"),
        repl='\1 \2'
        )
]

TURKISH_LOWERCASE = [
    Fix(regex=re.compile(r"I\u307"), repl='i'),
    Fix(regex=re.compile(r"I"), repl='ı'),
    Fix(regex=re.compile(r"İ"), repl='i'),
]

TURKISH_UPPERCASE = [
    Fix(regex=re.compile(r'i'), repl='İ')
]

def classical_fix(match: re.Match):
    return f"in {str(match.group(0)).upper()}{str(match.group(1)).lower() if match.group(1) else ""} {str(match.group(2)).upper()}"

CLASSICAL_FIX = [
    Fix(
        regex=re.compile(r"\bin ([a-g])(?:[\s-]([Ff]lat|[Ss]harp))?\s(dorian|lydian|major|minor|mixolydian)(?:\b|$)",
        flags=re.IGNORECASE),
        repl=classical_fix
    )
]

FRENCH_FIX = [
    Fix(
        regex=re.compile(r"([!?;:]+)", flags=re.IGNORECASE),
        repl=' \1'
    ),
    Fix(
        regex=re.compile(r"([«]+)", flags=re.IGNORECASE),
        repl=' \1 '
    ),
    Fix(
        regex=re.compile(r"([»]+)", flags=re.IGNORECASE),
        repl=' \1'
    ),
    Fix(
        regex=re.compile(r"^(Le\s|La\s|Les\s|L[’'])(\S+)$", flags=re.IGNORECASE),
        repl=lambda mo: mo.group(0).replace('\'', '’') + mo.group(1).title()
    )
]

def run_fixes(input_string: str, fixes: list[Fix]) -> str:
    """
    Iterate through the fixes array and apply thje fixes to the input string
    """
    for fix in fixes:
        input_string = re.sub(fix.regex, fix.repl, input_string, count=1 if not fix.re_global else 0)
    return input_string

def replace_match(matches: re.Match, input_string: str, regex: Pattern[str], replacement: str) -> str:
    first_parens = matches[1] if matches[1] else ''
    second_parens = matches[-1] if matches[-1] else ''
    return regex.sub(f"{first_parens}{replacement}{second_parens}", input_string)



def output_word_check(output_words: list[str], word_index: int) -> bool:
    return (output_words[word_index] == ' ') | (output_words[word_index] == '"' and (safe_index(output_words, word_index - 1) in ['7', '12'])) | (safe_index(output_words, word_index + 1) == '"' and (output_words[word_index] in ['7', '12'])) | is_prep_bracket_word(output_words[word_index])


class GuessCaseMode:
    @classmethod
    def do_word(cls) -> bool:
        return False

    @classmethod
    def fix_vinyl_sizes(cls, input_string: str) -> str:
        return run_fixes(input_string, VINYL_SIZE_FIXES)

    @classmethod
    def is_lower_case_word(cls, word: str) -> bool:
        return bool(re.match(LOWERCASE_WORDS, word))

    @classmethod
    def is_roman_numeral(cls, word: str) -> bool:
        return bool(
            re.match(ROMAN_NUMERALS, word) and not re.match(EXCLUDED_ROMAN_NUMERALS, word))

    @classmethod
    def is_sentence_caps(cls) -> bool:
        return True

    @classmethod
    def is_upper_case_word(cls, word: str) -> bool:
        return bool(re.match(UPPERCASE_WORDS, word))

    @classmethod
    def prep_extra_title_info(cls, words: list[str]) -> list[str]:
        output_words = words
        last_word = len(words) - 1
        word_index = last_word

        handle_pre_process = False
        while (
            word_index >= 0 and output_word_check(output_words, word_index)):
            handle_pre_process = True
            word_index -= 1

        if word_index < last_word:
            word_index += 1
            while (output_words[word_index] == ' ' and word_index < last_word):
                word_index += 1

            probe = output_words[last_word]
            if (word_index == last_word and is_prep_bracket_single_word(probe)):
                handle_pre_process = False

            if handle_pre_process and word_index > 0 and word_index <= last_word:
                new_words = output_words[0:word_index]

                if safe_index(new_words, word_index -1) == '(':
                    new_words.pop()

                if safe_index(new_words, word_index -1) == '-':
                    new_words.pop()

                new_words.insert(0, '(')
                new_words.extend(
                    output_words[word_index:len(output_words)]
                )
                new_words.append(')')
                output_words = new_words
        return output_words

    @classmethod
    def pre_process_titles(cls, input_string: str) -> str:
        return run_fixes(input_string, PREPOCESS_FIXLIST)

    @classmethod
    def run_post_process(cls, input_string: str) -> str:
        return run_fixes(input_string, POSTPROCESS_FIXLIST)

    @classmethod
    def lower(cls, string: str) -> str:
        return string.lower()

    @classmethod
    def upper(cls, string: str) -> str:
        return string.upper()


class English(GuessCaseMode):

    @staticmethod
    def is_sentence_caps() -> bool:
        return False

    @classmethod
    def run_post_process(cls, input_string: str) -> str:
        return run_fixes(super().run_post_process(input_string), CLASSICAL_FIX)


class French(GuessCaseMode):
    @classmethod
    def run_post_process(cls, input_string: str) -> str:
        return run_fixes(super().run_post_process(input_string), FRENCH_FIX)


class Sentence(GuessCaseMode):
    pass


class Turkish(GuessCaseMode):

    @classmethod
    def is_lower_case_word(cls, word: str) -> bool:
        return bool(LOWERCASE_WORDS.match(word) or LOWERCASE_WORDS_TURKISH.match(word))

    @classmethod
    def is_sentence_caps(cls) -> bool:
        return False

    @classmethod
    def lower(cls, string: str) -> str:
        return run_fixes(string, TURKISH_LOWERCASE).lower()

    @classmethod
    def upper(cls, string: str) -> str:
        return run_fixes(string, TURKISH_UPPERCASE).upper()
