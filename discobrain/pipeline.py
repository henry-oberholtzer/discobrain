import os
import sqlite3
from typing import Any, cast

import requests

from .batch_store import BatchItemRecord, BatchItemStatus, BatchStore
from .release_converter.constants import USER_AGENT
from .release_converter.converter import ReleaseConverter
from .release_converter.discogs import DiscogsRelease
from .release_converter.musicbrainz import MBRelease, MusicBrainzLookUp


def get_musicbrainz_lookup(db_file: str | None = None) -> MusicBrainzLookUp:
    return MusicBrainzLookUp(user_agent=USER_AGENT, db_file=db_file)


def build_converter(
    lookup: MusicBrainzLookUp | None = None,
    session_data: dict[str, Any] | None = None,
) -> ReleaseConverter:
    session_data = session_data or {}
    oauth_token = session_data.get("discogs_access_token") or os.getenv("DISCOGS_OAUTH_TOKEN")
    oauth_token_secret = session_data.get("discogs_access_token_secret") or os.getenv("DISCOGS_OAUTH_TOKEN_SECRET")
    user_token = session_data.get("discogs_user_token") or os.getenv("DISCOGS_USER_TOKEN") or os.getenv("DISCOGS_API_KEY")

    return ReleaseConverter(
        lookup=lookup,
        consumer_key=os.getenv("DISCOGS_CONSUMER_KEY"),
        consumer_secret=os.getenv("DISCOGS_CONSUMER_SECRET"),
        oauth_token=oauth_token,
        oauth_token_secret=oauth_token_secret,
        user_token=user_token,
    )


def _extract_item_summary(mb_release: MBRelease) -> tuple[str | None, str | None, int | None]:
    artist_name = None
    if mb_release.artist_credit and mb_release.artist_credit.names:
        artist_name = "".join(
            [n.name + (n.join_phrase or "") for n in mb_release.artist_credit.names if n.name]
        )

    medium_format = None
    if mb_release.mediums and len(mb_release.mediums) and mb_release.mediums[0].format:
        medium_format = mb_release.mediums[0].format

    release_year = None
    if mb_release.events and len(mb_release.events) and mb_release.events[0].date:
        release_year = mb_release.events[0].date.year

    return artist_name, medium_format, release_year


def process_batch(
    batch_id: str,
    batch_store: BatchStore,
    lookup: MusicBrainzLookUp,
    converter: ReleaseConverter,
    base_url: str = "",
) -> list[str]:
    items = batch_store.get_items(batch_id, status=BatchItemStatus.PENDING.value)
    if not items:
        return []

    errors: list[str] = []

    # 1. Pre-submission Deduplication: Query MusicBrainz for any un-cached release URLs
    release_urls = [f"https://www.discogs.com/release/{item.discogs_id}" for item in items]
    uncached_urls = [url for url in release_urls if not lookup.get_by_url(url)]
    if uncached_urls:
        try:
            lookup.get_url_resources(uncached_urls)
        except (requests.RequestException, sqlite3.Error, ValueError, KeyError) as e:
            # If MusicBrainz lookup fails (e.g. offline/temporary error), continue to check cache
            print(f"Warning: MusicBrainz URL resource lookup error: {e}")

    # 2. Check each item against local cache; drop existing
    for item in items:
        url = f"https://www.discogs.com/release/{item.discogs_id}"
        existing_mbid = lookup.get_by_url(url)
        if existing_mbid:
            batch_store.update_item_status(item.id, BatchItemStatus.DROPPED.value, mbid=existing_mbid)

    # 3. Process remaining unseeded releases
    remaining_items = batch_store.get_items(batch_id, status=BatchItemStatus.PENDING.value)
    for item in remaining_items:
        try:
            raw_release = converter._discogs_release_endpoint(item.discogs_id)
            mb_release = converter._mb_from_discogs_release(raw_release)

            if base_url:
                mb_release.redirect_uri = (
                    f"{base_url.rstrip('/')}/callback?batch_id={batch_id}&discogs_id={item.discogs_id}"
                )

            converter.run_lookup(mb_release)
            artist_name, medium_format, release_year = _extract_item_summary(mb_release)

            # Relies on intrinsic normalization in MBRelease
            payload = mb_release.flatten()

            batch_store.update_item_details(
                item.id,
                title=mb_release.name,
                artist=artist_name,
                format=medium_format,
                year=release_year,
                payload=payload,
                raw_data=raw_release,
            )
        except (requests.RequestException, sqlite3.Error, ValueError, KeyError, RuntimeError) as exc:
            batch_store.delete_item(item.id)
            errors.append(f"Error processing Discogs release {item.discogs_id}: {exc}")

    return errors


def reevaluate_pending_items(
    batch_id: str,
    batch_store: BatchStore,
    lookup: MusicBrainzLookUp,
    converter: ReleaseConverter,
    base_url: str = "",
) -> list[BatchItemRecord]:
    pending_items = batch_store.get_items(batch_id, status=BatchItemStatus.PENDING.value)
    if not pending_items:
        return []

    parsed: list[tuple[BatchItemRecord, MBRelease, DiscogsRelease]] = []
    for item in pending_items:
        try:
            if item.raw_data:
                raw_release = cast(DiscogsRelease, item.raw_data)
            else:
                raw_release = converter._discogs_release_endpoint(item.discogs_id)

            mb_release = converter._mb_from_discogs_release(raw_release)
            if base_url:
                mb_release.redirect_uri = (
                    f"{base_url.rstrip('/')}/callback?batch_id={batch_id}&discogs_id={item.discogs_id}"
                )
            parsed.append((item, mb_release, raw_release))
        except (requests.RequestException, sqlite3.Error, ValueError, KeyError, RuntimeError) as exc:
            print(f"Warning: Failed to prepare release {item.discogs_id} for re-evaluation: {exc}")

    if not parsed:
        return pending_items

    try:
        converter.run_lookup([mb for _, mb, _ in parsed])
    except (requests.RequestException, sqlite3.Error, ValueError, KeyError, RuntimeError) as exc:
        print(f"Warning: Lookup error during re-evaluation: {exc}")

    for item, mb_release, raw_release in parsed:
        try:
            artist_name, medium_format, release_year = _extract_item_summary(mb_release)
            payload = mb_release.flatten()
            batch_store.update_item_details(
                item.id,
                title=mb_release.name,
                artist=artist_name,
                format=medium_format,
                year=release_year,
                payload=payload,
                raw_data=raw_release,
            )
        except (ValueError, KeyError, RuntimeError) as exc:
            print(f"Warning: Failed to update re-evaluated release {item.discogs_id}: {exc}")

    return batch_store.get_items(batch_id, status=BatchItemStatus.PENDING.value)
