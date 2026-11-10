# Discobrain

This is a local web application for easily submitting large amounts of releases to MusicBrainz.

It aims to handle as much data conversion as possible before seeding the release, and stores
connections between artist URLs and IDs on other sites and on MusicBrainz.

## Prerequisites

- **Python**: >= 3.12
- **uv**: Python package and environment manager ([installation guide](https://docs.astral.sh/uv/))

## Setting Up for Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/henry-oberholtzer/discobrain.git
   cd discobrain
   ```

2. **Install dependencies:**
   Install project dependencies and development tools using `uv`:
   ```bash
   uv sync
   ```

3. **Configure environment variables:**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to configure your settings:
   - `DISCOBRAIN_SECRET_KEY`: Secret key used for Flask session security.
   - **Discogs Authentication (choose one):**
     - **Personal Access Token:** Set `DISCOGS_USER_TOKEN` (generate one at [Discogs Developer Settings](https://www.discogs.com/settings/developers)). This raises your Discogs API rate limit from 25 to 60 requests per minute.
     - **OAuth 1.0a Application:** Set `DISCOGS_CONSUMER_KEY` and `DISCOGS_CONSUMER_SECRET` with the OAuth callback URL set to `http://localhost:5000/discogs/auth`.
   - `DISCOBRAIN_DB` *(optional)*: Custom path for SQLite database (defaults to `instance/discobrain.db`).

4. *(Optional)* **Optimize locale data:**
   Trim unused `isocodes` locale files to reduce disk footprint:
   ```bash
   uv run poe iso_free
   ```

## Running Locally

1. **To start the Flask development server:**
   ```bash
   uv run flask --app discobrain run
   ```

2. **Open the web application:**
   Visit [http://localhost:5000](http://localhost:5000) in your browser.

3. **Using the application:**
   - Enter Discogs release URLs or numeric IDs into the text area (one per line) or upload a `.txt` file.
   - Discobrain will pre-filter releases already in MusicBrainz, fetch metadata for unseeded releases, and normalize fields according to MusicBrainz standards.
   - Seed releases to MusicBrainz individually or step through them sequentially.

## Running Tests & Code Quality Checks

This project uses [poethepoet](https://github.com/nat-n/poethepoet) (`poe`) as a task runner and [pytest](https://docs.pytest.org/) for testing:

- **Run the test suite:**
  ```bash
  uv run poe test
  ```
  *(Or run pytest directly: `uv run pytest`)*

- **Run a specific test file:**
  ```bash
  uv run pytest test/test_webapp.py
  ```

- **Run static type checking:**
  ```bash
  uv run poe type
  ```
  *(Runs `pyrefly check`)*

- **Run linter with autofixes:**
  ```bash
  uv run poe lint
  ```
  *(Runs `ruff check --fix`)*

- **Run the complete validation pipeline:**
  ```bash
  uv run poe validate
  ```
  *(Runs type checking, linting, and tests in sequence)*

## AI Disclosure

AI models were used to generate code in this repository.

All code has been reviewed manually & responsibility for it is held by the maintainer.
