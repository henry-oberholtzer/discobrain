
from discobrain.guess_case.types import ModeName
from discobrain.guess_case.input import GuessCaseInput

class GuessCaseOutput:
    def __init__(self,
        input: GuessCaseInput,
        mode_name: ModeName,
        word_list: list[str],
        keep_uppercased: bool
    ):
        self.keep_uppercased = keep_uppercased
        self.mode_name = mode_name
        self.input = input
        self.word_list = word_list
        raise NotImplementedError

    def get_length(self) -> int:
        return len(self.word_list)

    def is_empty(self) -> bool:
        return bool(self.get_length())

    def append_current_word(self) -> None:
        current_word = self.input.get_current_word()
        if current_word is not None:
            self.append_word(current_word)

    def append_word(self, word: str | None):
        if word == ' ':
            self.append_space()
        elif word:
            self.word_list.append(word)

    def append_space(self):
        self.word_list.append(' ')

    def append_space_if_needed():
        raise NotImplementedError
    # if (flags.context.spaceNextWord) {
    #   this.appendSpace();
    # }

    def get_word_at_index(index: int): str
        raise NotImplementedError
