from __future__ import annotations

from .context import GuessCaseContext
from .handlers import get_handler_class
from .handlers.artist import ArtistHandler
from .stream import GuessCaseInput, GuessCaseOutput
from .types import EntityName, ModeName


def guess_case(
    text: str,
    entity: str = "track",
    mode: str | ModeName = "English",
    keep_uppercased: bool = True,
    roman: bool = False,
) -> str:
    """Guess the casing of an entity title/name according to MusicBrainz style rules."""
    context = GuessCaseContext()
    context.init()

    mode_name: ModeName = mode if mode in ("English", "French", "Sentence", "Turkish") else "English"  # type: ignore

    input_obj = GuessCaseInput(
        input_string=text,
        mode_name=mode_name,
        context=context,
        keep_uppercased=keep_uppercased,
        roman=roman,
    )
    output_obj = GuessCaseOutput(
        input_obj=input_obj,
        mode_name=mode_name,
        context=context,
        keep_uppercased=keep_uppercased,
        roman=roman,
    )
    handler_cls = get_handler_class(entity)
    handler = handler_cls(
        mode_name=mode_name,
        input_obj=input_obj,
        output_obj=output_obj,
        context=context,
    )

    num = handler.check_special_case(text)
    if handler.is_special_case(num):
        return handler.get_special_case_formatted(text, num)

    return handler.process(text)


def guess_sort_name(
    text: str,
    entity: str = "artist",
    is_person: bool = False,
    mode: str | ModeName = "English",
) -> str:
    """Guess the sort name of an entity (e.g. artist, label, release)."""
    context = GuessCaseContext()
    context.init()

    mode_name: ModeName = mode if mode in ("English", "French", "Sentence", "Turkish") else "English"  # type: ignore

    input_obj = GuessCaseInput(
        input_string=text,
        mode_name=mode_name,
        context=context,
    )
    output_obj = GuessCaseOutput(
        input_obj=input_obj,
        mode_name=mode_name,
        context=context,
    )
    handler_cls = get_handler_class(entity)
    handler = handler_cls(
        mode_name=mode_name,
        input_obj=input_obj,
        output_obj=output_obj,
        context=context,
    )

    if isinstance(handler, ArtistHandler):
        return handler.guess_sort_name(text, is_person=is_person)
    return handler.guess_sort_name(text)


class _EntityProxy:
    def __init__(self, gc: GuessCase, entity: str) -> None:
        self.gc = gc
        self.entity = entity

    def guess(self, text: str) -> str:
        return guess_case(
            text=text,
            entity=self.entity,
            mode=self.gc.mode_name,
            keep_uppercased=self.gc.keep_uppercased,
            roman=self.gc.roman,
        )

    def sortname(self, text: str, is_person: bool = False) -> str:
        return guess_sort_name(
            text=text,
            entity=self.entity,
            is_person=is_person,
            mode=self.gc.mode_name,
        )


class GuessCase:
    def __init__(
        self,
        mode_name: str | ModeName = "English",
        keep_uppercased: bool = True,
        roman: bool = False,
    ) -> None:
        self.mode_name = mode_name
        self.keep_uppercased = keep_uppercased
        self.roman = roman

    @property
    def entities(self) -> dict[str, _EntityProxy]:
        entities_list = [
            "area",
            "artist",
            "event",
            "genre",
            "instrument",
            "label",
            "place",
            "recording",
            "release",
            "release_group",
            "series",
            "track",
            "work",
        ]
        return {name: _EntityProxy(self, name) for name in entities_list}


__all__ = [
    "EntityName",
    "GuessCase",
    "ModeName",
    "guess_case",
    "guess_sort_name",
]
