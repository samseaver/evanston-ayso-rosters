#!/usr/bin/env python3
"""Multi-division batch runner.

Runs process.run() for every known AYSO division that exists as a
subdirectory of the season folder. Prints a one-line status per division
and exits non-zero if any division finished BLOCKED or FAILED.

Usage:
    python rosters.py SEASON_DIR                # every division found
    python rosters.py SEASON_DIR --only 10UB    # one division (can repeat)
    python rosters.py SEASON_DIR --skip 14UB    # exclude (can repeat)

Exit codes:
    0 - every division OK
    1 - at least one division BLOCKED or FAILED
    2 - no divisions found / season dir does not exist
"""

import argparse
import sys
from pathlib import Path

import process
from summary import DivisionResult, write_season_summary


# Known AYSO divisions in the order we like to report them.
KNOWN_DIVISIONS = [
    "5U", "6U",
    "8UB", "8UG",
    "10UB", "10UG",
    "12UB", "12UG",
    "14UB", "14UG",
]




def run(season_dir: Path, only=None, skip=None):
    only = set(only or [])
    skip = set(skip or [])

    if not season_dir.is_dir():
        print(f"[error] not a directory: {season_dir}", file=sys.stderr)
        return 2

    divisions = []
    for div in KNOWN_DIVISIONS:
        if (season_dir / div).is_dir():
            if only and div not in only:
                continue
            if div in skip:
                continue
            divisions.append(div)

    if not divisions:
        print(f"[error] no division directories found in {season_dir}", file=sys.stderr)
        return 2

    results = []
    for div in divisions:
        print(f"\n=== {div} ===")
        try:
            result = process.run(season_dir, div)
        except Exception as e:  # broad on purpose — never let one division kill the batch
            print(f"[FAILED] {div}: {type(e).__name__}: {e}", file=sys.stderr)
            result = DivisionResult.failed(div)
        results.append(result)

    season_summary_path = season_dir / "season_summary.md"
    write_season_summary(season_summary_path, season_dir.name, results)
    print(f"\nWrote {season_summary_path}")

    print("\n=== Summary ===")
    for r in results:
        print(f"  {r.division}: {r.status}")

    bad = [r for r in results if r.exit_code != 0]
    if bad:
        print(
            f"\n{len(bad)} division(s) need attention before SportConnect upload.",
            file=sys.stderr,
        )
        return 1
    print("\nAll divisions ready for upload.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Run every division in a season directory.")
    parser.add_argument("season_dir", type=Path)
    parser.add_argument("--only", action="append", default=[], metavar="DIV",
                        help="Limit to this division (can repeat).")
    parser.add_argument("--skip", action="append", default=[], metavar="DIV",
                        help="Exclude this division (can repeat).")
    args = parser.parse_args()
    sys.exit(run(args.season_dir, only=args.only, skip=args.skip))


if __name__ == "__main__":
    main()
