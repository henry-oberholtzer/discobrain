import re

import unicode_blocks
from guess_language import guess_language
from isocodes import ISONamespaceRecord, extended_languages, script_names


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


def guess_iso_639_3(text: str) -> str:
    if len(text) > 20:
        guess = guess_language(text)
        if isinstance(guess, str):
            return extended_languages.get(alpha_2=guess)['alpha_3']
    return ""

ENG_ARTICLES = {
    "a",
    "an",
    "da",
    "the"
}

ENG_CONJUGATIONS = {
    "and",
    "'n'",
    "'n",
    "but",
    "or",
    "nor"
}

ENG_PREPOSITIONS = {
    "as",
    "at",
    "by",
    "for",
    "in",
    "of",
    "o'",
    "on",
    "to",
    "but",
    "per",
    "qua",
    "re",
    "up",
    "via",
}

# Via MusicBrainz wordChecker.js
ENG_ETI = {
    "original mix",
    "mix",
    "remix"
}

LOWERCASE_WORDS = {
    *ENG_ARTICLES,
    *ENG_PREPOSITIONS,
    *ENG_CONJUGATIONS,
    *ENG_ETI
}

def mb_title_case(text: str) -> str:
    def lowercase(matchobj) -> str:
        return matchobj.group(0).lower()
    # If it's all uppercase, lowercase, or numeric, skip
    if text.isupper() or text.isnumeric() or text.islower():
        return text
    for word in LOWERCASE_WORDS:
        regex = rf'(?<=[\w\d\s,][\s\(]){word}(?=[\s,\)])'
        text = re.sub(regex, lowercase, text, flags=re.IGNORECASE)
    return text
