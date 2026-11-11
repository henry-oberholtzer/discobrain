from __future__ import annotations

from .base import BaseHandler


class SimpleLowerHandler(BaseHandler):
    def process(self, input_string: str) -> str:
        return input_string.lower()

    def guess_sort_name(self, input_string: str) -> str:
        return input_string.lower()
