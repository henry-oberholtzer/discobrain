# Implementation of
# https://musicbrainz.org/doc/Development/Seeding/Release_Editor

import dataclasses
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import ClassVar

from isocodes import countries


def mb_dict_factory(data: MutableMapping, parent_key: str = '', sep: str = '.'):
    items: list[tuple[str, int | str]] = []
    for key, value in data.items():
        flat_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(mb_dict_factory(data=value, parent_key=flat_key).items())
        if isinstance(value, (str, int)):
            items.append((flat_key, value))
        if isinstance(value, list):
            if isinstance(value[0], MutableMapping):
                for idx, iterable_value in enumerate(value):
                    idx_key = f"{flat_key}{sep}{idx}"
                    items.extend(mb_dict_factory(iterable_value, parent_key=idx_key).items())
            else:
                for idx, iterable_value in enumerate(value):
                    idx_key = f"{flat_key}{sep}{idx}"
                    items.append((idx_key, iterable_value))
    return dict(items)

def mb_title_case(text: str) -> str:
    return text.replace(" The ", " the ")

@dataclass
class MBBase:
    TITLE_FIELDS: ClassVar[list[str]] = ["name"]
    COUNTRY_FIELDS: ClassVar[list[str]] = ["country"]

    def flatten(self) -> dict[str, int | str]:
        return mb_dict_factory(dataclasses.asdict(self))

    def __setattr__(self, prop: str, val: str | int):
        """
        Manages necessary transformations to make this into "Good" MusicBrainz data.
        """
        if isinstance(val, str):
            if prop in self.TITLE_FIELDS:
                return super().__setattr__(prop, mb_title_case(val))
            # Normalize country names to ISO names
            elif prop in self.COUNTRY_FIELDS:
                result = countries.by_name_dict[val]
                if result:
                    return super().__setattr__(prop, result.alpha_2)
        super().__setattr__(prop, val)


@dataclass
class MBArtistName(MBBase):
    name: str | None = None

@dataclass
class MBName(MBBase):
    mbid: str | None = None
    name: str | None = None
    artist: MBArtistName | None = None
    join_phrase: str | None = None

@dataclass
class MBArtistCredit(MBBase):
    names: list[MBName]

@dataclass
class MBTrack(MBBase):
    name: str | None = None
    number: str | None = None
    # MBID
    recording: str | None = None
    length: int | None = None
    artist_credit: MBArtistCredit | None = None

@dataclass
class MBMedium(MBBase):
    format: str | None = None
    name: str | None = None
    track: list[MBTrack] | None = None

@dataclass
class MBLabel(MBBase):
    mbid: str
    catalog_number: str
    name: str

@dataclass
class MBDate(MBBase):
    year: int | None = None
    month: int | None = None
    day: int | None = None

@dataclass
class MBEvent(MBBase):
    date: MBDate | None = None
    # any ISO code
    country: str | None = None

@dataclass
class MBURL(MBBase):
    url: str | None = None
    link_type: int | None = None

@dataclass
class MBRelease(MBBase):
    """
    Takes a given data source URL on init,
    then fetches and converts it to a relevant MusicBrainz
    new release format.
    """
    # non optional
    name: str
    # URL for getting source data
    urls: list[MBURL] | None = None
    # can be pre-existing MBID release group
    release_group: str | None = None
    # type of release group
    type: str | None = None
    # disambiguation comment, use for White Label, etc
    comment: str | None = None
    # annotation, use for multi-line text, e.g. other info on discogs
    annotation: str | None = None
    barcode: str | None = None
    # ISO-639-3 code
    language: str | None = None
    # ISO 15924 code
    script: str | None = None
    # status {official, promotion, bootleg, pseudo-release}
    packaging: str | None = None
    # Multi line text describing edits made
    edit_note: str | None = None
    # Redirect
    redirect_uri: str | None = None

    events: list[MBEvent] | None = None

    labels: list[MBLabel] | None = None

    artist_credit: MBArtistCredit | None = None

    mediums: list[MBMedium] | None = None


