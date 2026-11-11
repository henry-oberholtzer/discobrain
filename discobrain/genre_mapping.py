import itertools
from collections.abc import Iterable

# Mapping of Discogs Electronic styles (or combination of styles) to MusicBrainz genres.
# Keys are frozensets of lowercase Discogs style names.
# Values are tuples of specific MusicBrainz genres.
DISCOGS_ELECTRONIC_STYLE_MAP: dict[frozenset[str], tuple[str, ...]] = {
    # -------------------------------------------------------------------------
    # Compound Style Combinations (Modifiers + Base Genres)
    # -------------------------------------------------------------------------
    # Acid compounds
    frozenset({"acid", "techno"}): ("acid techno",),
    frozenset({"acid", "house"}): ("acid house",),
    frozenset({"acid", "trance"}): ("acid trance",),
    frozenset({"acid", "jazz"}): ("acid jazz",),
    # Dub compounds
    frozenset({"dub", "techno"}): ("dub techno",),
    frozenset({"dub", "house"}): ("dub house",),
    # Ambient compounds
    frozenset({"ambient", "techno"}): ("ambient techno",),
    frozenset({"ambient", "house"}): ("ambient house",),
    frozenset({"ambient", "dub"}): ("ambient dub",),
    # Hard / Dark compounds
    frozenset({"hard", "techno"}): ("hard techno",),
    frozenset({"hard", "trance"}): ("hard trance",),
    frozenset({"hard", "house"}): ("hard house",),
    frozenset({"dark", "ambient"}): ("dark ambient",),
    frozenset({"dark", "wave"}): ("darkwave",),
    # Tech compounds
    frozenset({"tech", "house"}): ("tech house",),
    frozenset({"tech", "trance"}): ("tech trance",),
    # Progressive compounds
    frozenset({"progressive", "house"}): ("progressive house",),
    frozenset({"progressive", "trance"}): ("progressive trance",),
    # Minimal compounds
    frozenset({"minimal", "techno"}): ("minimal techno",),
    frozenset({"minimal", "house"}): ("microhouse",),
    # Deep compounds
    frozenset({"deep", "house"}): ("deep house",),
    frozenset({"deep", "techno"}): ("dub techno",),
    # -------------------------------------------------------------------------
    # Standalone Discogs Styles -> MusicBrainz Genres
    # -------------------------------------------------------------------------
    # Techno & Subgenres
    frozenset({"techno"}): ("techno",),
    frozenset({"acid techno"}): ("acid techno",),
    frozenset({"dub techno"}): ("dub techno",),
    frozenset({"minimal techno"}): ("minimal techno",),
    frozenset({"hard techno"}): ("hard techno",),
    frozenset({"schranz"}): ("schranz",),
    frozenset({"detroit techno"}): ("detroit techno",),
    frozenset({"ghettotech"}): ("ghettotech",),
    # House & Subgenres
    frozenset({"house"}): ("house",),
    frozenset({"acid house"}): ("acid house",),
    frozenset({"deep house"}): ("deep house",),
    frozenset({"tech house"}): ("tech house",),
    frozenset({"progressive house"}): ("progressive house",),
    frozenset({"electro house"}): ("electro house",),
    frozenset({"microhouse"}): ("microhouse",),
    frozenset({"tribal house"}): ("tribal house",),
    frozenset({"garage house"}): ("garage house",),
    frozenset({"ghetto house"}): ("ghetto house",),
    frozenset({"italo house"}): ("italo house",),
    frozenset({"euro house"}): ("euro house",),
    # Drum & Bass / Jungle
    frozenset({"drum n bass"}): ("drum and bass",),
    frozenset({"drum & bass"}): ("drum and bass",),
    frozenset({"drum and bass"}): ("drum and bass",),
    frozenset({"jungle"}): ("jungle",),
    frozenset({"halftime"}): ("halftime",),
    frozenset({"breakcore"}): ("breakcore",),
    # Breakbeat & Garage
    frozenset({"breakbeat"}): ("breakbeat",),
    frozenset({"breaks"}): ("breakbeat",),
    frozenset({"uk garage"}): ("uk garage",),
    frozenset({"garage"}): ("uk garage",),
    frozenset({"2-step"}): ("2-step",),
    frozenset({"dubstep"}): ("dubstep",),
    frozenset({"grime"}): ("grime",),
    frozenset({"footwork"}): ("footwork",),
    # Trance & Subgenres
    frozenset({"trance"}): ("trance",),
    frozenset({"goa trance"}): ("goa trance",),
    frozenset({"psy-trance"}): ("psytrance",),
    frozenset({"psytrance"}): ("psytrance",),
    frozenset({"progressive trance"}): ("progressive trance",),
    frozenset({"hard trance"}): ("hard trance",),
    frozenset({"tech trance"}): ("tech trance",),
    # Ambient & Downtempo
    frozenset({"ambient"}): ("ambient",),
    frozenset({"dark ambient"}): ("dark ambient",),
    frozenset({"drone"}): ("drone",),
    frozenset({"downtempo"}): ("downtempo",),
    frozenset({"trip hop"}): ("trip hop",),
    frozenset({"chillwave"}): ("chillwave",),
    frozenset({"new age"}): ("new age",),
    frozenset({"vaporwave"}): ("vaporwave",),
    frozenset({"illbient"}): ("illbient",),
    # IDM & Experimental
    frozenset({"idm"}): ("idm",),
    frozenset({"glitch"}): ("glitch",),
    frozenset({"experimental"}): ("experimental",),
    frozenset({"noise"}): ("noise",),
    # Electro, Synth & Disco
    frozenset({"electro"}): ("electro",),
    frozenset({"electroclash"}): ("electroclash",),
    frozenset({"synth-pop"}): ("synth-pop",),
    frozenset({"synthpop"}): ("synth-pop",),
    frozenset({"synthwave"}): ("synthwave",),
    frozenset({"disco"}): ("disco",),
    frozenset({"nu-disco"}): ("nu-disco",),
    frozenset({"italo-disco"}): ("italo-disco",),
    frozenset({"euro-disco"}): ("euro-disco",),
    frozenset({"hi-nrg"}): ("hi-nrg",),
    frozenset({"eurodance"}): ("eurodance",),
    # Hardcore & Industrial
    frozenset({"hardcore"}): ("hardcore",),
    frozenset({"gabber"}): ("gabber",),
    frozenset({"hardstyle"}): ("hardstyle",),
    frozenset({"speedcore"}): ("speedcore",),
    frozenset({"ebm"}): ("ebm",),
    frozenset({"industrial"}): ("industrial",),
    frozenset({"darkwave"}): ("darkwave",),
    frozenset({"power electronics"}): ("power electronics",),
}

# MusicBrainz genre hierarchy: maps subgenres to their parent genres.
MB_GENRE_PARENTS: dict[str, tuple[str, ...]] = {
    # Subgenres of Techno
    "acid techno": ("techno",),
    "dub techno": ("techno", "ambient"),
    "minimal techno": ("techno",),
    "hard techno": ("techno", "hardcore"),
    "detroit techno": ("techno",),
    "schranz": ("hard techno", "techno"),
    "ambient techno": ("techno", "ambient"),
    "ghettotech": ("techno", "electro"),
    # Subgenres of House
    "acid house": ("house",),
    "deep house": ("house",),
    "tech house": ("house", "techno"),
    "progressive house": ("house",),
    "electro house": ("house", "electro"),
    "microhouse": ("house", "minimal techno"),
    "tribal house": ("house",),
    "garage house": ("house", "uk garage"),
    "ghetto house": ("house",),
    "italo house": ("house", "italo-disco"),
    "euro house": ("house", "eurodance"),
    # Subgenres of Drum & Bass, Jungle, Breakbeat & Garage
    "jungle": ("drum and bass",),
    "halftime": ("drum and bass",),
    "breakcore": ("hardcore", "breakbeat"),
    "uk garage": ("electronic",),
    "2-step": ("uk garage",),
    "dubstep": ("uk garage", "electronic"),
    "grime": ("uk garage", "electronic"),
    "footwork": ("electronic",),
    # Subgenres of Trance
    "goa trance": ("trance",),
    "psytrance": ("trance",),
    "progressive trance": ("trance",),
    "hard trance": ("trance", "hardcore"),
    "tech trance": ("trance", "techno"),
    "acid trance": ("trance",),
    # Subgenres of Ambient & Downtempo
    "dark ambient": ("ambient", "industrial"),
    "drone": ("ambient",),
    "trip hop": ("downtempo", "hip hop"),
    "chillwave": ("downtempo", "synthwave"),
    "ambient dub": ("ambient", "dub"),
    "ambient house": ("ambient", "house"),
    "illbient": ("ambient", "downtempo"),
    # Subgenres of Electro & Synth
    "electroclash": ("electro", "synth-pop"),
    "synthwave": ("synth-pop",),
    "nu-disco": ("disco",),
    "italo-disco": ("disco",),
    "euro-disco": ("disco",),
    "hi-nrg": ("disco",),
    "eurodance": ("electronic", "dance"),
    # Subgenres of Hardcore
    "gabber": ("hardcore",),
    "speedcore": ("hardcore",),
    "hardstyle": ("hardcore",),
    # Base electronic genres roll up to 'electronic'
    "techno": ("electronic",),
    "house": ("electronic",),
    "trance": ("electronic",),
    "drum and bass": ("electronic",),
    "breakbeat": ("electronic",),
    "ambient": ("electronic",),
    "downtempo": ("electronic",),
    "electro": ("electronic",),
    "idm": ("electronic",),
    "ebm": ("electronic", "industrial"),
    "synth-pop": ("electronic", "pop"),
}


def map_discogs_electronic_styles(
    genres: Iterable[str] | None,
    styles: Iterable[str] | None,
) -> list[str]:
    """Map Discogs Electronic styles and compounds to official MusicBrainz genres.

    Only applies when 'Electronic' is present in the Discogs genres list.
    Expands parent genres using the MusicBrainz hierarchy.
    """
    if not genres:
        return []

    # Check if 'Electronic' is among the release genres
    genre_set = {
        g.strip().lower()
        for g in genres
        if isinstance(g, str) and g.strip()
    }
    if "electronic" not in genre_set:
        return []

    if not styles:
        return ["electronic"]

    norm_styles = {
        s.strip().lower()
        for s in styles
        if isinstance(s, str) and s.strip()
    }
    matched_mb_genres: set[str] = set()

    # 1. Check combinations of size 2 (compounds)
    for combo in itertools.combinations(norm_styles, 2):
        key = frozenset(combo)
        if key in DISCOGS_ELECTRONIC_STYLE_MAP:
            for g in DISCOGS_ELECTRONIC_STYLE_MAP[key]:
                matched_mb_genres.add(g)

    # 2. Check standalone singles
    for s in norm_styles:
        key = frozenset([s])
        if key in DISCOGS_ELECTRONIC_STYLE_MAP:
            for g in DISCOGS_ELECTRONIC_STYLE_MAP[key]:
                matched_mb_genres.add(g)

    # 3. Inherit parent genres recursively from MB_GENRE_PARENTS
    final_tags: set[str] = set(matched_mb_genres)
    queue = list(matched_mb_genres)
    visited = set(matched_mb_genres)

    while queue:
        current = queue.pop(0)
        parents = MB_GENRE_PARENTS.get(current, ())
        for parent in parents:
            final_tags.add(parent)
            if parent not in visited:
                visited.add(parent)
                queue.append(parent)

    # Ensure umbrella 'electronic' tag is always present
    final_tags.add("electronic")

    # Return sorted list for deterministic results
    return sorted(final_tags)
