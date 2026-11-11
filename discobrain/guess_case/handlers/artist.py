from __future__ import annotations

import re

from ..constants import NOT_A_SPECIALCASE, SPECIALCASE_UNKNOWN
from ..utils import trim
from .base import BaseHandler

RE_ARTIST_EMPTY = re.compile(r"^\s*$", flags=re.IGNORECASE)
RE_ARTIST_UNKNOWN = re.compile(
    r"^[(\[]?\s*Unknown\s*[)\]]?$", flags=re.IGNORECASE
)
RE_ARTIST_NONE = re.compile(r"^[(\[]?\s*none\s*[)\]]?$", flags=re.IGNORECASE)
RE_ARTIST_NOARTIST = re.compile(
    r"^[(\[]?\s*no[\s-]+artist\s*[)\]]?$", flags=re.IGNORECASE
)
RE_ARTIST_NOTAPPLICABLE = re.compile(
    r"^[(\[]?\s*not[\s-]+applicable\s*[)\]]?$", flags=re.IGNORECASE
)
RE_ARTIST_NA = re.compile(
    r"^[(\[]?\s*n\s*[\\/]\s*a\s*[)\]]?$", flags=re.IGNORECASE
)

RE_SORTNAME_SR = re.compile(r",\s*Sr\.?$", flags=re.IGNORECASE)
RE_SORTNAME_JR = re.compile(r",\s*Jr\.?$", flags=re.IGNORECASE)

RE_SORTNAME_DJ = re.compile(r"^DJ$", flags=re.IGNORECASE)
RE_SORTNAME_THE = re.compile(r"^The$", flags=re.IGNORECASE)
RE_SORTNAME_LOS = re.compile(r"^Los$", flags=re.IGNORECASE)
RE_SORTNAME_DR = re.compile(r"^Dr\.$", flags=re.IGNORECASE)


class ArtistHandler(BaseHandler):
    def check_special_case(self, input_string: str | None = None) -> int:
        if input_string is None:
            return NOT_A_SPECIALCASE
        if (
            RE_ARTIST_EMPTY.match(input_string)
            or RE_ARTIST_UNKNOWN.match(input_string)
            or RE_ARTIST_NONE.match(input_string)
            or RE_ARTIST_NOARTIST.match(input_string)
            or RE_ARTIST_NOTAPPLICABLE.match(input_string)
            or RE_ARTIST_NA.match(input_string)
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

    def guess_sort_name(
        self, input_string: str, is_person: bool = False
    ) -> str:
        def callback(artist_name: str) -> str:
            if not artist_name:
                return ""
            modified = trim(artist_name)
            append = ""

            if RE_SORTNAME_SR.search(modified):
                modified = RE_SORTNAME_SR.sub("", modified)
                append = ", Sr."
            elif RE_SORTNAME_JR.search(modified):
                modified = RE_SORTNAME_JR.sub("", modified)
                append = ", Jr."

            names = modified.split(" ")
            if not names or not names[0]:
                return ""

            reorder = False
            first_name = names[0]

            if RE_SORTNAME_DJ.match(first_name):
                append = f", DJ{append}"
                names.pop(0)
            elif RE_SORTNAME_THE.match(first_name):
                append = f", The{append}"
                names.pop(0)
            elif RE_SORTNAME_LOS.match(first_name):
                append = f", Los{append}"
                names.pop(0)
            elif RE_SORTNAME_DR.match(first_name):
                append = f", Dr.{append}"
                names.pop(0)
                reorder = True
            else:
                reorder = True

            if not is_person:
                reorder = False

            if reorder and len(names) > 1:
                reordered: list[str] = [""] * len(names)
                for i in range(len(names) - 1):
                    if i == len(names) - 2 and names[i] == "St.":
                        names[i + 1] = f"{names[i]} {names[i + 1]}"
                    elif names[i]:
                        reordered[i + 1] = names[i]

                reordered[0] = names[-1]
                if len(reordered) > 1:
                    reordered[0] += ","
                names = [n for n in reordered if n]

            filtered_names = " ".join(n for n in names if n)
            return trim(f"{filtered_names}{append}")

        return self.sort_compound_name(input_string, callback)
