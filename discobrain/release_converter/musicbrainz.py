# Implementation of
# https://musicbrainz.org/doc/Development/Seeding/Release_Editor
import dataclasses
import datetime
import itertools
import re
import sqlite3
from collections.abc import MutableMapping
from dataclasses import dataclass, field, fields
from enum import StrEnum
from functools import cached_property
from os import PathLike
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urljoin

from isocodes import countries
from requests.exceptions import HTTPError
from requests_ratelimiter import LimiterSession

from discobrain.guess_case import guess_case

from .utils import guess_iso_639_3, guess_iso_15924

# Eventually lifted to a configuration
MUSICBRAINZ_API_ROOT = "https://musicbrainz.org/ws/2/"

MUSICBRAINZ_FEATURING_JOIN = "feat."

MUSICBRAINZ_SUBTRACK_SEPARATOR = "/"

MUSICBRAINZ_REQUESTS_PER_SECOND = 1


class MBReleaseType(StrEnum):
    ALBUM = "Album"
    SINGLE = "Single"
    EP = "EP"
    BROADCAST = "Broadcast"
    OTHER = "Other"
    NONE = ""

class MBReleaseStatus(StrEnum):
    OFFICIAL = "official"
    PROMO = "promotion"
    BOOTLEG = "bootleg"
    PSUEDO = "pseudo-release"

def mb_dict_factory(data: MutableMapping, parent_key: str = '', sep: str = '.'):
    items: list[tuple[str, str | int]] = []
    for key, value in data.items():
        flat_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(mb_dict_factory(data=value, parent_key=flat_key).items())
        if isinstance(value, (str, int)):
            items.append((flat_key, value))
        if isinstance(value, list) and len(value):
            if isinstance(value[0], MutableMapping):
                for idx, iterable_value in enumerate(value):
                    idx_key = f"{flat_key}{sep}{idx}"
                    items.extend(mb_dict_factory(iterable_value, parent_key=idx_key).items())
            else:
                for idx, iterable_value in enumerate(value):
                    idx_key = f"{flat_key}{sep}{idx}"
                    items.append((idx_key, iterable_value))
    return dict(items)


@dataclass
class MBBase:
    TITLE_FIELDS: ClassVar[list[str]] = ["name"]
    COUNTRY_FIELDS: ClassVar[list[str]] = ["country"]
    BARCODE_FIELDS: ClassVar[list[str]] = ["barcode"]
    GUESS_CASE_ENTITY: ClassVar[str | None] = None

    def flatten(self) -> dict[str, int | str]:
        return mb_dict_factory(dataclasses.asdict(self))

    def __setattr__(self, prop: str, val: str | int):
        """
        Manages necessary transformations to make this into "Good" MusicBrainz data.
        """
        if isinstance(val, str):
            if prop in self.TITLE_FIELDS:
                entity = self.GUESS_CASE_ENTITY or "release"
                return super().__setattr__(
                    prop, guess_case(val, entity=entity, keep_uppercased=True)
                )
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
    GUESS_CASE_ENTITY: ClassVar[str | None] = "artist"
    name: str | None = None

@dataclass
class MBName(MBBase):
    GUESS_CASE_ENTITY: ClassVar[str | None] = "artist"
    mbid: str | None = None
    name: str | None = None
    artist: MBArtistName | None = None
    join_phrase: str | None = None

@dataclass
class MBArtistCredit(MBBase):
    names: list[MBName] = field(default_factory=list)

@dataclass
class MBTrack(MBBase):
    GUESS_CASE_ENTITY: ClassVar[str | None] = "track"
    name: str | None = None
    number: str | None = None
    # MBID
    recording: str | None = None
    length: int | None = None
    artist_credit: MBArtistCredit | None = None

@dataclass
class MBMedium(MBBase):
    GUESS_CASE_ENTITY: ClassVar[str | None] = "release"
    track: list[MBTrack] = field(default_factory=list)
    format: str | None = None
    name: str | None = None

@dataclass
class MBLabel(MBBase):
    GUESS_CASE_ENTITY: ClassVar[str | None] = "label"
    mbid: str | None = None
    catalog_number: str | None = None
    name: str | None = None

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
    GUESS_CASE_ENTITY: ClassVar[str | None] = "release"
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

    def flatten(self) -> dict[str, int | str]:
        flat = super().flatten()
        if self.language:
            flat["language"] = self.language
        if self.script:
            flat["script"] = self.script
        return flat

def mb_release_type_from_title(title: str) -> MBReleaseType:
    """
    if ends with 'LP' or 'Album' -> Album
    if ends with 'EP', or 'E.P.'-> EP
    """
    normalized = re.sub(r'[^a-z ]', '', title.lower())
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

MUSICBRAINZ_URL_RELS = ["artist-rels", "label-rels", "release-rels", "release-group-rels"]

class MusicBrainzLookUp:
    """
    Look and cache up musicbrainz entities corresponding to a given URL
    """
    def __init__(self,
        user_agent: str,
        db_file: Path | PathLike | str | None = None,
        api_root: str | None = None,
        init_tables: bool = True,
        url_rels: list[str] | None = None
    ):
        self.user_agent = user_agent
        self.db_file = db_file
        self.api_root = MUSICBRAINZ_API_ROOT if not api_root else api_root
        self.url_rels = MUSICBRAINZ_URL_RELS if not url_rels else url_rels
        self.queue = []
        # If a database file is given, create the tables on it if they don't exist
        if init_tables:
            self.init_tables()

    @property
    def db_path(self) -> str:
        if self.db_file and str(self.db_file) != ":memory:":
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
        return "INSERT OR REPLACE INTO cache (url, mbid, relationship, timestamp) VALUES (?, ?, ?, ?)"

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
        self.db.commit()

    def get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any] | None:
        try:
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
        resource = data.get("resource")
        if not resource:
            return rels
        relations = data.get("relations")
        if relations:
            for relation in relations:
                target_type = relation["target-type"]
                target_mbid = relation[target_type]["id"]
                rels.append((resource, target_mbid, target_type, self.zulu_timestamp))
        return rels

    def _get_url_resources(self, resources: list[str]):
        data = []
        for batch in itertools.batched(resources, 100):
            response = self.get("url", { 
                "resource": list(batch),
                "inc": "+".join(self.url_rels)
            })
            if response is not None:
                if "urls" in response:
                    for url in response["urls"]:
                        data.extend(self.get_rel_data(url))
                elif "resource" in response:
                    data.extend(self.get_rel_data(response))
        return data

    def get_url_resources(self, resources: list[str]):
        data = self._get_url_resources(resources)
        if data:
            cursor = self.db.cursor()
            cursor.executemany(self.table_insert(), data)
            cursor.close()
            self.db.commit()
        return data

    def init_tables(self):
        cursor = self.db.cursor()
        cursor.execute(self.table_definition())
        cursor.close()

    def get_mbid(self, url: str, relationship: str) -> str | None:
        cursor = self.db.cursor()
        response = cursor.execute(
            "SELECT mbid FROM cache WHERE url = ? AND relationship = ?",
            (url, relationship),
        ).fetchone()
        cursor.close()
        if response:
            return response[0]
        return None

    def get_by_url(self, url: str) -> str | None:
        cursor = self.db.cursor()
        response = cursor.execute("SELECT mbid FROM cache WHERE url = ?", (url,)).fetchone()
        cursor.close()
        if response:
            return response[0]
        return None

    def clear_queue(self):
        urls = list(self.queue)
        self.queue = []
        if urls:
            self.get_url_resources(urls)

    def clear_cache(self) -> None:
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM cache;")
        cursor.close()
        self.db.commit()

    def get_cache_count(self) -> int:
        cursor = self.db.cursor()
        res = cursor.execute("SELECT COUNT(*) FROM cache;").fetchone()
        cursor.close()
        if res:
            return int(res[0])
        return 0

    def get_mbids(self, mb_base: MBBase, enqueue: bool = True):
        target_types = (MBMedium, MBTrack, MBLabel, MBRelease, MBArtistCredit, MBName)
        for mb_field in fields(mb_base):
            key = mb_field.name
            value = getattr(mb_base, key)
            if (
                key in ["mbid", "release_group"]
                and isinstance(value, str)
                and not re.match(
                    r'[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}',
                    value,
                )
                and value.startswith("http")
            ):
                if stored_mbid := self.get_by_url(value):
                    setattr(mb_base, key, stored_mbid)
                elif enqueue:
                    self.queue.append(value)
                else:
                    # Nothing has been found
                    setattr(mb_base, key, None)
            elif isinstance(value, target_types):
                self.get_mbids(value, enqueue=enqueue)
            elif isinstance(value, list):
                for entry in value:
                    if isinstance(entry, MBArtistCredit):
                        for ename in entry.names:
                            self.get_mbids(ename, enqueue=enqueue)
                    elif isinstance(entry, target_types):
                        self.get_mbids(entry, enqueue=enqueue)

