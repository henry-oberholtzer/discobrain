from __future__ import annotations

from ..utils import trim
from .base import BaseHandler


class AreaHandler(BaseHandler):
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
        return trim(input_string)


class PlaceHandler(BaseHandler):
    def do_word(self) -> bool:
        _ = (
            self.do_ignore_words()
            or self.mode.do_word()
            or self.do_normal_word()
        )
        self.context.number = False
        return True

    def guess_sort_name(self, input_string: str) -> str:
        return self.sort_compound_name(input_string, self.move_article_to_end)
