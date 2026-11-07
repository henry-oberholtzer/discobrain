# Implementation of
# https://musicbrainz.org/doc/Development/Seeding/Release_Editor
import dataclasses
import datetime
import itertools
import re
import sqlite3
from collections.abc import MutableMapping
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from os import PathLike
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urljoin

from isocodes import countries
from requests.exceptions import HTTPError
from requests_ratelimiter import LimiterSession

from .utils import guess_iso_639_3, guess_iso_15924

LOWERCASE_WORDS = ["the", "da", "of", "for", "an?", "in", "to", "remix", "original mix", "mix", "dub mix", "remix", "edit", "re-edit", "presents", "feat.?"]

MUSICBRAINZ_API_ROOT = "https://musicbrainz.org/ws/2/"

MUSICBRAINZ_REQUESTS_PER_SECOND = 1

class MBReleaseType(StrEnum):
    ALBUM = "Album"
    SINGLE = "Single"
    EP = "EP"
    BROADCAST = "Broadcast"
    OTHER = "Other"
    NONE = ""

def mb_dict_factory(data: MutableMapping, parent_key: str = '', sep: str = '.'):
    items: list[tuple[str, str | int]] = []
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
    def lowercase(matchobj) -> str:
        return matchobj.group(0).lower()
    if text.isupper() or text.isnumeric() or text.islower():
        return text
    for word in LOWERCASE_WORDS:
        regex = rf'(?<=[\w\d\s,][\s\(]){word}(?=[\s,\)])'
        text = re.sub(regex, lowercase, text, flags=re.IGNORECASE)
    return text

@dataclass
class MBBase:
    TITLE_FIELDS: ClassVar[list[str]] = ["name"]
    COUNTRY_FIELDS: ClassVar[list[str]] = ["country"]
    BARCODE_FIELDS: ClassVar[list[str]] = ["barcode"]

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
                result = countries.by_name_dict.get(val)
                if result:
                    return super().__setattr__(prop, result.alpha_2)
            elif prop in self.BARCODE_FIELDS:
                return super().__setattr__(prop, re.sub(r"\D", '', val))
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
    name: str | None = None
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
    # ISO 15924 code
    #script: str | None = None
    # status {official, promotion, bootleg, pseudo-release}
    status: str | None = None
    packaging: str | None = None
    # Multi line text describing edits made
    edit_note: str | None = None
    # Redirect
    redirect_uri: str | None = None

    events: list[MBEvent] | None = None

    labels: list[MBLabel] | None = None

    artist_credit: MBArtistCredit | None = None

    mediums: list[MBMedium] | None = None

    def _text_sample(self) -> str:
    # ISO-639-3 code
        def get_track_titles(mediums: list[MBMedium] | None) -> list[str]:
            titles = []
            if mediums:
                for m in mediums:
                    if m.track:
                        for t in m.track:
                            if t.name:
                                titles.append(t.name)
            return titles

        titles = get_track_titles(self.mediums)
        sample = f"{self.name} {' '.join(titles)}"
        return sample

    @property
    def language(self) -> str:
        return guess_iso_639_3(self._text_sample())

    @property
    def script(self) -> str:
        return guess_iso_15924(self._text_sample())

def mb_release_type_from_title(title: str) -> MBReleaseType:
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

def mb_release_type_from_tracks(num_tracks: int) -> MBReleaseType:
    if num_tracks < 4:
        return MBReleaseType.SINGLE
    elif num_tracks < 7:
        return MBReleaseType.EP
    return MBReleaseType.ALBUM

DB_TABLE_MAPPING = {
        "artist": "artist-rels",
        "label": "label-rels",
        "release": "release-rels",
        "releasegroup": "release-group-rels"
}

class MusicBrainzLookUp:
    """
    Look and cache up musicbrainz entities corresponding to a given URL
    """
    def __init__(self,
        user_agent: str,
        db_file: Path | PathLike | str | None = None,
        api_root: str | None = None,
        init_tables: bool = True,
    ):
        self.user_agent = user_agent
        self.db_file = db_file
        self.api_root = MUSICBRAINZ_API_ROOT if not api_root else api_root
        # If a database file is given, create the tables on it if they don't exist
        if init_tables:
            self.init_tables()

    @property
    def db_path(self) -> str:
        if self.db_file:
            return str(Path(self.db_file).resolve().absolute())
        return ":memory:"

    @cached_property
    def db(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    @property
    def session(self) -> LimiterSession:
        s = LimiterSession(
            per_second=MUSICBRAINZ_REQUESTS_PER_SECOND,
        )
        s.headers.update({ "User-Agent": self.user_agent })
        return s

    def table_definition(self):
        return """
        CREATE TABLE IF NOT EXISTS cache(
            url TEXT UNIQUE NOT NULL,
            mbid TEXT NOT NULL,
            relationship TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """

    def table_insert(self):
        return "INSERT INTO cache (url, mbid, relationship, timestamp) VALUES (?, ?, ?, ?)"

    @property
    def zulu_timestamp(self):
        return datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z')

    def store(self, url: str, mbid: str, relationship: str):
        """
        Store the given data
        """
        cursor = self.db.cursor()
        cursor.execute(
            self.table_insert(),
            (url, mbid, relationship, self.zulu_timestamp)
        )
        cursor.close()

    def get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any] | None:
        try:
            print(params)
            response = self.session.get(
                urljoin(self.api_root, endpoint,),
                params={
                    **params,
                    "fmt": "json"
                }
            )
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            print(e)
            return None

    def get_rel_data(self, data: dict[str, Any]):
        rels = []
        resource = data["resource"]
        relations = data.get("relations")
        if relations:
            for relation in relations:
                target_type = relation["target-type"]
                target_mbid = relation[target_type]["id"]
                rels.append((resource, target_mbid, target_type, self.zulu_timestamp))
        return rels

    def _get_url_resources(self, 
        resources: list[str]):
        data = []
        for batch in itertools.batched(resources, 100):
            response = self.get("url", { 
                "resource": resources,
                "inc": "+".join(DB_TABLE_MAPPING.values())
            })
            if response is not None:
                if response.get("urls"):
                    for url in response["urls"]:
                        data.extend(self.get_rel_data(url))
                else:
                    data.extend(self.get_rel_data(response))
        return data

    def get_url_resources(self, resources: list[str]):
        data = self._get_url_resources(resources)
        cursor = self.db.cursor()
        cursor.executemany(self.table_insert(), data)
        cursor.close()
        self.db.commit()
        return data


    def init_tables(self):
        cursor = self.db.cursor()
        cursor.execute(self.table_definition())
        cursor.close()

    def bulk_query(self, urls: list[str]):
        raise NotImplementedError

    def get_mbid(self, url: str, relationship: str) -> str | None:
        # Either immediately returns a query or enqueus it.
        cursor = self.db.cursor()
        response = cursor.execute(f"SELECT mbid FROM cache WHERE url='{url}' AND relationship='{relationship}'").fetchone()
        cursor.close()
        if response:
            return response[0]
        return None

