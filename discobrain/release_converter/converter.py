import os
import re
from copy import deepcopy
from itertools import chain
from typing import cast

import requests
from requests_oauthlib import OAuth1
from requests_ratelimiter import LimiterSession

from .constants import USER_AGENT
from .discogs import (
    DISCOGS_FORMAT_MAPPING,
    DISCOGS_ISO_COUNTRY_MAPPING,
    DiscogsFormat,
    DiscogsLabel,
    DiscogsRelease,
    DiscogsReleaseArtist,
)
from .musicbrainz import (
    MBURL,
    MBArtistCredit,
    MBArtistName,
    MBDate,
    MBEvent,
    MBLabel,
    MBMedium,
    MBName,
    MBRelease,
    MBReleaseStatus,
    MBReleaseType,
    MBTrack,
    MusicBrainzLookUp,
    mb_release_type_from_title,
    mb_release_type_from_tracks,
)

DISCOGS_ENDPOINT = "https://api.discogs.com"
DISCOGS_AUTHENTICATED_REQUESTS_PER_MINUTE = 60
DISCOGS_UNAUTHENTICATED_REQUESTS_PER_MINUTE = 25

DISCOGS_ID_RE = re.compile(r"(?<=\/)\d+")

# Discogs types
ALBUM = ["Mini-Album", "Album", "Compilation"]

SINGLE = ["Single", "Maxi-Single"]

EP = ["EP"]

DISAMBIGUATORS = ["White Label", "Repress", "Remastered", "Misprint"]

EXTRA_ARTIST_TYPES = ["Featuring"]

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
        mediums.extend([deepcopy(medium) for i in range(qty)])
    return mediums

def mm_ss_to_ms(duration: str) -> int | None:
    if not duration:
        return None
    segments = duration.split(':')
    return (int(segments[0]) * 60 + int(segments[1]))*1000

def discogs_strip_disambiguation(name: str) -> str:
    return re.sub(r'\s*\(\d+\)$', '', name)

def make_join(join: str | None) -> str | None:
    if not join:
        return None
    if join in ",;":
        return ", "
    return f" {join.strip()} "

def build_artist(d_artist: DiscogsReleaseArtist) -> MBName:
    artist = MBName()
    # If it's "Various", replace with the known MB various artists
    if d_artist['id'] == 194:
        artist.mbid="89ad4ac3-39f7-470e-963a-56509c546377"
    # If it's unknown artist
    elif d_artist['id'] == 355:
        artist.mbid="125ec42a-7229-4250-afc5-e057484327fe"
    else:
        # Set this as a Discogs ID for now
        # we'll see if we can find the artist later, otherwise we will drop it.
        artist.mbid = f"https://www.discogs.com/artist/{d_artist.get('id')}"
        anv = discogs_strip_disambiguation(d_artist.get('anv'))
        name = discogs_strip_disambiguation(d_artist.get('name'))
        artist.name = anv if anv else name
        artist.artist = MBArtistName(name=name)
    artist.join_phrase=make_join(d_artist.get('join'))
    return artist


def build_artists(artists: list[DiscogsReleaseArtist]) -> MBArtistCredit:
    return MBArtistCredit(names=[build_artist(artist) for artist in artists])

def discogs_tracklist(d: DiscogsRelease) -> list[MBMedium]:
    tracklist = d['tracklist']
    mediums = discogs_build_mediums(d['formats'])
    album_artist = build_artists(d['artists'])
    current_side = 0
    current_medium = 0
    for idx, track in enumerate(tracklist):
        mb_track = MBTrack(
            name=track['title'],
            number=track['position'],
            length=mm_ss_to_ms(track['duration'])
        )
        # Check if the medium should be changed

        # The current medium must have a track to be eligible to change
        # and there must be more mediums we can change to.
        med = mediums[current_medium]
        if idx != 0 and current_medium < len(mediums):
            last_index = med.track[-1].number
            if mb_track.number and last_index and mb_track.number[0] != last_index[0]:
                # If the indices don't start the same, increment the curent medium
                # If this medium is double sided, divide it by 2
                if med.format and ("Vinyl" in med.format or "Cassette" in med.format):
                    current_side += 1
                    if current_side % 2 == 0:
                        current_medium += 1
                else:
                    current_medium += 1

        if track_artists := track.get('artists'):
            mb_track.artist_credit = build_artists(track_artists)
        else:
            mb_track.artist_credit = deepcopy(album_artist)
        if extra_artists := track.get('extraartists'):
            extra = build_artists([ea for ea in extra_artists if ea['role'] in EXTRA_ARTIST_TYPES])
            mb_track.artist_credit.names[-1].join_phrase = make_join("Feat.")
            mb_track.artist_credit.names.extend(extra.names)
        if not mediums[current_medium].track:
            mediums[current_medium].track = [mb_track]
        elif mediums[current_medium].track:
            mediums[current_medium].track.append(mb_track)

    return mediums

def build_label(l: DiscogsLabel) -> MBLabel:
    # Handle the No Label exception
    if "Not On Label" in l['name']:
        return MBLabel(
            mbid="157afde4-4bf5-4039-8ad2-5a15acc85176"
    )
    return MBLabel(
        name=discogs_strip_disambiguation(l['name']),
        catalog_number=l['catno'],
        mbid=f"https://www.discogs.com/label/{l['id']}"
    )

def build_labels(l: list[DiscogsLabel]) -> list[MBLabel]:
    return [build_label(label) for label in l]

def discogs_master_release(d: DiscogsRelease) -> str | None:
    master_id = d.get('master_id')
    return f"https://www.discogs.com/master/{master_id}" if master_id else None


class ReleaseConverter:
    def __init__(
        self,
        lookup: MusicBrainzLookUp | None = None,
        *,
        user_token: str | None = None,
        api_key: str | None = None,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
        oauth_token: str | None = None,
        oauth_token_secret: str | None = None,
        session: requests.Session | None = None,
        user_agent: str = USER_AGENT,
        auto_env: bool = True,
    ):
        self.lookup = lookup
        self.user_agent = user_agent
        self.user_token = user_token or api_key
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret
        self.auto_env = auto_env

        if auto_env:
            if not self.user_token:
                self.user_token = os.getenv("DISCOGS_USER_TOKEN") or os.getenv("DISCOGS_API_KEY")
            if not self.consumer_key:
                self.consumer_key = os.getenv("DISCOGS_CONSUMER_KEY")
            if not self.consumer_secret:
                self.consumer_secret = os.getenv("DISCOGS_CONSUMER_SECRET")
            if not self.oauth_token:
                self.oauth_token = os.getenv("DISCOGS_OAUTH_TOKEN")
            if not self.oauth_token_secret:
                self.oauth_token_secret = os.getenv("DISCOGS_OAUTH_TOKEN_SECRET")

        if session is not None:
            self.session = self._configure_session(session)
        else:
            self.session = self._build_session()

    @property
    def is_authenticated(self) -> bool:
        return self.auth_type is not None

    @property
    def auth_type(self) -> str | None:
        if self.consumer_key and self.consumer_secret and self.oauth_token and self.oauth_token_secret:
            return "oauth"
        if self.user_token:
            return "user_token"
        if self.consumer_key and self.consumer_secret:
            return "key_secret"
        return None

    def _configure_session(self, session: requests.Session) -> requests.Session:
        session.headers["User-Agent"] = self.user_agent

        match self.auth_type:
            case "oauth":
                if session.auth is None:
                    session.auth = OAuth1(
                        client_key=self.consumer_key,
                        client_secret=self.consumer_secret,
                        resource_owner_key=self.oauth_token,
                        resource_owner_secret=self.oauth_token_secret,
                    )
            case "user_token":
                if "Authorization" not in session.headers:
                    session.headers["Authorization"] = f"Discogs token={self.user_token}"
            case "key_secret":
                if "Authorization" not in session.headers:
                    session.headers["Authorization"] = f"Discogs key={self.consumer_key}, secret={self.consumer_secret}"
            case _:
                pass

        return session

    def _build_session(self) -> requests.Session:
        rate_limit = (
            DISCOGS_AUTHENTICATED_REQUESTS_PER_MINUTE
            if self.is_authenticated
            else DISCOGS_UNAUTHENTICATED_REQUESTS_PER_MINUTE
        )
        session = LimiterSession(per_minute=rate_limit)
        return self._configure_session(session)

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
        response = self.session.get(f"{DISCOGS_ENDPOINT}/releases/{release_id}")
        response.raise_for_status()
        return cast(DiscogsRelease, response.json())

    def _mb_from_discogs_release(self, d: DiscogsRelease) -> MBRelease:
        mb = MBRelease(name=d['title']) 
        mb.artist_credit=build_artists(d['artists'])
        mb.release_group=discogs_master_release(d)
        mb.barcode = barcode(d)
        mb.urls = [discogs_url(d)]
        mb.type = release_type(d)
        mb.comment = release_disambiguation(d['formats'])
        mb.status = discogs_release_status(d['formats'])
        mb.edit_note = self.edit_note(d['id'])
        mb.events = discogs_release_events(d)
        mb.mediums = discogs_tracklist(d)
        mb.labels = build_labels(d['labels'])
        return mb

    def run_lookup(self, mb_releases: list[MBRelease] | MBRelease):
        if self.lookup:
            if not isinstance(mb_releases, list):
                mb_releases = [mb_releases]
            for mb_release in mb_releases:
                self.lookup.get_mbids(mb_release)
            self.lookup.clear_queue()
            for mb_release in mb_releases:
                self.lookup.get_mbids(mb_release, enqueue=False)

    def discogs(self, discogs_release: str | int | list[str] | list[int]) -> MBRelease | list[MBRelease]:
        if isinstance(discogs_release, list):
            releases = []
            for id in discogs_release:
                id = self._discogs_id_extract(id)
                release = self._discogs_release_endpoint(id)
                mb = self._mb_from_discogs_release(release)
                releases.append(mb)
            self.run_lookup(releases)
            return releases
        else:
        # fetch the release from discogs
            id = self._discogs_id_extract(discogs_release)
            release = self._discogs_release_endpoint(id)
            mb = self._mb_from_discogs_release(release)
            self.run_lookup(mb)
        # now check the IDs against our URL cache
            return mb

