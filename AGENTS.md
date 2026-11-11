# AGENTS.md — Repository Guide for Discobrain

This document provides a comprehensive operational and architectural guide for AI agents (and human developers) working on the **Discobrain** codebase.

---

## 1. Project Overview & Mission

**Discobrain** is a local web application built to streamline batch submissions of music releases into [MusicBrainz](https://musicbrainz.org/).

### Core Goals (as defined in `README.md`)
1. **Automated Data Conversion & Intrinsic Normalization:** Transform release metadata from external sources (starting with Discogs) into MusicBrainz-compliant structures (`MBRelease`) before seeding into the MusicBrainz Release Editor. Crucially, **data normalization is built directly into the `MBRelease` class hierarchy itself**: assigning fields to `MBRelease` and its constituent `MBBase` entities immediately normalizes titles, countries, barcodes, and dynamically infers language and script.
2. **Entity & Relation Caching:** Map external artist, label, and release URLs/IDs to known MusicBrainz Identifiers (MBIDs) in a local SQLite cache (`MusicBrainzLookUp`) to avoid duplicate queries and facilitate entity linking.
3. **Pre-Submission Deduplication:** Automatically query MusicBrainz and the local cache to drop releases that are already present in MusicBrainz.
4. **Guided & Automated Submission Workflow:** Present converted releases with one-click seeding into the MusicBrainz web editor (`https://musicbrainz.org/release/add`), dynamically refresh artist/label mappings as earlier releases in the batch are submitted, and track submission progress.
5. **Minimalist Frontend:** Maintain an intentionally lightweight frontend with minimal JavaScript, prioritizing simple server-rendered HTML forms and native browser navigation.
6. **Future Expansion:** Expand beyond Discogs to support imports from additional platforms (e.g., Bandcamp, Beatport).

---

## 2. Architecture & Data Flow

```mermaid
flowchart TD
    User([User / Web UI]) -->|Input Discogs URLs or IDs / TXT upload| FlaskApp[Flask App Controllers]
    FlaskApp --> Auth[Discogs OAuth / Token Handler]
    FlaskApp --> Dedupe[Deduplication Check]
    
    Dedupe --> LookupCache[(MusicBrainzLookUp SQLite Cache)]
    Dedupe --> MBAPI[MusicBrainz Web Service /ws/2]
    
    Dedupe -->|Drop existing releases| DroppedList[Dropped Releases List]
    Dedupe -->|Unseeded releases| Converter[ReleaseConverter]
    
    Converter --> DiscogsAPI[Discogs API]
    DiscogsAPI -->|DiscogsRelease JSON| Converter
    
    subgraph MBReleaseHierarchy["MBRelease & MBBase Data Hierarchy (Intrinsic Normalization)"]
        Converter -->|Instantiate & Populate| MBReleaseInstance["MBRelease Instance"]
        
        subgraph SetattrNormalization["Automatic on Property Assignment (MBBase.__setattr__)"]
            TitleCase["Title Casing (mb_title_case) -> name fields"]
            CountryMap["ISO 3166-1 alpha-2 (isocodes) -> country fields"]
            BarcodeClean["Non-numeric Stripping -> barcode fields"]
        end
        
        subgraph DynamicProperties["Dynamic Inspection Properties (on MBRelease)"]
            LangDetect["ISO-639-3 Language Detection (guess_iso_639_3)"]
            ScriptDetect["ISO-15924 Script Detection (guess_iso_15924)"]
        end
        
        MBReleaseInstance --- SetattrNormalization
        MBReleaseInstance --- DynamicProperties
    end
    
    MBReleaseInstance --> Flattener[MBRelease.flatten()]
    Flattener --> SeedForm[POST Form to musicbrainz.org/release/add]
    SeedForm --> UserMB[User completes edit on MusicBrainz]
    UserMB --> ReturnHook[Return / Confirmation Callback]
    ReturnHook --> LookupCache
```

### End-to-End Workflow Stages

1. **Authentication:**
   - Discogs API limits: 25 requests/min (unauthenticated) vs. 60 requests/min (authenticated).
   - Handled via OAuth 1.0a (`discobrain/auth.py`) or personal access tokens / key-secret pairs (`ReleaseConverter`).
   - Session credentials persist in browser/session.

2. **Input Ingestion:**
   - User submits newline-delimited Discogs URLs or release IDs via a web textarea or uploaded text file.
   - Discogs IDs are extracted via regex (`(?<=\/)\d+` or raw integer values).

3. **Lookup & Pre-Filter:**
   - Releases are queried in `MusicBrainzLookUp`.
   - Releases already linked to an MBID are excluded from the import queue and shown to the user with direct links to MusicBrainz.

4. **Release Conversion & Intrinsic Normalization:**
   - For valid IDs, raw release data is fetched from `https://api.discogs.com/releases/{id}` with rate limiting.
   - Raw JSON (`DiscogsRelease`) is parsed and mapped directly into `MBRelease` and its child dataclasses (`MBMedium`, `MBTrack`, `MBArtistCredit`, `MBLabel`, `MBEvent`).
   - **Normalization is intrinsic to `MBRelease`:** As data is added or assigned to any `MBBase` instance, `MBBase.__setattr__` automatically normalizes values upon assignment (applying `mb_title_case()` to title fields, resolving country names to ISO alpha-2 via `isocodes`, and stripping non-numeric characters from barcodes). In addition, `MBRelease` dynamically analyzes release and track titles during inspection/flattening to deduce the ISO-639-3 language and ISO-15924 script codes.
   - `MusicBrainzLookUp.get_mbids()` resolves existing Discogs artist/label URLs to MBIDs, queueing batches for resolution against `/ws/2/url`.

5. **Submission Flow:**
   - The user views pending releases on the submission page.
   - Each release provides a form targetting `https://musicbrainz.org/release/add` populated with flattened parameters (`MBRelease.flatten()`).
   - Users can submit individual releases in new tabs or trigger an automated sequential submission flow.
   - As new releases/artists are submitted, the local cache re-evaluates subsequent releases in the queue.

---

## 3. Directory & File Structure

```
discobrain/
├── discobrain/                       # Main application package
│   ├── __init__.py                   # Flask app initialization & route entrypoints
│   ├── auth.py                       # Discogs OAuth 1.0a Blueprint (/discogs)
│   ├── templates/                    # Jinja2 HTML templates
│   │   └── base.html                 # Base layout template
│   └── release_converter/            # Core conversion and MusicBrainz integration
│       ├── __init__.py               # Exports ReleaseConverter
│       ├── constants.py              # User-Agent and shared constants
│       ├── converter.py              # ReleaseConverter class, rate-limiting, mapping
│       ├── discogs.py                # Discogs TypedDicts, country & format mappings
│       ├── musicbrainz.py            # MBRelease dataclasses, flatten(), MusicBrainzLookUp cache
│       └── utils.py                  # Title casing, ISO language & script guessing
├── test/                             # Test suite and fixtures
│   ├── discogs/                      # Real Discogs release JSON payloads for offline tests
│   │   ├── 13954.json
│   │   ├── 38348.json
│   │   ├── 631758.json
│   │   └── 765433.json
│   ├── conftest.py                   # Pytest fixtures and test configurations
│   ├── test_auth.py                  # Flask auth blueprint tests
│   ├── test_discogs_to_musicbrainz.py# ReleaseConverter transformation tests
│   ├── test_musicbrainz.py           # Dataclass flattening and MusicBrainz model tests
│   ├── test_musicbrainz_lookup.py    # SQLite cache and MusicBrainz /ws/2/url lookup tests
│   ├── test_release_converter_auth.py# Authentication configuration tests
│   ├── test_utils.py                 # Language, script, and casing utility tests
│   └── utils.py                      # Test utility helpers
├── pyproject.toml                    # Project metadata, dependencies, and poe tasks
├── uv.lock                           # Locked dependency tree
└── README.md                         # Product specification and goals
```

---

## 4. Key Components Deep-Dive

### `discobrain.release_converter.converter.ReleaseConverter`
- **Session Management:** Configures `requests_ratelimiter.LimiterSession` with rate limits matching authentication status (60/min auth, 25/min unauth).
- **Discogs Auth Modes:** Supports `oauth` (OAuth1), `user_token` (`Discogs token=...`), `key_secret` (`Discogs key=..., secret=...`), or unauthenticated fallback.
- **Conversion Methods:**
  - `barcode()`: extracts and strips non-numeric characters.
  - `release_type()`: infers type (Album, EP, Single) hierarchically: from format descriptions first, then title regex, then track count.
  - `release_disambiguation()`: combines vinyl/casing attributes (e.g. "White Label", "Repress", "Orange").
  - `discogs_release_status()`: determines `official`, `promotion`, or `bootleg`.
  - `discogs_release_events()`: maps release dates and country names to ISO-3166-1 alpha-2 codes.
  - `discogs_tracklist()`: tracks mediums and multi-sided vinyl/cassettes (A/AA/B/etc.), associates track artists, and formats join phrases (`Feat.`, `&`, `,`).

### `discobrain.release_converter.musicbrainz`
- **Data Models with Intrinsic Normalization:**
  - Base class `MBBase` (`discobrain/release_converter/musicbrainz.py`) provides intrinsic normalization via `__setattr__`. Subclasses include `MBRelease`, `MBMedium`, `MBTrack`, `MBArtistCredit`, `MBName`, `MBArtistName`, `MBLabel`, `MBEvent`, `MBDate`, and `MBURL`.
  - **Automatic Normalization on Data Assignment (`MBBase.__setattr__`):**
    - **Title Casing:** Attributes in `TITLE_FIELDS` (`["name"]`) are automatically transformed via `mb_title_case(val)` when set, enforcing MusicBrainz capitalization standards (e.g., lowercasing English prepositions, articles, conjunctions, and ETI words like "remix", "original mix").
    - **Country Normalization:** Attributes in `COUNTRY_FIELDS` (`["country"]`) are mapped directly to ISO 3166-1 alpha-2 codes via `isocodes.countries.by_name_dict`.
    - **Barcode Cleaning:** Attributes in `BARCODE_FIELDS` (`["barcode"]`) automatically strip all non-numeric characters.
  - **Dynamic Language & Script Detection (`MBRelease`):**
    - `MBRelease.language` dynamically inspects the full text sample of release and track titles (`_text_sample()`) to determine the ISO-639-3 code via `guess_iso_639_3()`.
    - `MBRelease.script` inspects Unicode character block frequencies across the text sample to determine the ISO-15924 script code via `guess_iso_15924()`.
    - Both properties are automatically appended to the dictionary output during `MBRelease.flatten()`.
- **`flatten()` & `mb_dict_factory()`:** Converts nested dataclasses into dotted HTTP POST field format required by the [MusicBrainz Release Editor Seeding Protocol](https://musicbrainz.org/doc/Development/Seeding/Release_Editor) (e.g. `mediums.0.track.0.name`).
- **Special MBIDs:**
  - Various Artists: `89ad4ac3-39f7-470e-963a-56509c546377` (Discogs ID 194)
  - Unknown Artist: `125ec42a-7229-4250-afc5-e057484327fe` (Discogs ID 355)
  - Not On Label: `157afde4-4bf5-4039-8ad2-5a15acc85176`
- **`MusicBrainzLookUp`:**
  - Manages SQLite database table `cache` (`url`, `mbid`, `relationship`, `timestamp`).
  - Queries `https://musicbrainz.org/ws/2/url` (rate limited to 1 request/second).
  - Traverses release structures to enqueue and resolve Discogs artist and label URLs to native MBIDs.

### `discobrain.release_converter.utils`
- `mb_title_case(text)`: Lowercases standard English articles, prepositions, conjunctions, and ETI words ("remix", "mix") when present inside titles according to MusicBrainz style guidelines.
- `guess_iso_639_3(text)`: Language code detection based on `lingua-language-detector` (`lingua-py`), defaulting to a curated subset of 7 languages (English, French, German, Dutch, Italian, Spanish, Japanese) with support for custom language configuration.
- `guess_iso_15924(text)`: Script code detection based on Unicode character block distributions (e.g., `Latn`).

### `discobrain.auth`
- Flask Blueprint mounted at `/discogs`.
- Manages Discogs OAuth 1.0a handshake (`login` generates authorization URL; `auth` handles callback, obtains access token, and stores it in `session`).

---

## 5. Development Workflow & Commands

The project uses `uv` for package management and `poethepoet` (`poe`) as a task runner:

| Command | Action | Description |
|---|---|---|
| `uv run poe test` | `pytest` | Runs the test suite |
| `uv run poe lint` | `ruff check --fix` | Runs Ruff linter with autofixes |
| `uv run poe type` | `pyrefly check` | Runs Pyrefly static type checker |
| `uv run poe validate` | `type`, `lint`, `test` | Runs full validation pipeline |
| `uv run poe iso_free` | `isocodes locales...` | Trims unused locale files to reduce footprint |
| `uv run flask --app discobrain run` | Dev server | Starts local Flask web server |

### Environment Variables
Configure these in `.env` (or pass via environment):
- `DISCOBRAIN_SECRET_KEY`: Flask secret key (required for session handling).
- `DISCOGS_CONSUMER_KEY`: Discogs application consumer key.
- `DISCOGS_CONSUMER_SECRET`: Discogs application consumer secret.
- `DISCOGS_USER_TOKEN` / `DISCOGS_API_KEY`: Personal Discogs API token (alternative to OAuth).
- `DISCOGS_OAUTH_TOKEN`: Stored user OAuth token.
- `DISCOGS_OAUTH_TOKEN_SECRET`: Stored user OAuth token secret.

---

## 6. Implementation Status & Next Steps

### Completed
- [x] Discogs API authentication integration (OAuth 1.0a Blueprint + token/key support).
- [x] Full Discogs-to-MusicBrainz conversion pipeline (`ReleaseConverter`).
- [x] MusicBrainz release editor parameter flattening (`MBRelease.flatten()`).
- [x] MusicBrainz entity lookup and SQLite relationship cache (`MusicBrainzLookUp`).
- [x] Language, script, format, and country code normalization.
- [x] Rate limiting infrastructure (Discogs & MusicBrainz).

### Current Roadmap / To Be Built
- [ ] **Flask Web UI & Submission Controllers (`discobrain/__init__.py` + templates):**
  - Main input form accepting multiline text (URLs or IDs) or uploaded text file.
  - Discogs authentication status badge / connect button on header.
  - Processing view displaying:
    - Pre-filtered / dropped releases with direct links to MusicBrainz.
    - Converted release list with individual "Submit to MusicBrainz" seeding buttons.
    - Automatic step-through submission button ("Submit All Sequentially").
- [ ] **Dynamic Re-evaluation Loop:**
  - Before seeding a release, re-query the local cache so newly submitted artist/label MBIDs are automatically populated in subsequent releases.
- [ ] **Confirmation Callback / Seed Notifier:**
  - Capture return navigation or confirmation that a release was submitted to update the `MusicBrainzLookUp` cache with the newly created release MBID.
- [ ] **Multi-platform Extension:**
  - Abstract converter interface for future providers (Bandcamp, Beatport, etc.).

---

## 7. Guidelines & Best Practices for Agents

1. **Adhere to the Minimalist Frontend Rule:**
   - Keep JavaScript to an absolute minimum as mandated by `README.md`.
   - Prefer standard HTML forms, standard POST actions, and server-rendered templates.
2. **Preserve Rate Limits & Headers:**
   - Always ensure `USER_AGENT` (`Discobrain/0.0.1 ( email )`) is passed in HTTP requests.
   - Never bypass `requests_ratelimiter.LimiterSession`; MusicBrainz strictly enforces 1 req/sec and Discogs limits requests per minute.
3. **Type Annotations & Validation:**
   - All Python code should include accurate type hints compatible with `pyrefly`.
   - Run `uv run poe validate` before completing tasks to guarantee tests, linting, and types all pass.
4. **Mocking External APIs in Tests:**
   - MusicBrainz and Discogs external API calls must be mocked in unit tests to prevent test fragility and network-dependent failures.
   - Use JSON fixtures located in `test/discogs/` for converter test cases.
5. **Flask Secret Key in Testing:**
   - When testing views or blueprints that access `flask.session`, ensure `app.secret_key` or `app.config["SECRET_KEY"]` is set.
6. **MusicBrainz Seeding Compliance:**
   - Any modifications to `MBRelease` dataclasses or `mb_dict_factory` must preserve compatibility with the [MusicBrainz Release Editor Seeding specification](https://musicbrainz.org/doc/Development/Seeding/Release_Editor).
7. **Rely on Intrinsic Normalization in `MBRelease` & `MBBase`:**
   - Normalization is not an external pre-processing step. Do not write separate external cleaners or title-casing wrappers before populating `MBRelease` or its child objects (`MBTrack`, `MBEvent`, `MBName`).
   - Assigning values to `MBBase` instances automatically invokes `MBBase.__setattr__` for title casing, country mapping, and barcode stripping; `MBRelease` dynamically handles language and script detection upon access and flattening.
