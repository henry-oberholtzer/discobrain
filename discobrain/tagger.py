import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import requests
from oauthlib.oauth2 import OAuth2Error

from .genre_mapping import map_discogs_electronic_styles
from .mb_auth import get_musicbrainz_session, is_musicbrainz_authenticated

MUSICBRAINZ_TAG_URL = "https://musicbrainz.org/ws/2/tag"
CLIENT_ID_TAG = "Discobrain-0.0.1"


@dataclass
class TagSubmissionResult:
    status: str  # "submitted", "skipped", "failed"
    tags: list[str] = field(default_factory=list)
    error: str | None = None


def extract_discogs_tags(raw_data: Mapping[str, Any] | None) -> list[str]:
    """Extract and map tags from Discogs release payload to MusicBrainz genres.

    If the release contains 'Electronic' genre, applies the Electronic style and
    compound mapping along with parent genre inheritance. Otherwise, falls back
    to raw genres and styles.
    """
    if not raw_data:
        return []

    genres = raw_data.get("genres") or []
    styles = raw_data.get("styles") or []

    # Map Electronic styles to MusicBrainz genres
    mapped_tags = map_discogs_electronic_styles(genres, styles)
    if mapped_tags:
        return mapped_tags

    tags: list[str] = []
    seen: set[str] = set()

    for item in list(genres) + list(styles):
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                tags.append(cleaned)

    return tags


def build_tag_submission_xml(release_mbid: str, tags: list[str]) -> str:
    """Build MusicBrainz MMD 2.0 XML metadata payload for release tags."""
    metadata = ET.Element("metadata", xmlns="http://musicbrainz.org/ns/mmd-2.0#")
    release_list = ET.SubElement(metadata, "release-list")
    release = ET.SubElement(release_list, "release", id=release_mbid)
    user_tag_list = ET.SubElement(release, "user-tag-list")

    for tag in tags:
        user_tag = ET.SubElement(user_tag_list, "user-tag")
        name = ET.SubElement(user_tag, "name")
        name.text = tag

    xml_bytes = ET.tostring(metadata, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


def submit_release_tags(
    release_mbid: str,
    tags: list[str],
    session: Any = None,
) -> TagSubmissionResult:
    """Submit tags to a MusicBrainz release if user is authenticated and tags exist."""
    if not release_mbid:
        return TagSubmissionResult(status="skipped", tags=tags, error="Missing release MBID")

    if not tags:
        return TagSubmissionResult(status="skipped", tags=[])

    if session is None:
        if not is_musicbrainz_authenticated():
            return TagSubmissionResult(
                status="skipped",
                tags=tags,
                error="User not authenticated with MusicBrainz",
            )
        session = get_musicbrainz_session()
        if session is None:
            return TagSubmissionResult(
                status="skipped",
                tags=tags,
                error="Could not obtain MusicBrainz session",
            )

    xml_body = build_tag_submission_xml(release_mbid, tags)

    try:
        url = f"{MUSICBRAINZ_TAG_URL}?client={CLIENT_ID_TAG}"
        resp = session.post(
            url,
            data=xml_body.encode("utf-8"),
            headers={"Content-Type": "application/xml; charset=utf-8"},
            timeout=15,
        )
        if 200 <= resp.status_code < 300:
            return TagSubmissionResult(status="submitted", tags=tags)
        return TagSubmissionResult(
            status="failed",
            tags=tags,
            error=f"MusicBrainz returned HTTP {resp.status_code}",
        )
    except (requests.RequestException, OAuth2Error) as e:
        return TagSubmissionResult(status="failed", tags=tags, error=str(e))
