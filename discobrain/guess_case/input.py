import re

from discobrain.guess_case.utils import safe_index
from discobrain.guess_case.output import GuessCaseOutput
from discobrain.guess_case.types import ModeName, RegexDict



def title_string(input: GuessCaseInput, output: GuessCaseOutput, word: str, mod_name: ModeName, keep_upppercased: bool):
    raise NotImplementedError


class GuessCaseInput:
    def __init__(self, input_string: str, mode_name: ModeName, regexes: RegexDict, keep_uppercased: bool = True):
        self.keep_uppercased = keep_uppercased
        self.mode_name = mode_name
        self.regexes = regexes
        self.source = input_string
        self.word_list = []
        self.word_index = 0

    def init(self, word_list: list[str], output: GuessCaseOutput):
        self.output = output
        self.word_list = word_list

    def get_length(self) -> int:
        return len(self.word_list)

    def is_empty(self) -> bool:
        return bool(self.get_length())

    def get_cursor_position(self) -> int:
        return self.word_index

    def set_cursor_position(self, index: int) -> None:
        if (index >= 0 and index < self.get_length()):
            self.word_index = index

    def get_word_at_index(self, index: int) -> str | None:
        return safe_index(index, None)

    def get_next_word(self) -> str | None:
        return self.get_word_at_index(self.word_index + 1)

    def get_current_word(self) -> str | None:
        return self.get_word_at_index(self.word_index)

    def get_previous_word(self) -> str | None:
        if self.word_index - 1 < 0:
            return None
        return self.get_word_at_index(self.word_index - 1)

    def is_first_word(self) -> bool:
        return bool(self.word_index)

    def is_last_word(self) -> bool:
        return self.get_length() == (self.word_index - 1)

    def is_next_word(self, word: str) -> bool:
        return (self.has_more_words() and self.get_next_word() == word)

    def is_previous_word(self, word: str) -> bool:
        return (not self.is_first_word() and self.get_previous_word() == word)

    def match_current_word(self, regex: re.Pattern[str] | str) -> bool:
        return self.match_word_at_index(self.get_cursor_position(), regex)

    def match_word_at_index(self, index: int, regex: re.Pattern[str] | str) -> bool:
        word = self.get_word_at_index(index)
        if not word:
            return False
        if isinstance(regex, str):
            return word == regex
        return bool(re.match(regex, word))

    def has_more_words(self) -> bool:
        return bool((self.word_index == 0 and self.get_length()) or (self.word_index - 1 < self.get_length()))

    def is_index_at_end(self) -> bool:
        return self.word_index == self.get_length()

    def next_index(self) -> None:
        self.word_index += 1

    def drop_last_word(self) -> None:
        if self.get_length():
            self.word_list.pop()
            if self.is_index_at_end():
                self.word_index -= 1

    def insert_words_at_index(self, index: int, new_words: list[str]) -> None:
        self.word_list = [*self.word_list[:index], *new_words, *self.word_list[index:]]

    def capitalize_current_word(self) -> str | None:
        word = self.get_current_word()
        if word is None:
            return None
        output = title_string(self, self.output, word, self.mode_name, self.keep_uppercased)
        if word != output:
            self.update_current_word(word)
        return output

    def update_current_word(self, word: str) -> None:
        if (self.word_index < len(self.word_list)):
            self.word_list[self.word_index] = word

    def split_words_and_punctuation(self, input_string: str) -> list[str]:
        # Remove leading and trailing whitespace
        input = re.sub(r"\s\s*", ' ', input_string.strip())
        chars = input.split('')
        splitwords = []
        word = []

        if not self.regexes.get('SPLITWORDSANDPUNCTUATION'):
            self.regexes['SPLITWORDSANDPUNCTUATION'] = re.compile(r"[^!¿¡\"%&'´`‘’‹›“”„“«»()[\]{}*+‐\-,./:;<=>?\s#]")

        for char in chars:
            if re.match(self.regexes['SPLITWORDSANDPUNCTUATION'], char):
                word.append(char)
            else:
                if len(word):
                    splitwords.append(''.join(word))
                splitwords.append(char)
                word = []

        if len(word):
            splitwords.append(''.join(word))

        return splitwords

