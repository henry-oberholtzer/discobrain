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
    # non optional
    name: str
    # URL for getting source data
    urls: list[MBURL]
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

    artist_credit: list[MBArtistCredit] | None = None

    mediums: list[MBMedium] | None = None


    def post(self) -> object:
        """
        Converts the object into a relevant object for MB
        """

