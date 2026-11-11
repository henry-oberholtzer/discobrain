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
from collections.abc import Callable

from ..constants import (
    NOT_A_SPECIALCASE,
    OPEN_BRACKETS,
    SPECIALCASE_CROWD_NOISE,
    SPECIALCASE_DATA_TRACK,
    SPECIALCASE_DIALOGUE,
    SPECIALCASE_GUITAR_SOLO,
    SPECIALCASE_SILENCE,
    SPECIALCASE_UNKNOWN,
    SPECIALCASE_UNTITLED,
    SPECIALCASES_REGEX,
)
from ..context import GuessCaseContext
from ..modes import GuessCaseMode, get_mode
from ..stream import GuessCaseInput, GuessCaseOutput
from ..types import ModeName
from ..utils import is_lower_case_bracket_word, trim

RE_LINESTOP = re.compile(r"[?!;]")
RE_HYPHEN = re.compile(r"^[-‐]$")
RE_INVERTEDMARKS = re.compile(r"^[¿¡]$")
RE_SLASH = re.compile(r"^[\\/]$")
RE_DOUBLEQUOTE = re.compile(r"^[\"“”„“«»]$")
RE_SINGLEQUOTE = re.compile(r"^['‘’‹›]$")
RE_OPENBRACKET = re.compile(r"^[([{<]$")
RE_CLOSEBRACKET = re.compile(r"^[)\]}>]$")
RE_ACRONYM = re.compile(r"^\w$")
RE_DIGITS = re.compile(r"^\d+$")
RE_DIGITS_NUMBERSPLIT = re.compile(r"^[,.]$")
RE_DIGITS_DUPLE = re.compile(r"^\d\d$")
RE_DIGITS_TRIPLE = re.compile(r"^\d\d\d$")
RE_DIGITS_NTUPLE = re.compile(r"^\d\d\d\d+$")
RE_FEAT = re.compile(r"^(?:featuring|f|ft|feat)$", flags=re.IGNORECASE)
RE_FEAT_F = re.compile(r"^f$", flags=re.IGNORECASE)
RE_FEAT_FEAT = re.compile(r"^feat$", flags=re.IGNORECASE)


class BaseHandler:
    def __init__(
        self,
        mode_name: ModeName,
        input_obj: GuessCaseInput,
        output_obj: GuessCaseOutput,
        context: GuessCaseContext,
    ) -> None:
        self.mode_name = mode_name
        self.input = input_obj
        self.output = output_obj
        self.context = context

    @property
    def mode(self) -> GuessCaseMode:
        return get_mode(self.mode_name)

    def check_special_case(self, input_string: str | None = None) -> int:
        return NOT_A_SPECIALCASE

    def is_special_case(self, number: int) -> bool:
        return number != NOT_A_SPECIALCASE

    def get_special_case_formatted(self, input_string: str, number: int) -> str:
        if number == SPECIALCASE_DATA_TRACK:
            return "[data track]"
        if number == SPECIALCASE_SILENCE:
            return "[silence]"
        if number == SPECIALCASE_UNTITLED:
            return "[untitled]"
        if number == SPECIALCASE_UNKNOWN:
            return "[unknown]"
        if number == SPECIALCASE_CROWD_NOISE:
            return "[crowd noise]"
        if number == SPECIALCASE_GUITAR_SOLO:
            return "[guitar solo]"
        if number == SPECIALCASE_DIALOGUE:
            return "[dialogue]"
        return input_string

    def get_words_for_processing(self, input_string: str) -> list[str]:
        return self.input.split_words_and_punctuation(input_string)

    def process(self, input_string: str) -> str:
        words = self.get_words_for_processing(input_string)
        self.input.init(words, self.output)
        while not self.input.is_index_at_end():
            self.process_word()
        return self.mode.run_post_process(self.output.get_output())

    def process_word(self) -> None:
        if not self.do_white_space():
            handled = False
            if self.input.match_current_word(SPECIALCASES_REGEX):
                handled = (
                    self.do_double_quote()
                    or self.do_single_quote()
                    or self.do_opening_bracket()
                    or self.do_closing_bracket()
                    or self.do_comma()
                    or self.do_period()
                    or self.do_line_stop()
                    or self.do_ampersand()
                    or self.do_slash()
                    or self.do_colon()
                    or self.do_hyphen()
                    or self.do_inverted_marks()
                    or self.do_plus()
                    or self.do_asterisk()
                    or self.do_diamond()
                    or self.do_percent()
                )

            if not handled:
                _ = self.do_digits() or self.do_acronym() or self.do_word()

        self.input.next_index()

    def do_word(self) -> bool:
        return True

    def do_normal_word(self) -> None:
        self.output.append_space_if_needed()
        self.input.capitalize_current_word()
        self.output.append_current_word()
        self.context.reset_context()
        self.context.force_caps = False
        self.context.space_next_word = True

    def do_white_space(self) -> bool:
        if self.input.match_current_word(" "):
            self.context.whitespace = True
            self.context.space_next_word = True
            if self.context.opening_bracket:
                self.context.space_next_word = False
            return True
        return False

    def do_colon(self) -> bool:
        if self.input.match_current_word(":"):
            feat_index = self.output.get_length() - 3
            role = self.output.get_last_word()
            if (
                self.context.slurp_extra_title_information
                and feat_index > 0
                and self.output.get_word_at_index(feat_index) == "feat."
                and role
            ):
                self.output.set_word_at_index(
                    self.output.get_length() - 1, role.lower()
                )
            else:
                self.output.capitalize_last_word(
                    not self.mode.is_sentence_caps()
                )

            skip = False
            cursor_pos = self.input.get_cursor_position()
            length = self.input.get_length()
            if cursor_pos < length - 2:
                next_word = self.input.get_word_at_index(cursor_pos + 1)
                after_next = self.input.get_word_at_index(cursor_pos + 2)
                if next_word and next_word in OPEN_BRACKETS:
                    skip = True
                    self.context.space_next_word = True
                elif (
                    self.input.is_next_word(" ")
                    and after_next
                    and after_next in OPEN_BRACKETS
                ):
                    skip = True
                    self.context.space_next_word = True
                    self.input.next_index()

            if not skip:
                self.output.append_current_word()
                self.context.reset_context()
                self.context.force_caps = True
                self.context.colon = True
                self.context.space_next_word = self.input.is_next_word(" ")

            return True
        return False

    def do_asterisk(self) -> bool:
        if self.input.match_current_word("*"):
            self.output.append_word_preserve_white_space(True)
            self.context.reset_context()
            return True
        return False

    def do_diamond(self) -> bool:
        if self.input.match_current_word("#"):
            self.output.append_word_preserve_white_space(True)
            self.context.reset_context()
            return True
        return False

    def do_percent(self) -> bool:
        if self.input.match_current_word("%"):
            self.output.append_word_preserve_white_space(True)
            self.context.reset_context()
            return True
        return False

    def do_ampersand(self) -> bool:
        if self.input.match_current_word("&"):
            self.context.reset_context()
            self.context.force_caps = True
            self.output.append_space()
            self.context.space_next_word = True
            self.output.append_current_word()
            return True
        return False

    def do_line_stop(self) -> bool:
        if self.input.match_current_word(RE_LINESTOP):
            self.context.reset_context()
            self.output.capitalize_last_word(not self.mode.is_sentence_caps())
            self.context.force_caps = True
            self.context.space_next_word = True
            self.output.append_current_word()
            return True
        return False

    def do_hyphen(self) -> bool:
        if self.input.match_current_word(RE_HYPHEN):
            self.output.append_word_preserve_white_space(True)
            self.context.reset_context()
            self.context.force_caps = not self.mode.is_sentence_caps()
            self.context.hyphen = True
            return True
        return False

    def do_inverted_marks(self) -> bool:
        if self.input.match_current_word(RE_INVERTEDMARKS):
            self.output.append_word_preserve_white_space(False)
            self.context.reset_context()
            self.context.force_caps = True
            return True
        return False

    def do_plus(self) -> bool:
        if self.input.match_current_word("+"):
            self.output.append_word_preserve_white_space(True)
            self.context.reset_context()
            return True
        return False

    def do_slash(self) -> bool:
        if self.input.match_current_word(RE_SLASH):
            self.output.append_word_preserve_white_space(True)
            self.context.reset_context()
            self.context.force_caps = True
            return True
        return False

    def do_double_quote(self) -> bool:
        if self.input.match_current_word(RE_DOUBLEQUOTE):
            self.output.append_word_preserve_white_space(False)
            self.context.reset_context()
            self.context.force_caps = not self.input.is_next_word(" ")
            return True
        return False

    def do_single_quote(self) -> bool:
        if self.input.match_current_word(RE_SINGLEQUOTE):
            self.context.force_caps = False
            is_prev_space = self.input.is_previous_word(" ")
            is_next_space = self.input.is_next_word(" ")
            state = self.context.opened_single_quote

            if is_prev_space and not is_next_space:
                self.output.append_space()
                self.context.opened_single_quote = True
                self.context.force_caps = True
            elif not is_prev_space and is_next_space:
                if state:
                    self.context.force_caps = True
                    self.context.opened_single_quote = False
                self.output.capitalize_last_word()

            self.context.space_next_word = is_next_space
            self.output.append_current_word()
            self.context.reset_context()
            if state == self.context.opened_single_quote:
                self.context.force_caps = False
            self.context.single_quote = True
            return True
        return False

    def do_opening_bracket(self) -> bool:
        curr = self.input.get_current_word()
        if curr and RE_OPENBRACKET.match(curr):
            self.output.capitalize_last_word(not self.mode.is_sentence_caps())
            self.context.push_bracket(curr)
            closing_b = self.context.get_current_close_bracket()
            force_lowercase = False
            cursor_pos = self.input.get_cursor_position() + 1
            for i in range(cursor_pos, self.input.get_length()):
                w = self.input.get_word_at_index(i) or ""
                if w != " ":
                    if is_lower_case_bracket_word(w) or re.match(
                        r"^(?:featuring|ft|feat)$", w, flags=re.IGNORECASE
                    ):
                        self.context.slurp_extra_title_information = True
                        if i == cursor_pos:
                            force_lowercase = True
                    if w == closing_b:
                        break

            self.output.append_space()
            self.context.reset_context()
            self.context.space_next_word = False
            self.context.opening_bracket = True
            self.context.force_caps = not force_lowercase
            self.output.append_current_word()
            return True
        return False

    def do_closing_bracket(self) -> bool:
        if self.input.match_current_word(RE_CLOSEBRACKET):
            self.output.capitalize_last_word()
            if self.context.is_inside_brackets():
                self.context.pop_bracket()
                self.context.slurp_extra_title_information = False
            self.context.reset_context()
            self.context.force_caps = not self.mode.is_sentence_caps()
            self.context.space_next_word = True
            self.output.append_current_word()
            return True
        return False

    def do_comma(self) -> bool:
        if self.input.match_current_word(","):
            if self.output.get_last_word() != ",":
                self.context.reset_context()
                self.context.space_next_word = True
                self.context.force_caps = False
                self.output.append_current_word()
            return True
        return False

    def do_period(self) -> bool:
        if self.input.match_current_word("."):
            if self.output.get_last_word() == ".":
                if not self.context.ellipsis:
                    self.output.append_word("..")
                    while self.input.is_next_word("."):
                        self.input.next_index()
                    self.context.reset_context()
                    self.context.ellipsis = True
                self.context.force_caps = True
                self.context.space_next_word = True
            else:
                if (
                    not self.input.has_more_words()
                    or self.input.get_next_word() != "."
                ):
                    self.output.capitalize_last_word()
                self.output.append_word(".")
                self.context.reset_context()
                self.context.force_caps = True
                self.context.space_next_word = self.input.is_next_word(" ")
            return True
        return False

    def do_acronym(self) -> bool:
        curr = self.input.get_current_word()
        if not curr or not RE_ACRONYM.match(curr):
            return False

        sub_index = self.input.get_cursor_position() + 1
        tmp: list[str] = [curr.upper()]
        expect_word = False
        got_period = False

        while sub_index < self.input.get_length():
            word = self.input.get_word_at_index(sub_index)
            if expect_word and word and RE_ACRONYM.match(word):
                tmp.append(word.upper())
                expect_word = False
                got_period = False
            else:
                if word == "." and not got_period:
                    tmp.append(".")
                    got_period = True
                    expect_word = True
                elif got_period and word == " ":
                    expect_word = True
                elif tmp and tmp[-1] != ".":
                    tmp.pop()
                    sub_index -= 1
                    break
                else:
                    break
            sub_index += 1

        if len(tmp) > 2:
            s = "".join(tmp)
            s = s.rstrip(".") + "."
            self.output.append_space_if_needed()
            self.output.append_word(s)
            self.context.reset_context()
            self.context.acronym = True
            self.context.space_next_word = True
            self.context.force_caps = False
            self.input.set_cursor_position(sub_index - 1)
            return True

        return False

    def do_digits(self) -> bool:
        curr = self.input.get_current_word()
        if not curr or not RE_DIGITS.match(curr):
            return False

        sub_index = self.input.get_cursor_position() + 1
        tmp: list[str] = [curr]
        self.context.number_split_expect = True

        while sub_index < self.input.get_length():
            if self.context.number_split_expect:
                if self.input.match_word_at_index(
                    sub_index, RE_DIGITS_NUMBERSPLIT
                ):
                    w = self.input.get_word_at_index(sub_index)
                    if w:
                        tmp.append(w)
                    self.context.number_split_expect = False
                else:
                    break
            elif self.input.match_word_at_index(sub_index, RE_DIGITS_TRIPLE):
                if self.context.number_split_char is None and len(tmp) > 1:
                    self.context.number_split_char = tmp[-1]
                w = self.input.get_word_at_index(sub_index)
                if w:
                    tmp.append(w)
                self.context.number_split_expect = True
            else:
                if self.input.match_word_at_index(sub_index, RE_DIGITS_DUPLE):
                    if (
                        len(tmp) > 2
                        and self.context.number_split_char != tmp[-1]
                    ):
                        w = self.input.get_word_at_index(sub_index)
                        if w:
                            tmp.append(w)
                        sub_index += 1
                    else:
                        tmp.pop()
                        sub_index -= 1
                elif self.input.match_word_at_index(
                    sub_index, RE_DIGITS_NTUPLE
                ):
                    w = self.input.get_word_at_index(sub_index)
                    if w:
                        tmp.append(w)
                    sub_index += 1
                else:
                    tmp.pop()
                    sub_index -= 1
                break
            sub_index += 1

        self.input.set_cursor_position(sub_index - 1)
        self.output.append_space_if_needed()
        self.output.append_word("".join(tmp))
        self.context.reset_context()
        self.context.force_caps = False
        self.context.number = True
        return True

    def do_ignore_words(self) -> bool:
        if self.input.get_current_word() == "dB":
            self.output.append_space_if_needed()
            self.output.append_current_word()
            return True
        return False

    def do_featuring_artist_style(self) -> bool:
        curr = self.input.get_current_word()
        if not curr or not RE_FEAT.match(curr):
            return False

        next_w = self.input.get_next_word()
        if RE_FEAT_F.match(curr) and (not next_w or next_w not in (".", "/")):
            return False

        if self.input.get_cursor_position() < self.input.get_length() - 2:
            feat_word = curr + (
                next_w
                if (next_w and next_w in (".", "/"))
                else ("." if RE_FEAT_FEAT.match(curr) else "")
            )

            if (
                not self.context.opening_bracket
                and not self.context.is_inside_brackets()
            ):
                cursor_pos = self.input.get_cursor_position()
                length = self.input.get_length()
                i = cursor_pos
                while i < length:
                    if self.input.get_word_at_index(i) == "(":
                        break
                    i += 1

                if i != cursor_pos and i < length - 1:
                    self.input.insert_words_at_index(i, [")", " "])

                self.input.update_current_word("(")
                self.do_opening_bracket()
            else:
                self.output.append_word(" ")

            self.output.append_word(feat_word)
            self.context.reset_context()
            self.context.force_caps = True
            self.context.opening_bracket = False
            self.context.space_next_word = True
            self.context.slurp_extra_title_information = True

            if self.input.is_next_word(".") or self.input.is_next_word("/"):
                self.input.next_index()
            return True

        return False

    def move_article_to_end(self, input_string: str) -> str:
        def repl(match: re.Match[str]) -> str:
            return f"{match.group(2)}, {match.group(1)}"

        return re.sub(
            r"^(The|Los) (.+)$", repl, trim(input_string), flags=re.IGNORECASE
        )

    def guess_sort_name(self, input_string: str) -> str:
        return self.move_article_to_end(input_string)

    def sort_compound_name(
        self, input_string: str, callback: Callable[[str], str]
    ) -> str:
        trimmed = trim(input_string)
        join_phrase = " and "
        if " + " in trimmed:
            join_phrase = " + "
        elif " & " in trimmed:
            join_phrase = " & "

        parts = trimmed.split(join_phrase)
        processed = [callback(part) for part in parts]
        return join_phrase.join(processed)
