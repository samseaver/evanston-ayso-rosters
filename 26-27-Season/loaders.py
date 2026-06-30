"""Load AYSO export data into structured Python objects.

Wraps validate.py for YAML config loading and adds CSV/TSV loaders for the
AYSO exports. All loaders raise ValidationError (re-exported from validate)
on missing required columns so failures happen at the loader boundary, not
mid-pipeline.

Re-exports:
    load_field_map, load_overrides, ValidationError  (from validate)

Adds:
    load_players(unallocated_path, field_map) -> list[Player]
    load_volunteers(personnel_path)           -> list[Volunteer]
    load_coach_assignments(coaches_path)      -> list[CoachAssignment]
    load_ratings(ratings_path)                -> dict[(first, last)] -> int
"""

import csv
from dataclasses import dataclass, field
from typing import List, Optional

from validate import (  # noqa: F401  -- re-exported
    load_field_map,
    load_overrides,
    ValidationError,
)


def _open_text(path):
    """Open a text file, preferring UTF-8 and falling back to latin-1.

    Historic AYSO exports (24-25, 25-26) arrived as Windows latin-1; modern
    exports may be UTF-8. Test fixtures in this repo are UTF-8. Trying UTF-8
    first means the fixtures work without ceremony, while real latin-1
    exports still decode correctly via the fallback.
    """
    try:
        with open(path, encoding="utf-8") as probe:
            probe.read()
        return open(path, encoding="utf-8", newline="")
    except UnicodeDecodeError:
        return open(path, encoding="latin-1", newline="")


@dataclass
class Player:
    player_id: str
    full_name: str
    age: Optional[int]
    dob: str
    gender: str
    parent_first: str
    parent_last: str
    secondary_first: str
    secondary_last: str
    payment_status: str
    years_experience: Optional[int]
    experience_level: str
    primary_email: str
    rating: Optional[int] = None  # filled by ratings.resolve_all() after load


@dataclass
class Volunteer:
    volunteer_id: str
    volunteer_type_id: str
    full_name: str
    role: str
    associated_players: List[str] = field(default_factory=list)


@dataclass
class CoachAssignment:
    team_label: str
    first_name: str
    last_name: str
    role: str


def _require_columns(path, fieldnames, required):
    missing = [c for c in required if c not in fieldnames]
    if missing:
        raise ValidationError(
            f"{path}: missing required columns: {', '.join(missing)}"
        )


def _parse_int(value):
    if not value or value == "No Answer":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def load_players(unallocated_path, field_map):
    """Read <DIV>_Unallocated.txt and return list[Player].

    `field_map` is the dict returned by validate.load_field_map. The form-id
    column headers (years_experience, experience_level) come from there, so
    they can change per season without touching this code.
    """
    yexp_key = field_map["fields"]["years_experience"]
    elevel_key = field_map["fields"]["experience_level"]

    required_columns = [
        "PlayerID",
        "Player Name",
        "Age",
        "Date Of Birth",
        "Gender",
        "Parent FirstName",
        "Parent LastName",
        "Secondary Contact FirstName",
        "Secondary Contact LastName",
        "Primary Contact Email",
        "Division Price Payment Status",
        yexp_key,
        elevel_key,
    ]

    players = []
    with _open_text(unallocated_path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        _require_columns(unallocated_path, reader.fieldnames or [], required_columns)
        for row in reader:
            players.append(
                Player(
                    player_id=row["PlayerID"],
                    full_name=row["Player Name"],
                    age=_parse_int(row["Age"]),
                    dob=row["Date Of Birth"],
                    gender=row["Gender"].lower(),
                    parent_first=row["Parent FirstName"],
                    parent_last=row["Parent LastName"],
                    secondary_first=row["Secondary Contact FirstName"],
                    secondary_last=row["Secondary Contact LastName"],
                    payment_status=row["Division Price Payment Status"],
                    years_experience=_parse_int(row[yexp_key]),
                    experience_level=row[elevel_key],
                    primary_email=row["Primary Contact Email"],
                )
            )
    return players


def load_volunteers(personnel_path):
    """Read <DIV>_Personnel.txt and return list[Volunteer].

    Parses the comma-separated `associatedPlayers` field into a clean list,
    dropping "No Answer" sentinels and empty entries.
    """
    required_columns = [
        "VolunteerID",
        "VolunteerTypeId",
        "Team Personnel Name",
        "Team Personnel Role",
        "associatedPlayers",
    ]

    volunteers = []
    with _open_text(personnel_path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        _require_columns(personnel_path, reader.fieldnames or [], required_columns)
        for row in reader:
            raw = row["associatedPlayers"] or ""
            associated = [
                name.strip()
                for name in raw.split(",")
                if name.strip() and name.strip() != "No Answer"
            ]
            volunteers.append(
                Volunteer(
                    volunteer_id=row["VolunteerID"],
                    volunteer_type_id=row["VolunteerTypeId"],
                    full_name=row["Team Personnel Name"],
                    role=row["Team Personnel Role"],
                    associated_players=associated,
                )
            )
    return volunteers


def load_coach_assignments(coaches_path):
    """Read <DIV>_Coaches.tsv and return list[CoachAssignment].

    TBD team labels are returned as-is; the caller decides whether to skip
    them. Empty fields stay empty (whitespace stripped).
    """
    required_columns = ["Team", "First Name", "Last Name", "Role"]

    coaches = []
    with _open_text(coaches_path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        _require_columns(coaches_path, reader.fieldnames or [], required_columns)
        for row in reader:
            coaches.append(
                CoachAssignment(
                    team_label=row["Team"].strip(),
                    first_name=row["First Name"].strip(),
                    last_name=row["Last Name"].strip(),
                    role=row["Role"].strip(),
                )
            )
    return coaches


def load_ratings(ratings_path):
    """Read a season-level player ratings TSV.

    Returns dict[(normalised_first, normalised_last)] -> int rating. Keys are
    name-normalised via names.normalise() so lookups handle accents,
    casing, and stray whitespace consistently with the rest of the pipeline.
    Skips rows with NA or empty ratings.
    """
    from names import normalise  # local import: keeps loaders importable in isolation

    ratings = {}
    with _open_text(ratings_path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            first = (row.get("Player First") or "").strip()
            last = (row.get("Player Last") or "").strip()
            raw = (row.get("Rating") or "").strip()
            if not first or not last or not raw:
                continue
            if raw in ("NA - Did not play", "NA"):
                continue
            try:
                rating = int(raw.split()[0])
            except (ValueError, IndexError):
                continue
            ratings[(normalise(first), normalise(last))] = rating
    return ratings
