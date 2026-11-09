# Discobrain

This is a local web application for easily submitting large amounts of releases to MusicBrainz.

It aims to handle as much data conversion as possible before seeding the release, and stores
connections between artist URLs and IDs on other sites and on MusicBrainz.

# User Experience

Currently, the application is limited to importing releases from Discogs, but will eventually
expand to supporting other sites.

When the application opens, the main page displays an option to authenticate with Discogs
to improve API access speeds. The credentials are stored on the browser.

There is a textbox where a user can paste a list of Discogs URLs or release IDs, with each being on a new line.

Alternatively, a text file matching the same requirements can be uploaded.

Upon clicking "parse" the submission flow is started.

All given release IDs are checked against MusicBrainz or in the local cache managed by MusicBrainzLookup,
ones that already exist are dropped from futher processing.

First releases are fetched from Discogs and and converted into MBRelease objects with the ReleaseConverter class.

Then the user is redirected to a start page to begin the import flow, which also shows releases that have been dropped
as they already exist on MusicBrainz.

The user is re-directed to the MusicBrainz webpage to complete the submission of the seeded data.

Once the user has finished, the return URL provided in the seeded data will send them back to the application.

The application recieves notice that the release has been seeded, and stores that in the MusicBrainzLookup cache.

Then the user is directed to the next MusicBrainz release page with seeded data, and this repeats.

After completing all submissions, the user is then re-directed to the home page to start again.




