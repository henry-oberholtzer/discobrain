"""
A Python port of the MusicBrainz `guess-case` module.

Original JavaScript implementation:
Copyright (C) 2005 Stefan Kestenholz (keschte)
Copyright (C) 2010-2024 MetaBrainz Foundation and contributors
Source: https://github.com/metabrainz/musicbrainz-server/tree/master/root/static/scripts/guess-case
Licensed under GPL-2.0-or-later.
"""

from __future__ import annotations

from .area_place import AreaHandler, PlaceHandler
from .artist import ArtistHandler
from .base import BaseHandler
from .label import LabelHandler
from .release import ReleaseHandler
from .simple import SimpleLowerHandler
from .track import TrackHandler
from .work import WorkHandler

HANDLER_MAP: dict[str, type[BaseHandler]] = {
    "area": AreaHandler,
    "artist": ArtistHandler,
    "event": WorkHandler,
    "genre": SimpleLowerHandler,
    "instrument": SimpleLowerHandler,
    "label": LabelHandler,
    "place": PlaceHandler,
    "recording": TrackHandler,
    "release": ReleaseHandler,
    "release_group": ReleaseHandler,
    "series": WorkHandler,
    "track": TrackHandler,
    "work": WorkHandler,
}


def get_handler_class(entity_name: str) -> type[BaseHandler]:
    return HANDLER_MAP.get(entity_name.lower(), TrackHandler)
