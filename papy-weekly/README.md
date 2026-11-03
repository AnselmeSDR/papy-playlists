# Papy Weekly routine

Scripts used by the cloud routine "Spotify - papy-weekly-playlist" (claude.ai/code/routines),
which rebuilds the "Papy Weekly" playlist every Monday with 100 discovery tracks.

| File | Role |
|---|---|
| `rules.py` | Exact quotas per genre, genre guards, normalisation (shared) |
| `reco.py` | Recommender: expands the user's seed artists through Deezer related artists (no API key), ranks candidates by how many seeds lead to them, penalises known / recently proposed artists, picks one track per artist |
| `validate.py` | Gatekeeper: exact quotas, 1 track per main artist, exclusions, genre guards, discovery share. Nothing is written to Spotify without `PASS` |

Why Deezer: Spotify blocks recommendations (404), other users' playlists (403) and artist
genres for development-mode apps. Tracks are mapped back to Spotify by ISRC.

Network: the cloud environment must reach `api.deezer.com` (otherwise the routine falls back
to the model's own knowledge and says so in its report).

Local dry run (no Spotify write): put `seeds.json`, `known.txt`, `recent.txt`, `exclude.txt`
in a folder, then `python3 reco.py <folder>` and `python3 validate.py <folder>`.
