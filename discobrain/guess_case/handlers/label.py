from __future__ import annotations

import re

from ..constants import NOT_A_SPECIALCASE, SPECIALCASE_UNKNOWN
from .base import BaseHandler

RE_LABEL_EMPTY = re.compile(r"^\s*$", flags=re.IGNORECASE)
RE_LABEL_UNKNOWN = re.compile(
    r"^[(\[]?\s*Unknown\s*[)\]]?$", flags=re.IGNORECASE
)
RE_LABEL_NONE = re.compile(r"^[(\[]?\s*none\s*[)\]]?$", flags=re.IGNORECASE)
RE_LABEL_NOLABEL = re.compile(
    r"^[(\[]?\s*no[\s-]+label\s*[)\]]?$", flags=re.IGNORECASE
)
RE_LABEL_NOTAPPLICABLE = re.compile(
    r"^[(\[]?\s*not[\s-]+applicable\s*[)\]]?$", flags=re.IGNORECASE
)
RE_LABEL_NA = re.compile(
    r"^[(\[]?\s*n\s*[\\/]\s*a\s*[)\]]?$", flags=re.IGNORECASE
)


class LabelHandler(BaseHandler):
    def check_special_case(self, input_string: str | None = None) -> int:
        if input_string is None:
            return NOT_A_SPECIALCASE
        if (
            RE_LABEL_EMPTY.match(input_string)
            or RE_LABEL_UNKNOWN.match(input_string)
            or RE_LABEL_NONE.match(input_string)
            or RE_LABEL_NOLABEL.match(input_string)
            or RE_LABEL_NOTAPPLICABLE.match(input_string)
            or RE_LABEL_NA.match(input_string)
        ):
            return SPECIALCASE_UNKNOWN
        return NOT_A_SPECIALCASE

    def do_word(self) -> bool:
        self.output.append_space_if_needed()
        self.input.capitalize_current_word()
        self.output.append_current_word()
        self.context.reset_context()
        self.context.number = False
        self.context.force_caps = False
        self.context.space_next_word = True
        return True

    def guess_sort_name(self, input_string: str) -> str:
        return self.sort_compound_name(input_string, self.move_article_to_end)
