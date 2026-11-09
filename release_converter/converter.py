
from release_converter.musicbrainz import MBTrack
from copy import copy
from release_converter.musicbrainz import MBMedium
from release_converter.musicbrainz import MBEvent
from release_converter.musicbrainz import MBDate
import re
from itertools import chain
from typing import cast

import requests

from release_converter.discogs import DiscogsFormat, DiscogsRelease, DISCOGS_ISO_COUNTRY_MAPPING, DiscogsTrack, DISCOGS_FORMAT_MAPPING
from release_converter.musicbrainz import (
    MBURL,
    MBRelease,
    MBReleaseStatus,
    MBReleaseType,
    mb_release_type_from_title,
    mb_release_type_from_tracks,
)

from .constants import USER_AGENT

DISCOGS_ENDPOINT = "https://api.discogs.com"

DISCOGS_ID_RE = re.compile(r"(?<=\/)\d+")

# Discogs types
ALBUM = ["Mini-Album", "Album", "Compilation"]

SINGLE = ["Single", "Maxi-Single"]

EP = ["EP"]

DISAMBIGUATORS = ["White Label", "Repress", "Remastered", "Misprint"]

def barcode(d: DiscogsRelease) -> str:
    """
    Extract and normalize barcode
    """
    for id in d['identifiers']:
        if id['type'] == 'Barcode':
            return id['value']
    return ""

def discogs_url(d: DiscogsRelease) -> MBURL:
    """
    Give the source URL from Discogs
    """
    return MBURL(
            url=f"https://www.discogs.com/release/{d['id']}",
            link_type=76
            )

def format_descs(formats: list[DiscogsFormat]) -> set[str]:
    descriptions = [format['descriptions'] for format in formats]
    descriptions = set(chain.from_iterable(descriptions))
    return descriptions

def release_type_from_format(formats: list[DiscogsFormat]) -> MBReleaseType:
    descriptions = format_descs(formats)
    if not set(ALBUM).isdisjoint(descriptions):
        return MBReleaseType.ALBUM
    if not set(EP).isdisjoint(descriptions):
        return MBReleaseType.EP
    if not set(SINGLE).isdisjoint(descriptions):
        return MBReleaseType.SINGLE
    return MBReleaseType.NONE


def release_type(d: DiscogsRelease) -> str:
    # 1. From given information (most reliable)
    release_type = release_type_from_format(d['formats'])
    # 2. From title (artist intent)
    if not release_type:
        release_type = mb_release_type_from_title(d['title'])
    # 3. From track count
    if not release_type:
        release_type = mb_release_type_from_tracks(len(d['tracklist']))
    return release_type

def release_disambiguation(formats: list[DiscogsFormat]) -> str:
    descs = format_descs(formats)
    free_text = [f.get('text') for f in formats if f.get('text') is not None]
    disambiguators = descs.intersection(set(DISAMBIGUATORS))
    return f"{', '.join([*free_text, *disambiguators])}".lower()

def discogs_release_status(formats: list[DiscogsFormat]) -> MBReleaseStatus:
    descriptions = format_descs(formats)
    if not {"Promo", "Test Pressing", "Advance"}.isdisjoint(descriptions):
        return MBReleaseStatus.PROMO
    if not {"Unofficial Release", "Partially Unofficial"}.isdisjoint(descriptions):
        return MBReleaseStatus.BOOTLEG
    return MBReleaseStatus.OFFICIAL

def discogs_date_string(date: str) -> MBDate:
    segments = date.split('-')
    return MBDate(
        year=int(segments[0]) if int(segments[0]) else None,
        month=int(segments[1]) if int(segments[1]) else None,
        day=int(segments[2]) if int(segments[2]) else None
    )


def discogs_release_events(d: DiscogsRelease) -> list[MBEvent]:
    date = discogs_date_string(d['released'])
    countries = DISCOGS_ISO_COUNTRY_MAPPING.get(d['country'])
    if not countries:
        return [MBEvent(date=date)]
    else:
        return [MBEvent(date=date, country=country) for country in countries]

def discogs_format_mapping(f: DiscogsFormat) -> str | None:
    format = f['name']
    mb_version = DISCOGS_FORMAT_MAPPING.get(format)
    if isinstance(mb_version, str):
        return mb_version
    if isinstance(mb_version, dict):
        for desc in f['descriptions']:
            specific = mb_version.get(desc)
            if specific:
                return specific
    return None

def discogs_build_mediums(format: list[DiscogsFormat]) -> list[MBMedium]:
    mediums = []
    for f in format:
        medium = MBMedium()
        qty = int(f['qty'])
        medium.format = discogs_format_mapping(f)
        # Add as many of these as listed
        mediums.extend([copy(medium) for i in range(qty)])
    return mediums

def mm_ss_to_ms(duration: str) -> int:
    segments = duration.split(':')
    return (int(segments[0]) * 60 + int(segments[1]))*1000


def discogs_tracklist(tracklist: list[DiscogsTrack], format: list[DiscogsFormat]) -> list[MBMedium]:
    mediums = discogs_build_mediums(format)
    current_medium = 0
    for track in tracklist:
        track = MBTrack(
            name=track['title'],
            number=track['position'],
            length=mm_ss_to_ms(track['duration'])
        )
        if not mediums[current_medium].track:
            mediums[current_medium].track = [track]
        elif mediums[current_medium].track is not None:
            mediums[current_medium].track.append(track)
    return mediums


class ReleaseConverter:

    def edit_note(self, discogs_release: str | int) -> str:
        if isinstance(discogs_release, int):
            discogs_release = f"https://www.discogs.com/release/{discogs_release}"
        return (f"Imported from {discogs_release} using Discobrain "
        "https://github.com/henry-oberholtzer/discobrain")

    def _discogs_id_extract(self, discogs_url: str | int) -> int:
        if isinstance(discogs_url, int):
            return discogs_url
        if (match := DISCOGS_ID_RE.search(discogs_url)):
            return int(match.group(0))
        return int(discogs_url)

    def _discogs_release_endpoint(self, release_id: int) -> DiscogsRelease:
        response = requests.get(
            f"{DISCOGS_ENDPOINT}/releases/{release_id}",
            headers={ 'User-Agent': USER_AGENT}
        )
        response.raise_for_status()
        return cast(DiscogsRelease, response.json())

    def _mb_from_discogs_release(self, d: DiscogsRelease) -> MBRelease:
        mb = MBRelease(name=d['title']) 
        mb.barcode = barcode(d)
        mb.urls = [discogs_url(d)]
        mb.type = release_type(d)
        mb.comment = release_disambiguation(d['formats'])
        mb.status = discogs_release_status(d['formats'])
        mb.edit_note = self.edit_note(d['id'])
        mb.events = discogs_release_events(d)
        # fetch the release from discogs
        return mb


    def discogs(self, discogs_release: str | int) -> MBRelease:
        id = self._discogs_id_extract(discogs_release)
        release = self._discogs_release_endpoint(id)
        return self._mb_from_discogs_release(release)

