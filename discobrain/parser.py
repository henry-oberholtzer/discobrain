import re

# Match patterns like:
# - https://www.discogs.com/release/13954-DJ-Teebee-Through-The-Eyes-Of-A-Scorpion
# - discogs.com/release/13954
# - r13954 or [r13954]
# - 13954
DISCOGS_URL_PATTERN = re.compile(r"(?:release/|/|^r|\[r)?(\d+)", re.IGNORECASE)


def parse_discogs_id(value: str | int) -> int | None:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text or text.startswith("#"):
        return None
    if text.isdigit():
        return int(text)
    # Search for /release/<id> first (most specific for URLs)
    if url_match := re.search(r"release/(\d+)", text, re.IGNORECASE):
        return int(url_match.group(1))
    # Search for generic pattern
    if match := DISCOGS_URL_PATTERN.search(text):
        return int(match.group(1))
    return None


def parse_discogs_ids(raw_text: str) -> list[int]:
    """
    Parses a multiline string of Discogs URLs or release IDs into a deduplicated list of integer IDs.
    Preserves input order while removing duplicates.
    """
    results: list[int] = []
    seen: set[int] = set()
    for line in raw_text.splitlines():
        line = line.strip()
        release_id = parse_discogs_id(line)
        if release_id is not None and release_id not in seen:
            seen.add(release_id)
            results.append(release_id)
    return results
