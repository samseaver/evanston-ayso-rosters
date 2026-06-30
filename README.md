# Evanston AYSO Rosters

Tools and notes for compiling the Evanston AYSO team rosters each season, across divisions 5U through 14U (both boys and girls). The end product is a per-division CSV that is uploaded manually into SportConnect (AYSO does not provide an API).

## No personal information in this repo

The source data — player names, emails, phone numbers, parent contacts, accessibility notes — never lives in the repo. It stays in a local tarball that is `.gitignore`d. Any example names that appear in the docs are obvious placeholders (`Player A`, `Coach One`, `coach1/coach2/coach3`).

If you spot a real name anywhere in the tracked files, please open an issue or DM the maintainer.

## What's here

- **`REVIEW.md`** — written review of the 24-25 and 25-26 seasons: what files exist, how the processing pipeline works, where the rough edges are, and a categorised list of simplification opportunities.
- **`ROADMAP.md`** — the actionable shortlist of what's being built for the 26-27 redesign, with phase ordering and status.
- **`24-25-Season/`, `25-26-Season/`** — the scripts as they were actually run those seasons. Kept as historical reference; not actively maintained.
- **`26-27-Season/`** — the active redesign. Currently just config scaffolding; the new processing script will land here as the roadmap is worked through.
