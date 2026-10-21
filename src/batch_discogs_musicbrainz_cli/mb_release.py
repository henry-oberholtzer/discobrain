# Implementation of
# https://musicbrainz.org/doc/Development/Seeding/Release_Editor
from dataclasses import dataclass


@dataclass
class MBArtistName:
    name: str

@dataclass
class MBName:
    mbid: str
    name: str
    artist: MBArtistName
    join_phrase: str

@dataclass
class MBArtistCredit:
    names: list[MBName]

@dataclass
class MBTrack:
    name: str
    number: str
    # MBID
    recording: str
    length: int
    artist_credit: list[MBArtistCredit]

@dataclass
class MBMedium:
    format: str
    name: str
    track: list[MBTrack]

@dataclass
class MBLabel:
    mbid: str
    catalog_number: str
    name: str

@dataclass
class MBDate:
    year: int
    month: int
    day: int

@dataclass
class MBEvent:
    date: MBDate
    # any ISO code
    country: str

@dataclass
class MBURL:
    url: str
    link_type: int

@dataclass
class MBRelease:
    """
    Takes a given data source URL on init,
    then fetches and converts it to a relevant MusicBrainz
    new release format.

    It will titlecase, determine language and script (vaguely)
    and 
    """
    name: str
    # can be pre-existing MBID release group
    release_group: str
    # type of release group
    type: str
    # disambiguation comment, use for White Label, etc
    comment: str
    # annotation, use for multi-line text, e.g. other info on discogs
    annotation: str
    barcode: str
    # ISO-639-3 code
    language: str
    # ISO 15924 code
    script: str
    # status {official, promotion, bootleg, pseudo-release}
    packaging: str
    # Multi line text describing edits made
    edit_note: str
    # Redirect
    redirect_uri: str

    events: list[MBEvent]

    labels: list[MBLabel]

    artist_credit: list[MBArtistCredit]

    mediums: list[MBMedium]

    def post(self) -> object:
        """
        Converts the object into a relevant object for MB
        """

