"""
A Python port of the MusicBrainz `guess-case` module.

Original JavaScript implementation:
Copyright (C) 2005 Stefan Kestenholz (keschte)
Copyright (C) 2010-2024 MetaBrainz Foundation and contributors
Source: https://github.com/metabrainz/musicbrainz-server/tree/master/root/static/scripts/guess-case
Licensed under GPL-2.0-or-later.
"""

from typing import Literal

ModeName = Literal["English", "French", "Sentence", "Turkish"]

EntityName = Literal[
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
