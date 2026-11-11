"""
A Python port of the MusicBrainz `guess-case` module.

Original JavaScript implementation:
Copyright (C) 2005 Stefan Kestenholz (keschte)
Copyright (C) 2010-2024 MetaBrainz Foundation and contributors
Source: https://github.com/metabrainz/musicbrainz-server/tree/master/root/static/scripts/guess-case
Licensed under GPL-2.0-or-later.
"""

from __future__ import annotations

from .base import BaseHandler


class SimpleLowerHandler(BaseHandler):
    def process(self, input_string: str) -> str:
        return input_string.lower()

    def guess_sort_name(self, input_string: str) -> str:
        return input_string.lower()
