from __future__ import annotations

import re

from .constants import SPLITWORDSANDPUNCTUATION_REGEX
from .context import GuessCaseContext
from .types import ModeName
from .utils import is_lower_case_bracket_word, safe_index, trim


class GuessCaseInput:
    def __init__(
        self,
        input_string: str,
        mode_name: ModeName,
        context: GuessCaseContext,
        keep_uppercased: bool = True,
        roman: bool = False,
    ) -> None:
        self.source = input_string or ""
        self.mode_name = mode_name
        self.context = context
        self.keep_uppercased = keep_uppercased
        self.roman = roman
        self.word_list: list[str] = []
        self.word_index = 0
        self.output: GuessCaseOutput | None = None

    def init(self, word_list: list[str], output: GuessCaseOutput) -> None:
        self.output = output
        self.word_list = list(word_list)
        self.word_index = 0

    def get_length(self) -> int:
        return len(self.word_list)

    def is_empty(self) -> bool:
        return len(self.word_list) == 0

    def get_cursor_position(self) -> int:
        return self.word_index

    def set_cursor_position(self, index: int) -> None:
        if 0 <= index < self.get_length():
            self.word_index = index

    def get_word_at_index(self, index: int) -> str | None:
        return safe_index(self.word_list, index, None)

    def get_next_word(self) -> str | None:
        return self.get_word_at_index(self.word_index + 1)

    def get_current_word(self) -> str | None:
        return self.get_word_at_index(self.word_index)

    def get_previous_word(self) -> str | None:
        if self.word_index <= 0:
            return None
        return self.get_word_at_index(self.word_index - 1)

    def is_first_word(self) -> bool:
        return self.word_index == 0

    def is_last_word(self) -> bool:
        return self.word_index == self.get_length() - 1

    def has_more_words(self) -> bool:
        return (self.word_index == 0 and self.get_length() > 0) or (
            self.word_index < self.get_length() - 1
        )

    def is_next_word(self, word: str) -> bool:
        return self.has_more_words() and self.get_next_word() == word

    def is_previous_word(self, word: str) -> bool:
        return not self.is_first_word() and self.get_previous_word() == word

    def match_word_at_index(self, index: int, regex: re.Pattern[str] | str) -> bool:
        word = self.get_word_at_index(index)
        if word is None:
            return False
        if isinstance(regex, str):
            return word == regex
        return bool(regex.search(word))

    def match_current_word(self, regex: re.Pattern[str] | str) -> bool:
        return self.match_word_at_index(self.get_cursor_position(), regex)

    def is_index_at_end(self) -> bool:
        return self.word_index >= self.get_length()

    def next_index(self) -> None:
        self.word_index += 1

    def drop_last_word(self) -> None:
        if self.word_list:
            self.word_list.pop()
            if self.is_index_at_end():
                self.word_index -= 1

    def insert_words_at_index(self, index: int, new_words: list[str]) -> None:
        self.word_list = [
            *self.word_list[:index],
            *new_words,
            *self.word_list[index:],
        ]

    def update_current_word(self, word: str) -> None:
        if self.word_index < len(self.word_list):
            self.word_list[self.word_index] = word

    def capitalize_current_word(self) -> str | None:
        word = self.get_current_word()
        if word is None or self.output is None:
            return None
        from .title import title_string

        output = title_string(
            input_obj=self,
            output_obj=self.output,
            input_string=word,
            mode_name=self.mode_name,
            context=self.context,
            cfg_keep_uppercased=self.keep_uppercased,
            roman=self.roman,
        )
        if word != output:
            self.update_current_word(output)
        return output

    @staticmethod
    def split_words_and_punctuation(input_string: str) -> list[str]:
        # Compress whitespace
        cleaned = re.sub(r"^\s+", "", input_string)
        cleaned = re.sub(r"\s+$", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)

        split_words: list[str] = []
        word_chars: list[str] = []

        for ch in cleaned:
            if SPLITWORDSANDPUNCTUATION_REGEX.match(ch):
                word_chars.append(ch)
            else:
                if word_chars:
                    split_words.append("".join(word_chars))
                    word_chars = []
                split_words.append(ch)

        if word_chars:
            split_words.append("".join(word_chars))

        return split_words


class GuessCaseOutput:
    def __init__(
        self,
        input_obj: GuessCaseInput,
        mode_name: ModeName,
        context: GuessCaseContext,
        keep_uppercased: bool = True,
        roman: bool = False,
    ) -> None:
        self.input = input_obj
        self.mode_name = mode_name
        self.context = context
        self.keep_uppercased = keep_uppercased
        self.roman = roman
        self.word_list: list[str] = []

    def get_length(self) -> int:
        return len(self.word_list)

    def is_empty(self) -> bool:
        return len(self.word_list) == 0

    def append_word(self, word: str | None) -> None:
        if word == " ":
            self.append_space()
        elif word:
            self.word_list.append(word)

    def append_space(self) -> None:
        self.word_list.append(" ")

    def append_space_if_needed(self) -> None:
        if self.context.space_next_word:
            self.append_space()

    def append_current_word(self) -> None:
        curr = self.input.get_current_word()
        if curr is not None:
            self.append_word(curr)

    def get_word_at_index(self, index: int) -> str | None:
        return safe_index(self.word_list, index, None)

    def set_word_at_index(self, index: int, word: str) -> None:
        if 0 <= index < len(self.word_list):
            self.word_list[index] = word

    def get_last_word(self) -> str | None:
        if self.is_empty():
            return None
        return self.word_list[-1]

    def capitalize_word_at_index(
        self, index: int, override_caps: bool | None = None
    ) -> None:
        from .modes import get_mode
        from .title import title_string

        mode = get_mode(self.mode_name)
        force_caps = (
            self.context.force_caps if override_caps is None else override_caps
        )

        if (not mode.is_sentence_caps() or force_caps) and not self.is_empty():
            word = self.get_word_at_index(index)
            if word is not None and not re.match(r"^\w\..*", word):
                probe = trim(word.lower())

                if (
                    not force_caps
                    and self.context.is_inside_brackets()
                    and is_lower_case_bracket_word(probe)
                ) or not force_caps and mode.is_upper_case_word(probe):
                    pass
                else:
                    orig_pos = self.input.get_cursor_position()
                    pos = orig_pos - 1
                    while pos >= 0:
                        w = self.input.get_word_at_index(pos)
                        if w is None or trim(w.lower()) == probe:
                            break
                        pos -= 1
                    self.input.set_cursor_position(pos)
                    output = title_string(
                        input_obj=self.input,
                        output_obj=self,
                        input_string=word,
                        mode_name=self.mode_name,
                        context=self.context,
                        cfg_keep_uppercased=self.keep_uppercased,
                        roman=self.roman,
                        force_caps=force_caps,
                    )
                    self.input.set_cursor_position(orig_pos)
                    if word != output:
                        self.set_word_at_index(index, output)

    def capitalize_last_word(self, override_caps: bool | None = None) -> None:
        self.capitalize_word_at_index(self.get_length() - 1, override_caps)

    def close_open_brackets(self) -> None:
        parts: list[str] = []
        while self.context.is_inside_brackets():
            cb = self.context.pop_bracket()
            if cb:
                parts.append(cb)
        if parts:
            self.append_word("".join(parts))

    def get_output(self) -> str:
        from .modes import get_mode

        mode = get_mode(self.mode_name)
        self.context.force_caps = not mode.is_sentence_caps()
        self.capitalize_last_word()
        self.close_open_brackets()
        return trim("".join(self.word_list))

    def append_word_preserve_white_space(self, capitalize_last: bool) -> None:
        from .modes import get_mode

        mode = get_mode(self.mode_name)
        whitespace_before = self.input.is_previous_word(" ")
        whitespace_after = self.input.is_next_word(" ")

        if capitalize_last:
            self.capitalize_last_word(not mode.is_sentence_caps())

        if whitespace_before:
            self.append_space()

        self.append_current_word()
        self.context.space_next_word = whitespace_after
