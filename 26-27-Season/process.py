#!/usr/bin/env python3
"""End-to-end roster processing for a single division.

Usage:
    python process.py SEASON_DIR DIVISION
    python process.py SEASON_DIR DIVISION --extras player_id1,player_id2,...

Wires together: validate (configs) -> loaders (data) -> ratings -> assembly
-> output. Prints the structured log to stdout for now; the markdown
validation report writer (report.py) lands next.

Exit codes:
    0 - assembly succeeded, no BLOCKERs
    1 - one or more BLOCKERs in the log; <DIV>_Teams.csv may still be
        written but the operator should resolve the BLOCKERs before
        uploading to SportConnect
    2 - environment / config problem (PyYAML missing, file not found)
"""

import argparse
import sys
from pathlib import Path

import ratings
from assembly import assemble_teams, LogEntry
from loaders import (
    ValidationError,
    load_coach_assignments,
    load_field_map,
    load_overrides,
    load_players,
    load_ratings,
    load_volunteers,
)
from output import write_teams_csv


def run(season_dir: Path, division: str, extra_player_ids=None) -> int:
    extra_player_ids = extra_player_ids or set()
    div_dir = season_dir / division

    try:
        field_map, fm_warnings = load_field_map(season_dir / "field_map.yaml")
    except ValidationError as e:
        print(f"[BLOCKER] {e}", file=sys.stderr)
        return 2

    overrides, ov_warnings = load_overrides(div_dir / "overrides.yaml")

    try:
        players = load_players(div_dir / f"{division}_Unallocated.txt", field_map)
        volunteers = load_volunteers(div_dir / f"{division}_Personnel.txt")
        coach_assignments = load_coach_assignments(div_dir / f"{division}_Coaches.tsv")
    except ValidationError as e:
        print(f"[BLOCKER] {e}", file=sys.stderr)
        return 2

    current_ratings = load_ratings(season_dir / field_map["ratings"]["current_season_file"])
    previous_ratings_path = season_dir / field_map["ratings"]["previous_season_file"]
    previous_ratings = (
        load_ratings(previous_ratings_path) if previous_ratings_path.exists() else {}
    )

    needs_rating = ratings.resolve_all(
        players, current_ratings, previous_ratings, extra_player_ids=extra_player_ids
    )

    teams, log = assemble_teams(
        players=players,
        coach_assignments=coach_assignments,
        volunteers=volunteers,
        overrides=overrides,
        division=division,
        extra_player_ids=extra_player_ids,
    )

    for name in needs_rating:
        log.insert(0, LogEntry(
            "BLOCKER", "needs_rating",
            f"{name}: no rating could be resolved (no current TSV, no previous TSV, "
            f"no usable experience-level enum). Add a rating row before re-running."
        ))
    for w in fm_warnings + ov_warnings:
        log.insert(0, LogEntry("WARNING", "config", w))

    output_path = div_dir / f"{division}_Teams.csv"
    write_teams_csv(output_path, division, teams, volunteers)

    blockers = [e for e in log if e.severity == "BLOCKER"]
    warnings = [e for e in log if e.severity == "WARNING"]
    infos = [e for e in log if e.severity == "INFO"]

    for entry in log:
        stream = sys.stderr if entry.severity == "BLOCKER" else sys.stdout
        print(f"[{entry.severity}] {entry.code}: {entry.message}", file=stream)

    print()
    print(f"Wrote {output_path}")
    print(
        f"Summary: {len(teams)} team(s), "
        f"{sum(t.size() for t in teams)} player(s) placed, "
        f"{len(blockers)} blocker(s), {len(warnings)} warning(s), {len(infos)} info(s)"
    )

    return 1 if blockers else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("season_dir", type=Path)
    parser.add_argument("division", type=str)
    parser.add_argument(
        "--extras",
        type=str,
        default="",
        help="Comma-separated PlayerIDs that are EXTRA-league (10U/12U).",
    )
    args = parser.parse_args()

    extra_ids = {x.strip() for x in args.extras.split(",") if x.strip()}
    sys.exit(run(args.season_dir, args.division, extra_player_ids=extra_ids))


if __name__ == "__main__":
    main()
