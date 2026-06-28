# AYSO Rosters — Archive Review

A read of the `AYSO_Rosters.tar.gz` archive in this folder, covering the **24-25** and **25-26** seasons of compiling Evanston AYSO team rosters across divisions **5U → 14U** (both boys and girls). The end goal of the pipeline is a per-division roster file uploaded **manually into SportConnect** (no API). This document describes what's in the archive and proposes concrete simplifications for the next season.

> Scope note: the tarball was extracted to `/tmp/ayso_explore/AYSO_Rosters/` during this review; nothing in the project folder was modified. Remove with `rm -rf /tmp/ayso_explore` when done.

---

## 1. Overview

The archive contains two seasons of identical structure, with one Python script per season doing the heavy lifting:

```
AYSO_Rosters/
  24-25-Season/
    process_personnel_and_players.py       # 464 LOC, run once per division
    2024_Player_Ratings.tsv                # season-wide coach ratings
    Volunteer_Details.csv                  # season-wide volunteer roster
    requests.txt, Waitlist.csv             # season-wide one-offs (24-25 only)
    5U/ 6U/ 8UB/ 8UG/ 10UB/ 10UG/ 12UB/ 12UG/ 14UB/ 14UG/
        <DIV>_Coaches.tsv                  # coach → tentative team
        <DIV>_Personnel.{txt,xlsx}         # volunteer registration export
        <DIV>_Unallocated.{txt,xlsx}       # all registered players in division
        <DIV>_Pairs.txt                    # manual sibling/friend pairings (opt.)
        <DIV>_Extra_Allocated.csv          # 10U/12U EXTRA tryout placements
        <DIV>_Teams.csv                    # OUTPUT: SportConnect upload
        <DIV>_Ratings.tsv                  # OUTPUT: per-player audit
        <DIV>_Team_Ratings.tsv             # OUTPUT: per-team avg rating
        <DIV>_Problems.txt                 # OUTPUT: warning log (24-25 only)

  25-26-Season/
    process_personnel_and_players.py       # 518 LOC, evolved from 24-25
    check_coaches.py                       # 42 LOC, validates Coaches.tsv vs Personnel
    2025_Player_Ratings.tsv
    Volunteer_Details.{txt,xlsx}           # CSV replaced by txt/xlsx pair
    latest-all-teams-names-divisions.txt
    latest-latest-all-teams-names-divisions.txt
    14U/14U_Volunteers.xlsx                # combined 14U volunteer file
    <DIV>/
        <DIV>_Coaches.tsv
        <DIV>_Personnel.{txt,xlsx}
        <DIV>_Unallocated.{txt,xlsx}
        <DIV>_Unallocated-New.{txt,xlsx}   # NEW: late-registration delta
        <DIV>_Pairs.txt
        <DIV>_Extra_Allocated.csv
        <DIV>_Add_AssociatedPlayers.txt    # NEW: manual coach→child override
        <DIV>_Teams.csv                    # OUTPUT
        <DIV>_Ratings.tsv                  # OUTPUT
        <DIV>_Team_Ratings.tsv             # OUTPUT
        <DIV>_Extra_Teams.txt              # OUTPUT (10U/12U only)
```

### What changed between seasons

| Area | 24-25 | 25-26 |
|---|---|---|
| Coach → child matching | Substring `find_player()` over parent names | Three-tier: `parents_singles` → `Add_AssociatedPlayers.txt` → `associatedPlayers` field in Personnel |
| Player rating fallback | Coefficient-of-variation on years of experience | Previous-season TSV lookup → experience enum (competitive/recreational/none) |
| Extra player tracking | Plain list | Dict with original-team metadata |
| Problems log | `*_Problems.txt` per division | Removed — warnings still printed but not collected |
| Late registrants | n/a | `*_Unallocated-New.*` delta files |
| Coach validation | n/a | Standalone `check_coaches.py` |
| Volunteer export | Single CSV | TXT + XLSX duplicate (and 14U has its own XLSX) |
| Season-wide artifacts | `requests.txt`, `Waitlist.csv` | `latest-...-teams-...-divisions.txt` pair |

The 25-26 script is strictly an evolution of 24-25 — same skeleton, more conditionals around the rough edges.

---

## 2. Input files

### Per-division inputs

**`<DIV>_Personnel.{xlsx,txt}` — volunteer registration export**
- 96+ columns wide. Many fields are nested by role: `Photo(Head Coach)`, `Concussion Awareness(Referee)`, `SafeSport(Team Parent)`, etc., each with `Verified` / `Not Verified` / `Not Uploaded`.
- Only a handful of columns are actually read: `Team Personnel Name`, `Team Personnel Role`, `VolunteerID`, `VolunteerTypeId`, and (in 25-26) `associatedPlayers`.
- `associatedPlayers` is a comma-separated free-text field where the volunteer (during registration) lists their kid(s). Format is inconsistent: sometimes `Player A, Player B`, sometimes parenthetical age annotations like `Player A (13)`.
- Both `.xlsx` and `.txt` versions appear — the `.txt` is the script's input; the `.xlsx` is a redundant convenience copy.

**`<DIV>_Unallocated.{txt,xlsx}` — registered players for the division**
- 50+ columns. The script reads: `PlayerID`, `Player Name`, `Age`, `Date Of Birth`, `Gender`, `Parent FirstName/LastName`, `Secondary Contact FirstName/LastName`, `Division Price Payment Status`, plus two form-id columns whose IDs change every season:
  - `Player's Experience Level(14698164)` → `(18939062)` in 25-26
  - `Years of Experience:(14698163)` → `(18939060)` in 25-26
- "Unallocated" is misleading — by the time the script runs, these are *all* registered players in the division, not just the ones still unassigned.
- 25-26 adds a `*_Unallocated-New.*` variant. From the file sizes (e.g. 8UB: 22 lines vs. 113 lines) this is the delta of late registrants pulled separately.

**`<DIV>_Coaches.tsv` — coach → team assignment from a side spreadsheet**
- Columns: `Team`, `First Name`, `Last Name`, `Role`, `Coaching/Volunteer Partner`, `experience?`, `Solo/Paired`, `Tentative Team`, `Notes`.
- This is the file you maintain by hand (or near-hand) — names here often don't match the AYSO Personnel export exactly. `Team` values are short labels (`Tm 1`, `Tm 2`, `TBD`).
- `Role` values seen: `Coach`, `TP`, `TP (Team Parent)`, `TP--not signed up`.

**`<DIV>_Pairs.txt` — manual buddy/sibling pairs (optional)**
- One pair per line, tab-separated: `Player A\tPlayer B`.
- Bidirectional in the script (placing A places B). One name can appear on multiple lines.
- Found in 10U and 12U divisions only.

**`<DIV>_Extra_Allocated.csv` — 10U/12U EXTRA league players**
- Columns: `(blank)`, `Player First Name`, `Player Last Name`, `Account First Name`, `Account Last Name`, `Email`, `Cell Phone`.
- These are the kids who tried out and made the EXTRA league; the script's job is to spread them across the rec teams.
- 25-26 adds a `Team` column where you can pre-assign a specific EXTRA team.

**`<DIV>_Add_AssociatedPlayers.txt` — manual coach→child override (25-26 only)**
- Columns (tab-separated, 4 cols, sometimes prefixed with a row #): `Coach First`, `Coach Last`, `Player First`, `Player Last`.
- Escape hatch used when the automatic three-tier match fails — e.g. coach uses a different first name in AYSO than on the Coaches spreadsheet, or the kid isn't linked under their account.

### Season-level inputs

**`YYYY_Player_Ratings.tsv`** — coach-submitted skill ratings from the prior season.
- 24-25 cols: `Team`, `Player First`, `Player Last`, `Rating`, `Notes`, `Player Birth Date`.
- 25-26 cols: `Team Name`, `Player First`, `Player Last`, `Rating`. (Notes and Birth Date dropped.)
- `Rating` is a string like `4 - Strong (~20% of players); able to make plays...`. The script parses the leading integer 1–5.

**`Volunteer_Details.{csv,xlsx,txt}`** — program-wide volunteer roster across divisions.
- 41 columns. Same person can appear multiple rows (one per role/team). Includes the verification/training fields again.
- 24-25 is `.csv`; 25-26 ships **all three** of `.csv`, `.xlsx`, `.txt` for the same data.
- Not read by the script — appears to be an admin-facing artifact.

**`14U/14U_Volunteers.xlsx` (25-26 only)** — a 14U-specific volunteer export at the `14U/` level (not `14UB/` or `14UG/`). Suggests 14U is sometimes treated as one combined division administratively.

**`requests.txt` (24-25 only)** — free-text family requests like *"Clement has complete hearing loss in his right ear and wears a hearing aid…"*. Two-column TSV (player name → narrative). Not read by the script — referenced by the operator when sanity-checking placements.

**`Waitlist.csv` (24-25 only)** — players registered after teams closed; informational.

**`latest-all-teams-names-divisions.txt` and `latest-latest-all-teams-names-divisions.txt` (25-26)** — final team-name manifests. The double-`latest` suggests an after-the-fact revision; both files are kept.

### What's noisy here

- **Format duplication**: every Personnel and Unallocated file ships as both `.xlsx` and `.txt`, and Volunteer_Details in 25-26 ships as three formats. Only one is read; the others are just visual confirmation.
- **Field-id volatility**: AYSO's form field IDs (`(14698164)`, `(14698163)`) are embedded in column headers and change every season. The script silently `KeyError`s if you forget to update them.
- **Wide-and-sparse**: Personnel has 96 columns of which the script reads 5; Unallocated has 50 of which it reads ~10. Every season you stare at columns that don't matter.

---

## 3. Processing pipeline

### `process_personnel_and_players.py` — run once per division

Invocation: `python process_personnel_and_players.py 10UB`. The script loads everything for that division, then does a three-phase team assembly.

**Phase 0: Load and key everything by `(last_name, first_name)` tuple (lowercased)**

- Players come from `<DIV>_Unallocated.txt`; key = `(player_ln, player_fn)`.
- A `parents_singles` dict is built mapping `(parent_first, parent_last)` → list of their kids in this division. Same for `Secondary Contact`. This is the "find the coach's children" lookup.
- Ratings are resolved in this order:
  1. `2025_Player_Ratings.tsv` (current season).
  2. `2024_Player_Ratings.tsv` (previous season — only in 25-26).
  3. Experience-level enum: *Has played competitive soccer* → 4, *recreational* → 3, *no/limited* → 2.
  4. Fallback heuristic (24-25 only): `rating = min(3 + int(years_experience - coeff_var), 5)`, where `coeff_var = mean_experience / std_experience` over the division. *This is the opaque one — dimensions don't line up and the intent is unclear from the code.*

- Coaches come from `<DIV>_Coaches.tsv`; they're attached to the team index from the `Team` column (`Tm 1`, `Tm 2`, `TBD` skipped).

- Coach metadata (VolunteerID, role) comes from `<DIV>_Personnel.txt`, matched on lowercase `Team Personnel Name`. If a coach isn't found, the script prints `Coach Missing in Personnel Data: <name>` and silently drops them from the output rows.

**Phase 1: Place coach kids and their pair-mates**

For each coach, find their children via this chain:

```
24-25:                          25-26:
  parents_singles lookup          parents_singles lookup
  ↓ (else)                        ↓ (else)
  find_player(coach_name)         Add_AssociatedPlayers.txt
  (substring match on             ↓ (else)
   parent names)                  Personnel.associatedPlayers field
                                   ↓ (none)
                                  print warning, skip
```

The 24-25 `find_player` is a substring check: it returns any player whose `Parent FirstName` AND `Parent LastName` are both substrings of the coach's full name. False-positive prone (a "Bob Smith" coach matches a "Bob Johnson Smith" parent). 25-26 replaces this with explicit lookups but keeps `find_player` around as a vestigial fallback.

Each placed kid drags any `Pairs.txt` mate onto the same team.

**Phase 2: Place EXTRA league players (10U/12U only)**

Loop over `<DIV>_Extra_Allocated.csv`, place each EXTRA kid into the team with the lowest *current average rating × age × headcount* (sorts on a 4-tuple). EXTRA kids get a rating floor of `max(4, current_rating)` so they reliably skew the balance math.

In 24-25, an additional hardcoded constraint capped the first six 10UB teams at 6 players for this phase. 25-26 dropped that and uses the standard `c_max_players` cap throughout.

**Phase 3a: Above-average players, biggest-first**

Sort remaining players by rating descending. For each, place them on the team currently *lowest* in (avg rating, avg age, headcount). Cap: team size ≤ `c_max_players / 2` for this phase.

**Phase 3b: Below-average players, lowest-first**

Same loop with the sort reversed. Cap: team size ≤ `c_max_players`.

**Phase 4: Cleanup**

Any player still unassigned (usually because their sibling chain couldn't fit anywhere) gets dumped into the smallest team. A `WARNING: UNASSIGNED PLAYERS` line is printed if there are any.

**5U/6U special case**: no ratings, no EXTRA league. Balance is by **DOB** (oldest first) with a gender-balance tiebreaker. Same script, different branch.

**Team-size caps by division**: 5U/6U=10, 8U=9, 10U=10, 12U=12, 14UB=16, 14UG=10.

### `check_coaches.py` (25-26 only)

Forty-two lines. Reads `<DIV>_Coaches.tsv` and `<DIV>_Personnel.txt`, prints any coach whose name isn't in Personnel. Effectively a pre-flight check to spot the most common cause of the "Coach Missing in Personnel Data" warning before you run the main script.

---

## 4. Output files

| File | Format | Loaded into SportConnect? | Purpose |
|---|---|---|---|
| `<DIV>_Teams.csv` | CSV | **Yes** | Final roster: `TeamName, PlayerID, VolunteerID, VolunteerTypeID, Player Name, Team Personnel Name, Team Personnel Role` |
| `<DIV>_Ratings.tsv` | TSV | No | Per-player audit: `Team, Player Name, Rating, InExtra, [ExtraTeam in 25-26]` |
| `<DIV>_Team_Ratings.tsv` | TSV | No | Per-team avg rating, for visually verifying balance |
| `<DIV>_Extra_Teams.txt` | text | No | Which teams ended up with EXTRA players (10U/12U) |
| `<DIV>_Problems.txt` (24-25 only) | text | No | Per-division warning log |
| `24-25-Season/Example_Output_8UG.tsv` | TSV | n/a — reference | Format template showing what a "good" roster looks like, ratings inline |
| `Waitlist.csv` (24-25) / `latest-...-divisions.txt` (25-26) | varies | No | Season-level admin artifacts |

`Example_Output_8UG.tsv` is a 3-column reference (`TeamName \t player name \t rating`), distinct from the 7-column `<DIV>_Teams.csv` actually written by the script. Looks like it was an early-stage manual prototype that never got cleaned up.

---

## 5. Pain points & fragility

These are observations from reading the two seasons of code; they map directly to the recommendations in §6.

- **Name matching is substring-only**. No fuzzy match, no nickname table, no accent stripping. `Patrick Smith` vs `Pat Smith` vs `Patrick J. Smith` all need manual reconciliation.
- **Form field IDs leak into headers** and change every season. The script hardcodes `Player's Experience Level(14698164)` — if AYSO ships a new ID, you get a silent `KeyError` or, worse, the column is just absent and everything downstream gets a default value.
- **Silent failures everywhere**. `print()` then `continue`:
  - Missing pair-mate in `Pairs.txt` → "Missing Special Player" → keeps going.
  - EXTRA player not in `Unallocated.txt` → warning commented out entirely.
  - Coach not in Personnel → coach row simply omitted from output CSV.
  - Unassigned player at the end → one warning line, still writes the CSV.
  These all print to stdout interleaved; nothing structured, nothing aggregated, no exit code.
- **Format duplication doesn't help anyone**. The `.xlsx` and `.txt` siblings drift; you have to remember which one is canonical.
- **Manual override files have no schema**. `Pairs.txt`, `Add_AssociatedPlayers.txt`, `Extra_Allocated.csv` each have their own ad-hoc format. The parser crashes on extra whitespace or a missing tab. Two override files cover overlapping ground (`Pairs.txt` for sibling pairs, `Add_AssociatedPlayers.txt` for coach→child).
- **Coefficient-of-variation rating fallback** in 24-25 is genuinely unclear — dimensional analysis doesn't work (coeff_var is unitless, you're subtracting it from a year count, then adding to a "3"). 25-26 dropped it in favor of the explicit enum, but the function is still there.
- **5U/6U is a parallel code path** with its own balance logic embedded inside the same function — `if "5U" in DIVISION or "6U" in DIVISION:` branches scattered throughout.
- **Tuple-key bugs waiting to happen**. The script flips `(first, last)` ↔ `(last, first)` in five or six places. Each new file format requires one more `tuple(reversed(...))`.
- **Per-division invocation**. Ten divisions = ten invocations = ten times you check the warnings. The 24-25 `_Problems.txt` files were the start of fixing this, but 25-26 dropped them.

---

## 6. Simplification opportunities

Grouped so each chunk is reactable on its own. Listed roughly in order of ROI for the effort involved.

### A. Inputs (highest leverage)

**A1. Pick one canonical export format per file class and stop syncing the others.**
The duplicate `.xlsx`/`.txt` mirrors aren't load-bearing — the script reads `.txt` everywhere. Decide: keep `.txt` (TSV-friendly, diff-able) and delete the `.xlsx` mirrors from your workflow. Same for `Volunteer_Details` (currently 3 formats in 25-26).

**A2. Move season-specific field IDs into a `field_map.yaml`.**
Today the script has `line["Player's Experience Level(14698164)"]` hard-coded. Replace with a thin loader that reads:
```yaml
# 25-26-Season/field_map.yaml
years_experience: "Years of Experience:(18939060)"
experience_level: "Player's Experience Level(18939062)"
```
Updating the IDs each season becomes a 30-second config edit instead of a code change, and a missing key fails loudly at startup instead of silently mid-run.

**A3. Collapse the manual-override files into one `overrides.yaml` per division.**
Today there are three separate ad-hoc formats (`Pairs.txt`, `Add_AssociatedPlayers.txt`, `Extra_Allocated.csv`'s team column). One file, one schema, one parser:
```yaml
# 10UB/overrides.yaml
pairs:
  - [Player A, Player B]
  - [Player A, Player C]
coach_children:
  Coach One: [Player One]
  Coach Two: [Player Two]
extra_team_assignments:
  Player Three: 10UB-extra-01
notes:
  Player Four: "[accessibility need text] — see requests.txt"
```
You can hand-edit this in one spot, and validation can run as a single pass.

**A4. Project the wide Personnel/Unallocated files down to what's actually used.**
A pre-processing step (or just the loader) drops the 80+ columns the script never touches, producing a slim `players.tsv` and `volunteers.tsv` per division. The originals stay on disk for forensics; everything downstream reads the slim versions.

### B. Process (middle leverage)

**B1. Normalised name matching, with explicit ambiguity reporting.**
Replace the current substring match with: lowercase + strip accents + collapse internal whitespace + drop parenthetical annotations + optional nickname table (`pat`↔`patrick`, `liz`↔`elizabeth`). When a coach name maps to >1 player or 0 players, emit an actionable line:
```
[10UB] AMBIGUOUS: coach "Pat Smith" could be parent of:
  - Child One Smith (Pat Smith, dad)
  - Child Two Smith (Patrick J Smith, dad)
  Resolve by adding to 10UB/overrides.yaml under coach_children.
```
Keeps the human-in-the-loop step short and obvious.

**B2. Replace the silent `print` warnings with a structured `validation_report.md` per division.**
Same warnings, but written to disk grouped by severity:
- **BLOCKER** (script will produce wrong output): unassigned players at end, coach with no children resolved, missing Personnel entry.
- **WARNING** (script proceeded but you should check): pair-mate not found, EXTRA player not in Unallocated, payment-pending player.
- **INFO**: which overrides were used.

Exit code is non-zero if any BLOCKER appears.

**B3. Unify 5U/6U and the rest behind one team-assembly function with `balance_by=` parameter.**
Right now the script has `if "5U" in DIVISION` branches scattered. A single `assemble_teams(players, teams, balance_by=("rating","age","gender") | ("dob","gender"))` removes the duplication.

**B4. Drop the coefficient-of-variation fallback.**
Replace with an explicit, documented rule. Suggestion: experience enum is the only fallback; if that's missing too, the player goes on a `needs_rating.md` list and you (or the division commissioner) fill in a value before the run continues. No silent defaults.

### C. Outputs (low effort, high readability)

**C1. Per-division `<DIV>_summary.md`** replacing the byproduct trio (`_Ratings.tsv`, `_Team_Ratings.tsv`, `_Extra_Teams.txt`):
```markdown
# 10UB summary
- 12 teams, 142 players, avg rating 3.10 (σ=0.04)
- 6 EXTRA players placed across teams 01, 02, 04, 05, 07, 10
- 4 overrides used (see overrides.yaml)
- 0 unassigned, 0 blockers, 2 warnings (see validation_report.md)

## Team 01 — coach1/coach2/coach3  (avg 3.18)
  ...
```
Plus the unchanged `<DIV>_Teams.csv` for SportConnect upload.

**C2. Top-level `season_summary.md`** auto-generated, listing every division: `ready / has warnings / blocked`. At-a-glance "what's safe to upload right now".

### D. Workflow (low effort, removes per-division grind)

**D1. Single entrypoint:**
```
python rosters.py 25-26-Season              # runs every division
python rosters.py 25-26-Season --only 10UB  # iterate on one
```
Exits non-zero if any division has BLOCKERs. Solves the "ten invocations, ten times check the warnings" problem.

**D2. Acknowledge the manual SportConnect upload as the ceiling.**
No API → the final step stays manual. Worth a one-line note in the README rather than the recurring temptation to automate it; the simplification effort pays off in everything *upstream* of the upload.

---

## 7. Open questions

Things I couldn't determine from the archive alone — answers shape which simplifications are worth doing:

1. **Which inputs do you actually hand-edit each season vs. which are pure exports?**
   I'm assuming `<DIV>_Coaches.tsv`, `<DIV>_Pairs.txt`, `<DIV>_Add_AssociatedPlayers.txt`, and `<DIV>_Extra_Allocated.csv`'s team column are hand-maintained, and Personnel/Unallocated/Player_Ratings are exports. If `Coaches.tsv` is built from a shared Google Sheet, that changes whether A3 (the `overrides.yaml` consolidation) can pull from the sheet directly.

2. **Does SportConnect take a combined multi-division upload, or strictly one CSV per division?**
   If combined: worth producing one `season_teams.csv` as a primary output. If per-division: current `<DIV>_Teams.csv` shape stays.

3. **Any team-size/EXTRA-distribution constraints from AYSO that aren't in the code?**
   The 24-25 hardcoded "first six 10UB teams ≤ 6 players" looked rule-derived. Knowing what's a rule vs. what's just a heuristic-tuning would let us encode constraints explicitly.

4. **How frequently do AYSO form-field IDs actually change?**
   Every season based on the 24-25 → 25-26 diff. Confirms A2 is worth doing now rather than later.

5. **Are the `requests.txt` accessibility/coach-preference notes acted on automatically, or is that just human reference?**
   Currently the script doesn't read it — but it's the kind of thing where a structured field in `overrides.yaml` (`notes:`) could surface them at relevant decision points.

---

## TL;DR

The pipeline works but accumulates entropy: format duplication, season-volatile field IDs in code, three ad-hoc override file formats, silent warnings, and one giant per-division Python script. The shortest path to a calmer next season:

1. **`field_map.yaml`** per season (kills the season-to-season code edit).
2. **`overrides.yaml`** per division (unifies pairs/coach-children/extras).
3. **`validation_report.md`** per division + non-zero exit on BLOCKERs (no more silent failures).
4. **One entrypoint** that does all divisions and tells you which are ready to upload.

Everything else in §6 is gravy on top of that.
