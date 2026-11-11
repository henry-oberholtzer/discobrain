from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .context import GuessCaseContext
from .modes import GuessCaseMode, get_mode
from .types import ModeName
from .utils import (
    is_apostrophe,
    is_lower_case_bracket_word,
    is_punctuation_char,
    is_sentence_stop_char,
)

if TYPE_CHECKING:
    from .stream import GuessCaseInput, GuessCaseOutput

CONTRACTIONS_RE = re.compile(r"^(?:all|ve|ll|cha|re|mon)$", flags=re.IGNORECASE)
COY_RE = re.compile(r"^[coy]$", flags=re.IGNORECASE)


def title_string(
    input_obj: GuessCaseInput,
    output_obj: GuessCaseOutput,
    input_string: str | None,
    mode_name: ModeName,
    context: GuessCaseContext,
    cfg_keep_uppercased: bool = True,
    roman: bool = False,
    force_caps: bool | None = None,
) -> str:
    if not input_string:
        return ""

    mode = get_mode(mode_name)
    local_force_caps = context.force_caps if force_caps is None else force_caps

    length = input_obj.get_length()
    pos = input_obj.get_cursor_position()

    if pos == length:
        pos = length - 1
        input_obj.set_cursor_position(pos)

    lowercase = mode.to_lower_case(input_string)
    uppercase = mode.to_upper_case(input_string)

    prev_word = input_obj.get_previous_word()
    next_word = input_obj.get_next_word()

    if (
        input_string == uppercase
        and len(input_string) > 1
        and cfg_keep_uppercased
    ):
        output_string = uppercase
    elif len(lowercase) == 1 and is_apostrophe(prev_word):
        # e.g. 's, 'd, 't -> keep lowercase
        output_string = lowercase
    elif (
        mode.name == "English"
        and is_apostrophe(prev_word)
        and CONTRACTIONS_RE.match(lowercase)
    ):
        # Y'all, They've, You'll, What'cha, You're, C'mon
        output_string = lowercase
    elif (
        mode.name == "English"
        and is_apostrophe(prev_word)
        and input_obj.get_word_at_index(pos - 2) == "Ev"
    ):
        # Ev'ry, Ev'rything
        output_string = lowercase
    elif (
        mode.name == "English"
        and COY_RE.match(lowercase)
        and is_apostrophe(next_word)
    ):
        # O'Titled, Y'All, C'mon
        output_string = uppercase
    else:
        output_string = title_string_by_mode(
            input_obj=input_obj,
            output_obj=output_obj,
            mode=mode,
            context=context,
            input_string=lowercase,
            force_caps=local_force_caps,
        )
        lowercase = mode.to_lower_case(output_string)
        uppercase = mode.to_upper_case(output_string)

        followed_by_punct = (
            bool(next_word)
            and len(next_word) == 1
            and is_punctuation_char(next_word)
        )
        followed_by_apostrophe = (
            bool(next_word)
            and len(next_word) == 1
            and is_apostrophe(next_word)
        )

        if (
            not local_force_caps
            and mode.is_lower_case_word(lowercase)
            and not followed_by_punct
        ):
            output_string = lowercase
        elif (
            mode.is_roman_numeral(lowercase, roman=roman)
            and not followed_by_apostrophe
            and not (
                context.is_inside_brackets()
                and is_lower_case_bracket_word(lowercase)
            )
        ) or mode.is_upper_case_word(lowercase):
            output_string = uppercase
        elif (
            context.is_inside_brackets()
            and is_lower_case_bracket_word(lowercase)
        ):
            output_string = lowercase

    return output_string


def title_string_by_mode(
    input_obj: GuessCaseInput,
    output_obj: GuessCaseOutput,
    mode: GuessCaseMode,
    context: GuessCaseContext,
    input_string: str | None,
    force_caps: bool,
) -> str:
    if not input_string:
        return ""

    output_string = mode.to_lower_case(input_string)

    opos = output_obj.get_length()
    word_before: str | None = ""
    if opos > 1:
        word_before = output_obj.get_word_at_index(opos - 2)

    do_caps = (
        force_caps
        or not mode.is_sentence_caps()
        or context.slurp_extra_title_information
        or context.opening_bracket
        or input_obj.is_first_word()
        or is_sentence_stop_char(word_before)
    )

    if do_caps:
        chars = list(output_string)
        chars[0] = mode.to_upper_case(chars[0])

        if len(output_string) > 2 and output_string.startswith("mc"):
            chars[2] = mode.to_upper_case(chars[2])

        output_string = "".join(chars)

    return output_string
