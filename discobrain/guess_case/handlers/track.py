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

from ..constants import (
    NOT_A_SPECIALCASE,
    SPECIALCASE_DATA_TRACK,
    SPECIALCASE_SILENCE,
    SPECIALCASE_UNKNOWN,
    SPECIALCASE_UNTITLED,
)
from .base import BaseHandler

RE_BONUS_1 = re.compile(
    r"[([]?bonus(\s+track)?s?\s*[)\]]?$", flags=re.IGNORECASE
)
RE_BONUS_2 = re.compile(
    r"[([]?retail(\s+version)?\s*[)\]]?$", flags=re.IGNORECASE
)

RE_TRACK_DATATRACK = re.compile(
    r"^([(\[]?\s*data(\s+track)?\s*[)\]]?)$", flags=re.IGNORECASE
)
RE_TRACK_SILENCE = re.compile(
    r"^([(\[]?\s*(silen(t|ce)|blank)(\s+track)?\s*[)\]]?)$", flags=re.IGNORECASE
)
RE_TRACK_UNTITLED = re.compile(
    r"^([(\[]?\s*untitled(\s+track)?\s*[)\]]?)$", flags=re.IGNORECASE
)
RE_TRACK_UNKNOWN = re.compile(
    r"^([(\[]?\s*(unknown|bonus|hidden)(\s+track)?\s*[)\]]?)$",
    flags=re.IGNORECASE,
)
RE_TRACK_MYSTERY = re.compile(r"^\?+$")
RE_7IN = re.compile(r"^7in$", flags=re.IGNORECASE)
RE_12IN = re.compile(r"^12in$", flags=re.IGNORECASE)


class TrackHandler(BaseHandler):
    def remove_bonus_info(self, input_string: str) -> str:
        s = RE_BONUS_1.sub("", input_string)
        s = RE_BONUS_2.sub("", s)
        return s

    def process(self, input_string: str) -> str:
        return self.mode.fix_vinyl_sizes(super().process(input_string))

    def get_words_for_processing(self, input_string: str) -> list[str]:
        cleaned = self.remove_bonus_info(input_string)
        prepped = self.mode.pre_process_titles(cleaned)
        words = self.input.split_words_and_punctuation(prepped)
        return self.mode.prep_extra_title_info(words)

    def check_special_case(self, input_string: str | None = None) -> int:
        if not input_string:
            return NOT_A_SPECIALCASE
        if RE_TRACK_DATATRACK.match(input_string):
            return SPECIALCASE_DATA_TRACK
        if RE_TRACK_SILENCE.match(input_string):
            return SPECIALCASE_SILENCE
        if RE_TRACK_UNTITLED.match(input_string):
            return SPECIALCASE_UNTITLED
        if RE_TRACK_UNKNOWN.match(input_string):
            return SPECIALCASE_UNKNOWN
        if RE_TRACK_MYSTERY.match(input_string):
            return SPECIALCASE_UNKNOWN
        return NOT_A_SPECIALCASE

    def do_word(self) -> bool:
        if (
            not self.do_ignore_words()
            and not self.do_featuring_artist_style()
            and not self.mode.do_word()
        ):
            if self.input.match_current_word(RE_7IN):
                self.output.append_space_if_needed()
                self.output.append_word('7"')
                self.context.reset_context()
                self.context.space_next_word = False
                self.context.force_caps = False
            elif self.input.match_current_word(RE_12IN):
                self.output.append_space_if_needed()
                self.output.append_word('12"')
                self.context.reset_context()
                self.context.space_next_word = False
                self.context.force_caps = False
            else:
                self.output.append_space_if_needed()
                self.input.capitalize_current_word()
                self.output.append_current_word()
                self.context.reset_context()
                self.context.space_next_word = True
                self.context.force_caps = False

        self.context.number = False
        return True

    def guess_sort_name(self, input_string: str) -> str:
        return self.move_article_to_end(input_string)
