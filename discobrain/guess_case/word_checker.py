import re
from functools import reduce

PRE_BRACKET_SINGLE_WORDS_SET = {
  'acoustic',
  'airplay',
  'album',
  'alternate',
  'alternative',
  'ambient',
  'bit',
  'bonus',
  'censored',
  'chillout',
  'clean',
  'club',
  'composition',
  'cut',
  'dance',
  'dialogue',
  'dirty',
  'disc',
  'disco',
  'dub',
  'early',
  'explicit',
  'extended',
  'feat',
  'featuring',
  'ft',
  'instrumental',
  'live',
  'long',
  'loop',
  'main',
  'megamix',
  'mix',
  'official',
  'original',
  'piano',
  'radio',
  'rap',
  'rehearsal',
  'remixed',
  'remode',
  'rework',
  'reworked',
  'session',
  'short',
  'single',
  'studio',
  'take',
  'takes',
  'techno',
  'trance',
  'uncensored',
  'unknown',
  'untitled',
  'version',
  'video',
  'vocal',
  'with',
  'without',
}

LOWERCASE_BRACKET_WORDS_SET = {
  'a_cappella',
  'clubmix',
  'demo',
  'edit',
  'excerpt',
  'interlude',
  'intro',
  'karaoke',
  'maxi',
  'mono',
  'orchestral',
  'outro',
  'outtake',
  'outtakes',
  'quadraphonic',
  'reedit',
  're_edit',
  'refix',
  'reinterpreted',
  'remake',
  'remaster',
  'remastered',
  'remix',
  'rmx',
  'reprise',
  'skit',
  'stereo',
  'unplugged',
  'vs',
  *PRE_BRACKET_SINGLE_WORDS_SET
}

PREP_BRACKET_WORDS = re.compile(
    r'^(?:cd|disk|12["”]|7["”]|a_cappella|re_edit)$',
    flags=re.IGNORECASE
)

PRE_BRACKET_SINGLE_WORDS_REGEX = re.compile(rf"^({'|'.join(PRE_BRACKET_SINGLE_WORDS_SET)})$", flags=re.IGNORECASE)

LOWERCASE_BRACKET_WORDS_REGEX = re.compile(rf"^({'|'.join(LOWERCASE_BRACKET_WORDS_SET)})$", flags=re.IGNORECASE)

SENTENCE_STOP_CHARS_REGEX = re.compile(r"^[:.;?!]$")

APOSTROPHE_CHARS = re.compile(r"^['’]$")

PUNCTUATION_CHARS_REGEX = re.compile(r"^[:.;?!,]$")

BRACKET_PAIR_LIST = [
    ['(', ')'],
    ['[', ']'],
    ['<', '>'],
    ['（', '）'],
    ['［', '］'],
    ['{', '}'],
    ['【', '】'],
]

def bracket_acc(acc: dict[str,str], curr: list[str]) -> dict[str, str]:
    acc[curr[0]] = curr[1]
    acc[curr[1]] = curr[0]
    return acc

BRACKET_PAIR_MAPPING = reduce(bracket_acc, BRACKET_PAIR_LIST, {})

BRACKET_CHARS_REGEX = re.compile(rf"""^[
    {re.escape('|'.join('|'.join(pair) for pair in BRACKET_PAIR_LIST))}
]$""")

def is_bracket_char(word: str) -> bool:
    return bool(re.match(BRACKET_CHARS_REGEX, word))

def is_prep_bracket_single_word(word: str) -> bool:
    return bool(re.match(PRE_BRACKET_SINGLE_WORDS_REGEX, word))

def is_lowercase_bracket_word(word: str) -> bool:
    return bool(re.match(LOWERCASE_BRACKET_WORDS_REGEX, word))

def is_prep_bracket_word(word: str) -> bool:
    return bool(
        re.match(PREP_BRACKET_WORDS, word) or 
        is_lowercase_bracket_word(word))

def is_sentence_stop_char(word: str) -> bool:
    return bool(re.match(SENTENCE_STOP_CHARS_REGEX, word))


def is_apostrophe(word: str) -> bool:
    return bool(re.match(APOSTROPHE_CHARS, word))


def is_punctuation_char(word: str) -> bool:
    return bool(re.match(PUNCTUATION_CHARS_REGEX, word))



