import re
from itertools import chain
from typing import cast

import requests

from discobrain import USER_AGENT
from discobrain.discogs_release import DiscogsFormat, DiscogsRelease
from discobrain.mb_release import MBURL, MBRelease, MBReleaseType

DISCOGS_ENDPOINT = "https://api.discogs.com"

DISCOGS_ID_RE = re.compile(r"(?<=\/)\d+")

# Discogs types
ALBUM = ["Mini-Album", "Album", "Compilation"]

SINGLE = ["Single", "Maxi-Single"]

EP = ["EP"]

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

def type_from_format(formats: list[DiscogsFormat]) -> MBReleaseType:
    descriptions = format_descs(formats)
    if not set(ALBUM).isdisjoint(descriptions):
        return MBReleaseType.ALBUM
    if not set(EP).isdisjoint(descriptions):
        return MBReleaseType.EP
    if not set(SINGLE).isdisjoint(descriptions):
        return MBReleaseType.SINGLE
    return MBReleaseType.NONE

def type_from_title(title: str) -> MBReleaseType:
    """
    if ends with 'LP' or 'Album' -> Album
    if ends with 'EP', or 'E.P.'-> EP
    """
    normalized = re.sub(r'[^a-z ]', '', title.lower())
    print(normalized)
    if normalized.endswith('ep') or ' ep ' in normalized:
        return MBReleaseType.EP
    if normalized.endswith(('album', 'lp')):
        return MBReleaseType.ALBUM
    return MBReleaseType.NONE

def type_from_tracks() -> MBReleaseType:
    return MBReleaseType.NONE

def release_type(d: DiscogsRelease) -> str:
    # 1. From given information (most reliable)
    release_type = type_from_format(d['formats'])
    # 2. From title (artist intent)
    if not release_type:
        release_type = type_from_title(d['title'])

    # 3. From tracks
    # if one track


    # Single

    # EP

    # Broadcast

    # Other
    return release_type

class ReleaseConverter:


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
        # fetch the release from discogs
        return mb


    def discogs(self, discogs_release: str | int) -> MBRelease:
        id = self._discogs_id_extract(discogs_release)
        release = self._discogs_release_endpoint(id)
        return self._mb_from_discogs_release(release)

