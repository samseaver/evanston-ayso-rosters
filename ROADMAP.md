# 26-27 redesign roadmap

Where the new pipeline is going, in roughly the order things need to land. The analysis behind these choices lives in `REVIEW.md` §6 — this doc is the actionable shortlist, designed to be shared as a one-pager.

## Why a fresh start

Two seasons of incremental patches (see the 24-25 → 25-26 evolution in `REVIEW.md` §1) made the existing script harder to reason about, not easier. Form-field IDs are hardcoded and change every season; warnings vanish into stdout; manual overrides live in three different ad-hoc formats. 26-27 is the cut-over to a config-driven, fail-loud pipeline with one entrypoint and one schema for human overrides.

## Status legend

`[x]` done   `[~]` in progress   `[ ]` planned

## Phase 1 — Foundations (config-driven, fail-loud)

- `[~]` **`field_map.yaml` per season** — semantic names for AYSO's volatile column headers and per-season filenames. Updating IDs becomes a config edit rather than a code change, and a missing key fails at startup. (Scaffold landed; consumed once the new script exists.)
- `[~]` **`overrides.yaml` per division** — single schema replacing `Pairs.txt` + `Add_AssociatedPlayers.txt` + the `Team` column in `Extra_Allocated.csv`, and folding in 24-25's standalone `requests.txt` notes. One file, one parser, one validation pass. (Template scaffolded at `26-27-Season/overrides.example.yaml`; consumed once the new script exists.)
- `[x]` **Schema validation at startup** — `26-27-Season/validate.py`. Stand-alone CLI (`python validate.py [SEASON_DIR]`) plus importable `load_field_map()` / `load_overrides()` for the future processing script. Three tiers: `[OK]` / `[BLOCKER]` (non-zero exit) / `[WARNING]`. Catches malformed YAML, missing required keys, wrong types, unknown override sections (typo detection), and `(TBD)` form IDs still in `field_map.yaml`.

## Phase 2 — Pipeline

- `[ ]` **Normalised name matching** — lowercase + accent strip + collapse whitespace + drop parenthetical annotations + nickname table, replacing the current substring `find_player`. Ambiguous matches (0 or >1 candidates) emit an actionable line pointing at `overrides.yaml`.
- `[ ]` **Structured `validation_report.md` per division** — replaces the current scattered `print` warnings. Severities: BLOCKER (script will produce wrong output), WARNING (proceeded but check), INFO (overrides used). Non-zero exit on any BLOCKER.
- `[ ]` **One `assemble_teams(balance_by=...)` function** — replaces the parallel 5U/6U DOB-balanced and 8U+ rating-balanced code paths. Single tested function, parameterised.
- `[ ]` **Drop the coefficient-of-variation rating fallback** — replace with documented rules: previous-season rating → experience enum → `needs_rating.md` (player surfaced for human assignment). No silent defaults.

## Phase 3 — Outputs

- `[ ]` **Per-division `<DIV>_summary.md`** replacing the byproduct trio (`_Ratings.tsv`, `_Team_Ratings.tsv`, `_Extra_Teams.txt`). Human-readable team breakdown, balance metrics, override usage, warning summary. The `_Teams.csv` SportConnect upload artifact stays unchanged.
- `[ ]` **Top-level `season_summary.md`** — every division listed as `ready` / `has warnings` / `blocked`. At-a-glance "what's safe to upload right now".

## Phase 4 — Workflow

- `[ ]` **Single entrypoint** — `python rosters.py 26-27-Season` runs every division; `--only DIV` for iteration. Exits non-zero if any division has BLOCKERs.
- `[ ]` **Slim the wide exports at load time** — Personnel has 96 columns; the script reads 5. Unallocated has 50; the script reads ~10. Drop everything else at the loader, keeping the originals on disk for forensics.

## Out of scope (acknowledged ceilings)

- **SportConnect upload stays manual.** No API. Every simplification above pays off in everything *upstream* of that final manual step.
- **Coaches.tsv → Google Sheet integration** — possible later if it's actually hand-maintained in a sheet; pending the answer to open question 1 below.

## Open questions blocking decisions

(Restated from `REVIEW.md` §7 so this doc stands alone.)

1. Which inputs are hand-edited each season vs pure AYSO exports? (Determines what becomes config vs what gets re-derived.)
2. Does SportConnect accept a combined multi-division upload, or strictly one CSV per division? (Determines whether a single `season_teams.csv` is worth producing.)
3. Any team-size / EXTRA-distribution rules from AYSO that aren't currently in code? (The 24-25 "first six 10UB teams ≤ 6 players" looked rule-derived — should be encoded explicitly.)
4. How often do the AYSO form-field IDs really change? (Answer raises or lowers Phase 1 priority.)
5. Should the accessibility / coach-preference notes in `requests.txt` flow into `overrides.yaml`, or stay as human-reference only?
