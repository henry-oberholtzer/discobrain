from dataclasses import dataclass, field

from .word_checker import BRACKET_PAIR_MAPPING, is_bracket_char


@dataclass
class GuessCaseContext:
    acronym: bool = False
    acronym_split: bool = False
    colon: bool = False
    ellipsis: bool = False
    force_caps: bool = False
    hyphen: bool = False
    number: bool = False
    number_split_char: str | None = None
    number_split_expect: bool = False
    open_brackets: list[str] = field(default_factory=list)
    opened_single_quote: bool = False
    opening_bracket: bool = False
    single_quote: bool = False
    slurp_extra_title_information: bool = False
    space_next_word: bool = False
    whitespace: bool = False

    def reset(self) -> None:
        self.acronym_split = False
        self.colon = False
        self.ellipsis = False
        self.hyphen = False
        self.opening_bracket = False
        self.single_quote = False
        self.whitespace = False

    def init(self) -> None:
        self.force_caps = True
        self.space_next_word = False
        self.open_brackets.clear()
        self.slurp_extra_title_information = False

        self.reset()

        self.acronym = False
        self.number = False
        self.opened_single_quote = False
        self.number_split_char = None
        self.number_split_expect = False

    @property
    def is_inside_brackets(self) -> bool:
        return bool(len(self.open_brackets))

    def push_bracket(self, bracket: str) -> None:
        self.open_brackets.append(bracket)

    def pop_bracket(self) -> str | None:
        cb = self.get_current_close_bracket()
        self.open_brackets.pop()
        return cb

    def get_corresponding_bracket(self, bracket: str) -> str:
        return BRACKET_PAIR_MAPPING[bracket] if is_bracket_char(bracket) else ''

    def get_current_close_bracket(self) -> str | None:
        open_bracket = self.open_brackets[-1]
        return open_bracket if self.get_corresponding_bracket(open_bracket) else None

