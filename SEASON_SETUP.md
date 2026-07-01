# Setting up a season

For the volunteer (or voluntold) parent taking this on. The pipeline does the heavy lifting — you mostly gather files, put them in the right folders, and run one command.

## The 30-second version

1. Get exports from AYSO for each division.
2. Drop them in `26-27-Season/<DIVISION>/` with the expected filenames.
3. Update two form-ID lines in `field_map.yaml`.
4. Run `python 26-27-Season/rosters.py 26-27-Season`.
5. Open `season_summary.md` — it'll tell you which divisions are ready to upload.

Expect ~30–60 minutes gathering files, ~5 minutes running the pipeline, plus whatever time you spend on divisions the summary flags.

## What you need from AYSO / SportConnect

**Per division** (5U, 6U, 8UB, 8UG, 10UB, 10UG, 12UB, 12UG, 14UB, 14UG — up to 10 folders), all exported from the SportConnect admin UI:

| File in the division folder | What it is | Where it comes from |
|---|---|---|
| `<DIV>_Unallocated.txt` | The full registered roster for the division (tab-separated) | SportConnect division report → export |
| `<DIV>_Personnel.txt` | Volunteers (coaches, team parents) with their AYSO VolunteerIDs | SportConnect volunteer report → export |
| `<DIV>_Coaches.tsv` | The team-assignment spreadsheet you maintain (usually in Google Sheets) → save as TSV | Your own working sheet |
| `<DIV>_Extra_Allocated.csv` *(10U/12U only)* | The EXTRA-league tryout selections | Tryout coordinator |

**At the season level** (`26-27-Season/` root):

| File | What it is |
|---|---|
| `field_map.yaml` | Config — already there. You just update two lines each year. |
| `2026_Player_Ratings.tsv` | Coach ratings from last spring's evaluations |

That's it. Everything else the pipeline generates.

## The Coaches spreadsheet — a note on format

Unlike the AYSO exports, `<DIV>_Coaches.tsv` is a working sheet you and your fellow coordinators maintain by hand — usually a shared Google Sheet you export as TSV per division at the end.

The scripts are strict about **four column headers** and completely forgiving about the rest:

| Column header | Notes |
|---|---|
| `Team` | Value can be `TM 1`, `TM 2`, etc. Rows with value `TBD` are silently skipped. |
| `First Name` | Coach or team parent given name. |
| `Last Name` | Coach or team parent surname. |
| `Role` — or `Role / License` — or `Role/License` | Value is free text; `TP` and `Team Parent` are recognised specially and treated more leniently. |

Any other columns you add (`Notes`, `Coaching/Volunteer Partner`, `Solo/Paired`, `AYSO Exp.`, `Multiple divisions`, `Tentative Team`, whatever) are ignored — feel free to keep whatever helps your workflow.

**Worth knowing:**
- Coach names don't have to match AYSO records exactly — nicknames (`Bob` vs `Robert`) and accents (`Maria` vs `María`) are handled automatically.
- If a required header gets renamed by mistake in the sheet, the pipeline fails loudly at startup and names the column it can't find — no silent data loss.
- Multiple rows with the same `Team` value are grouped into that team's coaching staff.
- One tab per division in the Google Sheet, exported as TSV when you're ready to run.

## Step-by-step

### 1. Grab the exports

Save each into the right folder under `26-27-Season/`. Filenames matter — the loaders look them up exactly. Case matters.

### 2. Update the form-IDs (once per season)

Open `26-27-Season/field_map.yaml`. You'll see two lines like this:

```yaml
years_experience: "Years of Experience:(TBD)"
experience_level: "Player's Experience Level(TBD)"
```

The `(TBD)` needs to be replaced with the real form-IDs from AYSO's current-season registration. To find them: open any `<DIV>_Unallocated.txt` in a text editor and search for "Years of Experience". You'll see a column header like `Years of Experience:(18939060)`. Copy that whole string in.

**They change every season.** Yes, it's annoying. Yes, it's a 30-second edit. If you skip it, the pipeline fails loudly at startup and tells you which key is wrong.

### 3. Write overrides for the divisions that need them (optional)

Most divisions run clean with no overrides. If you need any of:
- Kids to keep together (siblings, best-friend requests)
- A coach whose kid isn't auto-matched (name mismatch, kid registered under other parent)
- Notes about a kid to surface for their coach (accessibility, prior-year requests)
- Pre-assigning an EXTRA player to a specific team

…copy `26-27-Season/overrides.example.yaml` into `26-27-Season/<DIV>/overrides.yaml` and fill in the sections you need. Every section is optional; delete what you don't use.

### 4. Run the pipeline

```
python 26-27-Season/rosters.py 26-27-Season
```

Takes seconds. Writes, for each division:
- `<DIV>_Teams.csv` — **this is what you upload to SportConnect**
- `<DIV>_summary.md` — human-readable team breakdown; forward to coaches
- `<DIV>_validation_report.md` — any warnings for that division

Plus at the season root:
- `season_summary.md` — one-table view of every division

### 5. Read `season_summary.md` first

Every division shows READY or BLOCKED.

- **All READY** → upload each `<DIV>_Teams.csv` to SportConnect. Done.
- **Any BLOCKED** → open that division's `<DIV>_validation_report.md`, fix what it says, re-run.

## What the warnings mean

You'll see some; most are informational.

| Warning | What to do |
|---|---|
| `cleanup_over_cap` | A team has one more player than the cap. Usually fine; SportConnect accepts. If not, manually shift a kid. |
| `no_coach_kids` (INFO) | Team parent has no kid in this division. Ignore. |
| `no_coach_kids` (WARNING) | Real coach's kid couldn't be auto-matched. Either they're in a different division (ignore), or add an `overrides.coach_children:` entry with the coach's name and their kid's name. |
| `extra_not_in_core` | An EXTRA-league player isn't in the base roster. Usually means they signed up for tryouts but not the base division. Confirm and skip. |
| `config` | Something in `field_map.yaml` or `overrides.yaml` is off. Message tells you what. |

**BLOCKERs are different** — they stop the pipeline from producing a valid roster. Most common:

| Blocker | What to do |
|---|---|
| `needs_rating` | A player couldn't be rated. Either add them to the ratings TSV or ask their family for their experience level. |
| `extra_ambiguous` | Two players share a first+last name. Add an `extra_team_assignments:` override to specify which. |
| `no_teams` | Every coach was `TBD`. Assign coaches to teams in `<DIV>_Coaches.tsv`. |

## When to ask for help

- **What a column in an AYSO export means** → read `REVIEW.md §2`.
- **What a valid file should look like** → `26-27-Season/tests/fixtures/` has small examples of every file type.
- **You have data from before 26-27 in the old format** (`Pairs.txt` / `Add_AssociatedPlayers.txt`) → `python 26-27-Season/convert_legacy.py <OLD_SEASON_DIR>` migrates it for you.
- **You changed something and want to check nothing broke** → `cd 26-27-Season && python3 -m unittest discover -s tests` (should say "OK 113 tests").

## What you don't have to worry about

- No code to write. `field_map.yaml` and `overrides.yaml` are the only files you author.
- The historical `24-25-Season/` and `25-26-Season/` scripts are kept as reference — don't touch them.
- Warnings don't stop the pipeline; only BLOCKERs do.
- The pipeline is idempotent — re-run it as many times as you like while iterating on overrides.
- SportConnect upload is manual (no API). The pipeline produces the file; you upload it.

For future seasons (27-28 onwards), copy `26-27-Season/` to `27-28-Season/`, delete the division data, and repeat. The scripts stay the same.
