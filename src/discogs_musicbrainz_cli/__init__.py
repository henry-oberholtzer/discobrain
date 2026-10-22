import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
            prog=sys.argv[0],
            description="Interactive CLI for importing Discogs releases to MusicBrainz"
            )
    parser.add_argument("discogs_id")
