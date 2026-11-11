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

from ..constants import NOT_A_SPECIALCASE, SPECIALCASE_UNTITLED
from .base import BaseHandler

RE_WORK_UNTITLED = re.compile(
    r"^([(\[]?\s*untitled\s*[)\]]?)$", flags=re.IGNORECASE
)


class WorkHandler(BaseHandler):
    def check_special_case(self, input_string: str | None = None) -> int:
        if input_string and RE_WORK_UNTITLED.match(input_string):
            return SPECIALCASE_UNTITLED
        return NOT_A_SPECIALCASE

    def get_words_for_processing(self, input_string: str) -> list[str]:
        prepped = self.mode.pre_process_titles(input_string)
        words = self.input.split_words_and_punctuation(prepped)
        return self.mode.prep_extra_title_info(words)

    def do_word(self) -> bool:
        _ = (
            self.do_ignore_words()
            or self.do_featuring_artist_style()
            or self.mode.do_word()
            or self.do_normal_word()
        )
        self.context.number = False
        return True

    def guess_sort_name(self, input_string: str) -> str:
        return self.move_article_to_end(input_string)
