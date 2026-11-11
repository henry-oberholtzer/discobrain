import re

BRACKET_PAIRS: list[list[str]] = [
    ["(", ")"],
    ["[", "]"],
    ["<", ">"],
    ["（", "）"],
    ["［", "］"],
    ["{", "}"],
    ["【", "】"],
]

BRACKET_PAIR_MAPPING: dict[str, str] = {}
OPEN_BRACKETS: set[str] = set()
CLOSE_BRACKETS: set[str] = set()

for _open, _close in BRACKET_PAIRS:
    BRACKET_PAIR_MAPPING[_open] = _close
    BRACKET_PAIR_MAPPING[_close] = _open
    OPEN_BRACKETS.add(_open)
    CLOSE_BRACKETS.add(_close)

# Words which are turned to lowercase if in brackets, but
# are *not* put in brackets if they're found at the end of the sentence.
PRE_BRACKET_SINGLE_WORDS_SET: set[str] = {
    "acoustic",
    "airplay",
    "album",
    "alternate",
    "alternative",
    "ambient",
    "bit",
    "bonus",
    "censored",
    "chillout",
    "clean",
    "club",
    "composition",
    "cut",
    "dance",
    "dialogue",
    "dirty",
    "disc",
    "disco",
    "dub",
    "early",
    "explicit",
    "extended",
    "feat",
    "featuring",
    "ft",
    "instrumental",
    "live",
    "long",
    "loop",
    "main",
    "megamix",
    "mix",
    "official",
    "original",
    "piano",
    "radio",
    "rap",
    "rehearsal",
    "remixed",
    "remode",
    "rework",
    "reworked",
    "session",
    "short",
    "single",
    "studio",
    "take",
    "takes",
    "techno",
    "trance",
    "uncensored",
    "unknown",
    "untitled",
    "version",
    "video",
    "vocal",
    "with",
    "without",
}

PRE_BRACKET_SINGLE_WORDS_REGEX = re.compile(
    rf"^({'|'.join(sorted(PRE_BRACKET_SINGLE_WORDS_SET))})$",
    flags=re.IGNORECASE,
)

# Words which are turned to lowercase if in brackets, and
# put in brackets if they're found at the end of the sentence.
LOWERCASE_BRACKET_WORDS_SET: set[str] = {
    "a_cappella",
    "clubmix",
    "demo",
    "edit",
    "excerpt",
    "interlude",
    "intro",
    "karaoke",
    "maxi",
    "mono",
    "orchestral",
    "outro",
    "outtake",
    "outtakes",
    "quadraphonic",
    "reedit",
    "re_edit",
    "refix",
    "reinterpreted",
    "remake",
    "remaster",
    "remastered",
    "remix",
    "rmx",
    "reprise",
    "skit",
    "stereo",
    "unplugged",
    "vs",
    *PRE_BRACKET_SINGLE_WORDS_SET,
}

LOWERCASE_BRACKET_WORDS_REGEX = re.compile(
    rf"^({'|'.join(sorted(LOWERCASE_BRACKET_WORDS_SET))})$",
    flags=re.IGNORECASE,
)

PREP_BRACKET_WORDS_REGEX = re.compile(
    r'^(?:cd|disk|12["”]|7["”]|a_cappella|re_edit)$',
    flags=re.IGNORECASE,
)

SENTENCE_STOP_CHARS_REGEX = re.compile(r"^[:.;?!/]$")
APOSTROPHE_CHARS_REGEX = re.compile(r"^['’]$")
PUNCTUATION_CHARS_REGEX = re.compile(r"^[:.;?!,]$")

SPLITWORDSANDPUNCTUATION_REGEX = re.compile(
    r"[^!¿¡\"%&'´`‘’‹›“”„“«»()[\]{}*+‐\-,./:;<=>?\s#]"
)

SPECIALCASES_REGEX = re.compile(
    r"(&|¿|¡|\?|!|;|:|'|‘|’|‹|›|\"|“|”|„|“|«|»|-|‐|\+|,|\*|\.|#|%|/|\\|\(|\)|\{|\}|\[|\])"
)

# Stopwords & casing words
LOWER_CASE_WORDS_REGEX = re.compile(
    r"^(a|an|and|as|at|but|by|da|de|di|fe|fi|for|in|ina|inna|n|nor|o|of|on|or|tha|the|to)$",
    flags=re.IGNORECASE,
)

LOWER_CASE_WORDS_TURKISH_REGEX = re.compile(
    r"^(ve|ile|ya|veya|yahut|ki|mı|mi|mu|mü|mısın|musun|mudur|mıdır|midir|miyim|misin|misiniz|mısınız|müsün|müyüm|müsünüz|mıyım|muyum|musunuz|miyiz|mıyız|muyuz|müyüz|müdür)$",
    flags=re.IGNORECASE,
)

UPPER_CASE_WORDS_REGEX = re.compile(
    r"^(dj|mc|tv|mtv|ep|lp|ymca|nyc|ny|ussr|usa|r&b|bbc|fm|bc|ac|dc|uk|bpm|ok|nba|rza|gza|odb|dmx|2xlc)$",
    flags=re.IGNORECASE,
)

ROMAN_NUMERALS_REGEX = re.compile(
    r"^m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$",
    flags=re.IGNORECASE,
)

EXCLUDED_ROMAN_NUMERALS_REGEX = re.compile(r"^(?:mi|mix)$", flags=re.IGNORECASE)

# Special case values
NOT_A_SPECIALCASE = -1
SPECIALCASE_UNKNOWN = 10
SPECIALCASE_DATA_TRACK = 30
SPECIALCASE_SILENCE = 31
SPECIALCASE_UNTITLED = 32
SPECIALCASE_CROWD_NOISE = 33
SPECIALCASE_GUITAR_SOLO = 34
SPECIALCASE_DIALOGUE = 35
