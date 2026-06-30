#!/usr/bin/env python3
"""Validate field_map.yaml and per-division overrides.yaml for the AYSO
rosters pipeline. Run before the main processing script.

Usage:
    python validate.py                # validates current dir
    python validate.py 26-27-Season   # validates the named season dir

Exit codes:
    0 = all configs valid (warnings allowed)
    1 = one or more blockers found
    2 = environment problem (e.g. PyYAML not installed)

Also importable: future processing scripts call load_field_map() and
load_overrides() instead of yaml.safe_load directly, so validation happens
at the loader boundary.
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[BLOCKER] PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


FIELD_MAP_SCHEMA = {
    "ratings": {
        "current_season_file": str,
        "previous_season_file": str,
    },
    "fields": {
        "years_experience": str,
        "experience_level": str,
    },
}

OVERRIDES_KEYS = {"groups", "coach_children", "extra_team_assignments", "notes"}


class ValidationError(Exception):
    """A blocker. The pipeline must not proceed."""


def _load_yaml(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValidationError(f"{path}: malformed YAML: {e}")
    except FileNotFoundError:
        raise ValidationError(f"{path}: file not found")


def load_field_map(path):
    """Load and validate a field_map.yaml. Returns (data, warnings).

    Raises ValidationError on any structural problem.
    """
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: top-level must be a mapping")

    for section, expected_keys in FIELD_MAP_SCHEMA.items():
        if section not in data:
            raise ValidationError(f"{path}: missing required section '{section}'")
        if not isinstance(data[section], dict):
            raise ValidationError(f"{path}: '{section}' must be a mapping")
        for key, expected_type in expected_keys.items():
            if key not in data[section]:
                raise ValidationError(f"{path}: missing required key '{section}.{key}'")
            value = data[section][key]
            if not isinstance(value, expected_type):
                raise ValidationError(
                    f"{path}: '{section}.{key}' must be a {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )

    warnings = []
    for key, value in data["fields"].items():
        if "(TBD)" in value:
            warnings.append(
                f"{path}: 'fields.{key}' still contains '(TBD)' "
                f"— update with the real AYSO form ID before running the pipeline"
            )

    return data, warnings


def load_overrides(path):
    """Load and validate one division's overrides.yaml. Returns (data, warnings).

    Missing file is fine — returns ({}, []). Overrides are optional per division.
    Raises ValidationError on any structural problem.
    """
    if not os.path.exists(path):
        return {}, []

    data = _load_yaml(path)
    if data is None:
        return {}, []
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: top-level must be a mapping")

    warnings = []
    for key in data:
        if key not in OVERRIDES_KEYS:
            warnings.append(
                f"{path}: unknown top-level key '{key}' "
                f"(expected one of: {', '.join(sorted(OVERRIDES_KEYS))}) — typo?"
            )

    if "groups" in data:
        if not isinstance(data["groups"], list):
            raise ValidationError(f"{path}: 'groups' must be a list of lists")
        for i, group in enumerate(data["groups"]):
            if not isinstance(group, list):
                raise ValidationError(f"{path}: groups[{i}] must be a list of player names")
            if len(group) < 2:
                raise ValidationError(
                    f"{path}: groups[{i}] must contain at least 2 player names, got {len(group)}"
                )
            for j, name in enumerate(group):
                if not isinstance(name, str):
                    raise ValidationError(f"{path}: groups[{i}][{j}] must be a string")

    if "coach_children" in data:
        if not isinstance(data["coach_children"], dict):
            raise ValidationError(
                f"{path}: 'coach_children' must be a mapping (coach name → list of child names)"
            )
        for coach, kids in data["coach_children"].items():
            if not isinstance(kids, list) or not all(isinstance(k, str) for k in kids):
                raise ValidationError(
                    f"{path}: coach_children['{coach}'] must be a list of string player names"
                )
            if not kids:
                raise ValidationError(
                    f"{path}: coach_children['{coach}'] must list at least one child"
                )

    if "extra_team_assignments" in data:
        if not isinstance(data["extra_team_assignments"], dict):
            raise ValidationError(
                f"{path}: 'extra_team_assignments' must be a mapping (player name → team name)"
            )
        for player, team in data["extra_team_assignments"].items():
            if not isinstance(team, str):
                raise ValidationError(
                    f"{path}: extra_team_assignments['{player}'] must be a string team name"
                )

    if "notes" in data:
        if not isinstance(data["notes"], dict):
            raise ValidationError(
                f"{path}: 'notes' must be a mapping (player name → note text)"
            )
        for player, note in data["notes"].items():
            if not isinstance(note, str):
                raise ValidationError(f"{path}: notes['{player}'] must be a string")

    return data, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate AYSO rosters configs.")
    parser.add_argument(
        "season_dir",
        nargs="?",
        default=".",
        help="Season directory containing field_map.yaml and <DIV>/overrides.yaml (default: cwd)",
    )
    args = parser.parse_args()

    season_dir = Path(args.season_dir).resolve()
    if not season_dir.is_dir():
        print(f"[BLOCKER] not a directory: {season_dir}", file=sys.stderr)
        sys.exit(2)

    all_warnings = []
    blockers = []

    field_map_path = season_dir / "field_map.yaml"
    try:
        _, w = load_field_map(field_map_path)
        all_warnings.extend(w)
        print(f"[OK] {field_map_path.relative_to(season_dir.parent)}")
    except ValidationError as e:
        blockers.append(str(e))
        print(f"[BLOCKER] {e}", file=sys.stderr)

    division_dirs = sorted(
        p for p in season_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    for div_dir in division_dirs:
        ov_path = div_dir / "overrides.yaml"
        if not ov_path.exists():
            continue
        try:
            data, w = load_overrides(ov_path)
            all_warnings.extend(w)
            sections = ", ".join(k for k in data.keys() if k in OVERRIDES_KEYS)
            print(f"[OK] {ov_path.relative_to(season_dir.parent)} ({sections})")
        except ValidationError as e:
            blockers.append(str(e))
            print(f"[BLOCKER] {e}", file=sys.stderr)

    if all_warnings:
        print("\nWarnings:")
        for w in all_warnings:
            print(f"  [WARNING] {w}")

    if blockers:
        print(
            f"\n{len(blockers)} blocker(s) found — pipeline cannot proceed.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nAll config valid.")
    sys.exit(0)


if __name__ == "__main__":
    main()
