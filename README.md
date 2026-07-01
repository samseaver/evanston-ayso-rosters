# Evanston AYSO Rosters

Tools and notes for compiling the Evanston AYSO team rosters each season, across divisions 5U through 14U (both boys and girls). The end product is a per-division CSV that is uploaded manually into SportConnect (AYSO does not provide an API).

## No personal information in this repo

The source data — player names, emails, phone numbers, parent contacts, accessibility notes — never lives in the repo. It stays in a local tarball that is `.gitignore`d. Any example names that appear in the docs are obvious placeholders (`Player A`, `Coach One`, `coach1/coach2/coach3`).

If you spot a real name anywhere in the tracked files, please open an issue or DM the maintainer.

## What's here

- **`SEASON_SETUP.md`** — start here if you're running the pipeline for a new season. Short, action-oriented, written for a busy parent volunteer.
- **`REVIEW.md`** — written review of the 24-25 and 25-26 seasons: input file formats, how the processing pipeline works, where the rough edges are, and a categorised list of simplification opportunities. Read this if you want the background.
- **`ROADMAP.md`** — actionable shortlist of what's been built for the 26-27 redesign, with phase status. All six phases are now `[x]` complete.
- **`REAL_DATA_DRY_RUN.md`** — validation exercise: the new pipeline was run against every 25-26 division and matches the original 25-26 script's placement counts exactly.
- **`24-25-Season/`, `25-26-Season/`** — the scripts as they were run those seasons. Kept as historical reference; not actively maintained.
- **`26-27-Season/`** — the active redesign. `rosters.py` is the entry point.
