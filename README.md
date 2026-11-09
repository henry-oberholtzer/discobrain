# Discobrain

This is a local web application for easily submitting large amounts of releases to MusicBrainz.

It aims to handle as much data conversion as possible before seeding the release, and stores
connections between artist URLs and IDs on other sites and on MusicBrainz.

The frontend is minimal, with as little JavaScript as possible.

# User Experience

Currently, the application is limited to importing releases from Discogs, but will eventually
expand to supporting other sites.

### Set Up

When the application opens, the main page displays an option to authenticate with Discogs
to improve API access speeds. The credentials are stored on the browser.

There is a textbox where a user can paste a list of Discogs URLs or release IDs, with each being on a new line.

Alternatively, a text file matching the same requirements can be uploaded.

Upon clicking "parse" the submission flow is started.

### Backend Work

All given release IDs are checked against MusicBrainz or in the local cache managed by MusicBrainzLookup,
ones that already exist are dropped from futher processing.

Releases are fetched from Discogs and converted into MBRelease objects with the ReleaseConverter class.

### Submission Flow

The user is redirected to a page to start the submissions.

The page displays a list with buttons to submit each release processed, opening the seeded data submission in a new tab.

The page also shows releases that have been dropped as they already exist on MusicBrainz, with a direct link to the MB page.

There is also a button to automatically iterate through all submissions to the MusicBrainz webpage to complete the submission of the seeded data.

Each release is re-evaluated for MB ids before it is seeded, in case a previous release already submitted certain artist IDs.

The application recieves notice that the release has been seeded, and stores that in the MusicBrainzLookup cache.

The user is directed to the next MusicBrainz release page with seeded data, and this repeats.

After completing all submissions, the user is then re-directed to the home page to start again.




