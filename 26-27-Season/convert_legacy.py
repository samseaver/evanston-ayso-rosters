#!/usr/bin/env python3
"""Convert 24-25/25-26 override files into per-division overrides.yaml.

For each division subdirectory of the given season dir, reads the legacy
override files that used to live as separate tab-delimited text and merges
them into a single overrides.yaml matching the new schema:

    <DIV>_Pairs.txt                    → overrides.yaml `groups:`
    <DIV>_Add_AssociatedPlayers.txt    → overrides.yaml `coach_children:`

Use this once per historical season to enable running the new pipeline
against old data for validation. Not needed for new (26-27+) seasons —
those maintain overrides.yaml directly.

Usage:
    python convert_legacy.py SEASON_DIR

Exit codes:
    0 - conversion complete (may have skipped divisions with no legacy files)
    2 - season dir not found or PyYAML missing
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[error] PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def _read_lines(path: Path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return [line.rstrip("\r\n") for line in f]


def convert_pairs(pairs_path: Path):
    """Return list[list[str]] for the `groups:` section, or [] if the file
    does not exist. Each Pairs.txt line is one tab-separated group of
    full player names."""
    if not pairs_path.exists():
        return []
    groups = []
    for line in _read_lines(pairs_path):
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) >= 2:
            groups.append(parts)
    return groups


def convert_add_associated(path: Path):
    """Return dict[coach_full] -> list[player_full] for the
    `coach_children:` section. Legacy format: 4 tab-separated columns per
    line, coach_first / coach_last / player_first / player_last."""
    if not path.exists():
        return {}
    result: dict = {}
    for line in _read_lines(path):
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 4:
            continue
        coach_first, coach_last, kid_first, kid_last = parts[0], parts[1], parts[2], parts[3]
        if not (coach_first and coach_last and kid_first and kid_last):
            continue
        coach_full = f"{coach_first} {coach_last}"
        kid_full = f"{kid_first} {kid_last}"
        result.setdefault(coach_full, []).append(kid_full)
    return result


def convert_division(div_dir: Path) -> bool:
    """Look for legacy override files in a division dir; write overrides.yaml
    if any are found. Returns True iff a file was written."""
    div = div_dir.name
    groups = convert_pairs(div_dir / f"{div}_Pairs.txt")
    coach_children = convert_add_associated(div_dir / f"{div}_Add_AssociatedPlayers.txt")

    if not groups and not coach_children:
        return False

    data: dict = {}
    if groups:
        data["groups"] = groups
    if coach_children:
        data["coach_children"] = coach_children

    out = div_dir / "overrides.yaml"
    with open(out, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("season_dir", type=Path)
    args = parser.parse_args()

    if not args.season_dir.is_dir():
        print(f"[error] not a directory: {args.season_dir}", file=sys.stderr)
        sys.exit(2)

    written = 0
    skipped = 0
    for div_dir in sorted(args.season_dir.iterdir()):
        if not div_dir.is_dir():
            continue
        if convert_division(div_dir):
            print(f"wrote {div_dir / 'overrides.yaml'}")
            written += 1
        else:
            skipped += 1

    print(f"\n{written} division(s) with legacy overrides converted; {skipped} skipped.")


if __name__ == "__main__":
    main()
