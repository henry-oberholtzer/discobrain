from dataclasses import dataclass, field

from .constants import BRACKET_PAIR_MAPPING


@dataclass
class GuessCaseContext:
    force_caps: bool = True
    space_next_word: bool = False
    open_brackets: list[str] = field(default_factory=list)
    slurp_extra_title_information: bool = False

    acronym: bool = False
    acronym_split: bool = False
    colon: bool = False
    ellipsis: bool = False
    hyphen: bool = False
    number: bool = False
    number_split_char: str | None = None
    number_split_expect: bool = False
    opened_single_quote: bool = False
    opening_bracket: bool = False
    single_quote: bool = False
    whitespace: bool = False

    def reset_context(self) -> None:
        """Reset temporary per-word flags."""
        self.acronym_split = False
        self.colon = False
        self.ellipsis = False
        self.hyphen = False
        self.opening_bracket = False
        self.single_quote = False
        self.whitespace = False

    def init(self) -> None:
        """Initialise flags for a run."""
        self.force_caps = True
        self.space_next_word = False
        self.open_brackets.clear()
        self.slurp_extra_title_information = False

        self.reset_context()

        self.acronym = False
        self.number = False
        self.opened_single_quote = False
        self.number_split_char = None
        self.number_split_expect = False

    def is_inside_brackets(self) -> bool:
        return len(self.open_brackets) > 0

    def push_bracket(self, bracket: str) -> None:
        self.open_brackets.append(bracket)

    def pop_bracket(self) -> str | None:
        close_b = self.get_current_close_bracket()
        if self.open_brackets:
            self.open_brackets.pop()
        return close_b

    def get_current_close_bracket(self) -> str | None:
        if not self.open_brackets:
            return None
        open_b = self.open_brackets[-1]
        return BRACKET_PAIR_MAPPING.get(open_b)
