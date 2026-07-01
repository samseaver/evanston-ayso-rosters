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

- `[x]` **Normalised name matching** — `26-27-Season/names.py`. Lowercase + accent strip + collapse whitespace + drop parenthetical annotations + nickname table (bob/robert, liz/elizabeth, etc.). Wired into assembly.py for coach→child resolution and group/override player-name matching. Ambiguous matches log a BLOCKER pointing at `overrides.yaml`. 25 unit tests.
- `[x]` **Structured `validation_report.md` per division** — `26-27-Season/report.py` formats the assembly log into markdown with BLOCKER / Warnings / Notes sections plus a status line (`READY` / `BLOCKED`). Written by `process.py` alongside the Teams.csv. Non-zero exit on any BLOCKER. 5 unit tests.
- `[x]` **`assemble_teams(balance_by=...)` in `26-27-Season/assembly.py`** — both rating-based (8U–14U) and DOB-balanced (5U/6U) paths implemented behind a single function. Auto-infers `balance_by` from division but accepts an explicit override. DOB path balances by oldest-first sort with same-gender count as the placement metric. 5U fixture exercises the DOB path end-to-end; full e2e produces 3+3 split with gender balance.
- `[x]` **Drop the coefficient-of-variation rating fallback** — replaced by `26-27-Season/ratings.py`: current TSV → previous TSV → experience enum → `None`, with `needs_rating` list surfaced as BLOCKERs. EXTRA-league floor of 4 still applied. No silent defaults.

## Phase 3 — Outputs

- `[x]` **Per-division `<DIV>_summary.md`** — `26-27-Season/summary.py`. Replaces the `_Ratings.tsv` + `_Team_Ratings.tsv` + `_Extra_Teams.txt` byproduct trio with one markdown artifact: status header, per-team breakdown (coaches, player table with ratings/ages/gender, balance metrics), overrides-used section, pointer to the Teams.csv and validation_report.md. Written by `process.py` alongside the other outputs.
- `[x]` **Top-level `season_summary.md`** — every division as a row in one markdown table (status, team count, player count, blocker/warning/note counts). Written by `rosters.py` after the batch completes. "Overall" line says READY across the board or names which divisions need attention.

## Phase 4 — Workflow

- `[x]` **Single entrypoint** — two complementary entry points: `26-27-Season/process.py SEASON_DIR DIVISION` for one division, `26-27-Season/rosters.py SEASON_DIR [--only DIV] [--skip DIV]` for the full multi-division batch. The batch runner reports per-division status and exits non-zero if any division is BLOCKED or FAILED — no need to scan output for warnings.
- `[x]` **Slim the wide exports at load time** — `26-27-Season/loaders.py` reads only the columns the pipeline uses, returning typed dataclasses (`Player`, `Volunteer`, `CoachAssignment`). Originals stay on disk untouched for forensics.

## Phase 5 — Feature parity with 25-26

- `[x]` **EXTRA-league loader** — `loaders.load_extras()` reads `<DIV>_Extra_Allocated.csv`; `process.py` matches names against the division roster and passes the resolved player-IDs to `assembly.assemble_teams()` (which already applies the rating-4 floor and lowest-balance placement). Unmatched EXTRA names log a WARNING; ambiguous matches log a BLOCKER. 10UB fixture with a deliberately-missing EXTRA player exercises the warning path end-to-end.
- `[x]` **Legacy override migration** — `26-27-Season/convert_legacy.py <SEASON_DIR>` translates each division's `<DIV>_Pairs.txt` + `<DIV>_Add_AssociatedPlayers.txt` into a `<DIV>/overrides.yaml`. Enables running the new pipeline against historic seasons for validation.

## Phase 6 — Real-data validation

- `[x]` **Dry run against real 25-26 data** — ran the new pipeline end-to-end against three divisions (8UB rating path, 5U DOB path, 10UB extras path). Full write-up in `REAL_DATA_DRY_RUN.md`. Team-level balance matches original exactly (same team names, sizes, displayed avg ratings); three real algorithm-faithfulness bugs surfaced and fixed:
  - `cleanup_over_cap` warning (instead of blocker) when placement pushes a team past the division cap — matches 25-26 behavior; SportConnect accepts.
  - `no_coach_kids` demoted to INFO for Team-Parent roles (their kids often live in other divisions); WARNING preserved for actual coaches.
  - Team-name display preserves apostrophes and other punctuation (`names.normalise()` was correct for matching but wrong for display).

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
