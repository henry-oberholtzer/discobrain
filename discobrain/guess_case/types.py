import re

from typing import Literal, TypedDict, NotRequired

ModeName = Literal["English", "French", "Turkish", "Sentence"]

class RegexDict(TypedDict):
    SPLITWORDSANDPUNCTUATION: NotRequired[re.Pattern[str]]
