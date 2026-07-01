# Real-data dry run — 25-26 → new pipeline

Validation exercise: run the new 26-27 pipeline (in `26-27-Season/`) against the actual 25-26 season data and diff the output against what the 25-26 script produced at the time. All raw data lived outside the repo (extracted from the source tarball into `/tmp/`); nothing PII-bearing was committed.

## Setup

1. Extracted the source tarball to `/tmp/ayso_explore/AYSO_Rosters/`.
2. Copied `24-25-Season/` and `25-26-Season/` into a working dir (`/tmp/dry_run/`).
3. Wrote `field_map.yaml` for 25-26 with the season's real form IDs (`(18939060)` for `Years of Experience`, `(18939062)` for `Player's Experience Level`).
4. Ran `26-27-Season/convert_legacy.py` (this repo) to translate each division's legacy `Pairs.txt` + `Add_AssociatedPlayers.txt` into `overrides.yaml`.
5. Ran the new pipeline: `python 26-27-Season/process.py /tmp/dry_run/25-26-Season <DIV>` per division.

## Results — three divisions covered

Each exercises a different pipeline path.

### 8UB (rating-based, 112 players, 12 teams)

| Metric | New pipeline | Original 25-26 script |
|---|---|---|
| Total players placed | 113 | 113 |
| Team count | 12 | 12 |
| Team names | 12/12 identical | — |
| Team sizes | 7×9 + 5×10 | 7×9 + 5×10 |
| Team avg rating (displayed) | matches every team | — |
| Individual (player, team) assignments matching | 45/113 (~40%) | — |

The **team-level balance is indistinguishable**. Every team has the same size and the same displayed average rating in both outputs. But ~60% of individual player placements differ — expected outcome of greedy placement with tie-breakers. Two runs with slightly different rating inputs cascade into different assignments while producing equivalent balance.

### 5U (DOB-balanced, 54 players, 6 teams)

- 54 = 54 placed
- 6 = 6 team names identical
- Zero blockers, zero warnings

Clean pass. DOB-balanced path faithful to original.

### 10UB (extras + groups, 127 players, 12 teams)

- 127 = 127 placed
- 12 = 12 team names identical (after the apostrophe fix — see below)
- Zero blockers; 7 warnings (all `cleanup_over_cap` for teams the algorithm pushed past the 10-player cap, consistent with 25-26 script behavior)

## Bugs surfaced and fixed

Three real divergences from 25-26 behavior:

1. **Cleanup pass respected the cap and BLOCKED overflow.** The original 25-26 script just placed unassigned players on the smallest team without any cap check. My port treated an over-cap placement as a `BLOCKER`. Fixed: cleanup always places (matching 25-26), logs `cleanup_over_cap` as a `WARNING` so the operator sees it but the pipeline still produces uploadable output. SportConnect accepts slightly over-cap teams in practice.

2. **`no_coach_kids` warnings noisy for Team Parents.** TP-role staff often have kids in other divisions and legitimately no children to match in their division of assignment. Demoted to `INFO` when role is TP; kept as `WARNING` for actual Coach roles where the mismatch is meaningful.

3. **Team names lost apostrophes.** `output.team_display_name()` was using `names.normalise()` to build the surname portion, which strips apostrophes as part of matching-form normalisation. That's correct for *comparing* names but wrong for *display* — e.g. `example-o'coach` became `example-ocoach`. Fixed by using a lighter display transform (lowercase only, punctuation preserved), matching the 25-26 script exactly.

All three fixes shipped in the same commits as this doc.

## What the dry run did NOT surface

- Ambiguous name matches — no case where the normalised nickname/accent match returned >1 player.
- `overrides.yaml` schema violations — the auto-conversion produced valid YAML for every division that had legacy override files.
- `field_map.yaml` key errors — form IDs looked up cleanly.
- Encoding issues — UTF-8 / latin-1 fallback handled the real exports without incident.

## Remaining known differences (not bugs)

Individual player placements diverge from the original in the rating-balanced divisions (~60% in 8UB). Root cause: the greedy placement algorithm has tie-breakers on (rating avg, age avg, size) and my rating resolution differs slightly from the original (I use the documented experience-enum fallback; the original had an opaque coefficient-of-variation heuristic that gave subtly different rating distributions). The *aggregate balance* is equivalent — same team sizes, same displayed avg ratings — but which specific kid ends up where can differ.

This is acceptable behavior: the operator gets a comparably-balanced roster with a clearer rating chain and no silent defaults. Not something to fix.

## Conclusion

Pipeline is ready for 26-27 use once the season opens and the real form IDs are known. Recommended flow when 26-27 registration opens:

1. Update `26-27-Season/field_map.yaml` — swap the `(TBD)` values for the actual AYSO 26-27 form IDs (grep any `Unallocated.txt` export for `Years of Experience` and `Player's Experience Level` to find them).
2. Drop the current-season ratings TSV into `26-27-Season/`.
3. Create `26-27-Season/<DIV>/` per division and populate with AYSO exports (`_Unallocated.txt`, `_Personnel.txt`, `_Coaches.tsv`, and — for 10U/12U — `_Extra_Allocated.csv`).
4. Author `26-27-Season/<DIV>/overrides.yaml` per division as needed (copy `overrides.example.yaml` as a template).
5. `python 26-27-Season/rosters.py 26-27-Season` — produces every `<DIV>_Teams.csv` for upload, plus per-division `validation_report.md` and `summary.md`, plus a top-level `season_summary.md`.
6. Read `season_summary.md` first for at-a-glance ready/blocked status.

If any historic-format overrides ever need to be migrated forward, `26-27-Season/convert_legacy.py <SEASON_DIR>` handles it.
