"""Team assembly algorithm: assign every player to a team within size caps.

Algorithm shape matches the 25-26 script (same balance heuristic — not the
moment to redesign team balance), implemented against the new typed
objects and override schema:

    1. Initialise teams from valid coach assignments (skip TBD).
    2. Place each coach's kids on their team via the fallback chain:
         a. overrides.coach_children[coach_name]
         b. parent-name index from player records
         c. volunteer.associated_players from Personnel.txt
       Logs WARNING if none of the above resolves.
    3. For each group from overrides.groups, ensure all members land on
       the same team. Groups whose anchor is already a coach kid stick
       to that coach's team; otherwise the group is held until the
       balance passes and placed atomically.
    4. Place EXTRA-league players (10U/12U) on the most under-stocked
       team that fits.
    5. Above-average pass: highest-rated remaining players placed on
       lowest-rated team, capped at half the division max.
    6. Below-average pass: lowest-rated remaining players placed on
       highest-rated team, capped at full division max.
    7. Cleanup: any stragglers go on the smallest team or are
       BLOCKER-logged if no team fits.
    8. Surface every override note as INFO so it appears in the report.

5U/6U is currently NotImplementedError — those divisions use DOB-based
balancing in the old script; the unified `balance_by=` interface is
deferred to the next roadmap item.
"""

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

from loaders import Player, Volunteer, CoachAssignment
from names import names_match


# Max players per team, keyed by division-name prefix.
DIVISION_MAX_PLAYERS = {
    "14UB": 16,
    "14UG": 10,
    "12U": 12,
    "10U": 10,
    "8U": 9,
    "6U": 10,
    "5U": 10,
}


def division_max(division: str) -> int:
    """Look up the team-size cap for a division like '8UB' or '14UG'."""
    for prefix, cap in DIVISION_MAX_PLAYERS.items():
        if division.startswith(prefix):
            return cap
    raise ValueError(f"Unknown division: {division}")


@dataclass
class TeamRoster:
    label: str
    coaches: List[CoachAssignment] = field(default_factory=list)
    players: List[Player] = field(default_factory=list)
    extras_present: bool = False

    @property
    def rating_avg(self) -> float:
        rated = [p.rating for p in self.players if p.rating is not None]
        return sum(rated) / len(rated) if rated else 0.0

    @property
    def age_avg(self) -> float:
        aged = [p.age for p in self.players if p.age is not None]
        return sum(aged) / len(aged) if aged else 0.0

    def size(self) -> int:
        return len(self.players)


@dataclass
class LogEntry:
    severity: str   # "BLOCKER" | "WARNING" | "INFO"
    code: str       # short tag like "no_coach_kids"
    message: str


def _initialize_teams(coach_assignments: Iterable[CoachAssignment]) -> List[TeamRoster]:
    teams_by_label: Dict[str, TeamRoster] = {}
    for ca in coach_assignments:
        label = ca.team_label.strip()
        if not label or label.upper() == "TBD":
            continue
        if label not in teams_by_label:
            teams_by_label[label] = TeamRoster(label=label)
        teams_by_label[label].coaches.append(ca)
    return list(teams_by_label.values())


def _build_parent_index(players: Iterable[Player]) -> Dict[tuple, List[Player]]:
    """Map (parent_first_lower, parent_last_lower) -> list[Player]. Includes
    both primary and secondary contacts."""
    idx: Dict[tuple, List[Player]] = {}
    for p in players:
        for first, last in (
            (p.parent_first, p.parent_last),
            (p.secondary_first, p.secondary_last),
        ):
            key = (first.strip().lower(), last.strip().lower())
            if key[0] and key[1]:
                idx.setdefault(key, []).append(p)
    return idx


def _find_players_by_name(names, players, log, source) -> List[Player]:
    """Resolve a list of player-name strings to Player objects."""
    found = []
    for name in names:
        matches = [p for p in players if names_match(p.full_name, name)]
        if len(matches) == 0:
            log.append(LogEntry(
                "WARNING", "name_not_found",
                f"Player '{name}' from {source} not found in division roster."
            ))
        elif len(matches) > 1:
            log.append(LogEntry(
                "BLOCKER", "name_ambiguous",
                f"Name '{name}' from {source} matches {len(matches)} players: "
                f"{[m.full_name for m in matches]}"
            ))
        else:
            found.append(matches[0])
    return found


def _resolve_coach_children(
    ca: CoachAssignment,
    players: List[Player],
    parent_index: Dict[tuple, List[Player]],
    volunteers: List[Volunteer],
    overrides_coach_children: Dict[str, List[str]],
    log: List[LogEntry],
) -> List[Player]:
    coach_full = f"{ca.first_name} {ca.last_name}"

    # 1. Explicit override wins
    for key, kid_names in overrides_coach_children.items():
        if names_match(coach_full, key):
            return _find_players_by_name(
                kid_names, players, log,
                source=f"overrides.coach_children[{key!r}]",
            )

    # 2. Parent-name index
    key = (ca.first_name.strip().lower(), ca.last_name.strip().lower())
    if key in parent_index:
        return list(parent_index[key])

    # 3. Volunteer.associated_players via name match
    for v in volunteers:
        if names_match(coach_full, v.full_name) and v.associated_players:
            return _find_players_by_name(
                v.associated_players, players, log,
                source=f"Personnel.associatedPlayers[{v.full_name!r}]",
            )

    log.append(LogEntry(
        "WARNING", "no_coach_kids",
        f"Could not resolve children for coach '{coach_full}'. "
        f"Add an entry under overrides.coach_children if applicable."
    ))
    return []


def _resolve_groups(
    overrides_groups: List[List[str]],
    players: List[Player],
    log: List[LogEntry],
) -> List[List[Player]]:
    resolved = []
    for i, names in enumerate(overrides_groups):
        members = _find_players_by_name(
            names, players, log, source=f"overrides.groups[{i}]"
        )
        if len(members) >= 2:
            resolved.append(members)
        elif len(members) == 1:
            log.append(LogEntry(
                "WARNING", "group_size_one",
                f"overrides.groups[{i}] resolved to a single player "
                f"({members[0].full_name}) — no grouping effect."
            ))
    return resolved


def _group_lookup(groups: List[List[Player]]) -> Dict[str, List[Player]]:
    """Map player_id -> list of other Players in the same group."""
    lookup: Dict[str, List[Player]] = {}
    for group in groups:
        ids_in_group = {p.player_id for p in group}
        for member in group:
            others = [p for p in group if p.player_id != member.player_id]
            lookup[member.player_id] = others
    return lookup


def _place(team: TeamRoster, player: Player, placed: Set[str]) -> None:
    if player.player_id not in placed:
        team.players.append(player)
        placed.add(player.player_id)


def _place_with_group(
    team: TeamRoster,
    player: Player,
    placed: Set[str],
    group_lookup: Dict[str, List[Player]],
    cap: int,
    log: List[LogEntry],
) -> bool:
    """Place player + any group-mates on this team if they all fit. Returns
    True if the placement happened, False if the group would exceed cap."""
    group = [player] + [m for m in group_lookup.get(player.player_id, []) if m.player_id not in placed]
    if len(team.players) + len(group) > cap:
        return False
    for member in group:
        _place(team, member, placed)
    return True


def _pick_lowest_rated(teams, cap, player_count_factor=False):
    """Team with lowest avg rating that's under cap. For above-average placement."""
    available = [t for t in teams if t.size() < cap]
    if not available:
        return None
    if player_count_factor:
        return min(available, key=lambda t: (t.size(), t.rating_avg, t.age_avg))
    return min(available, key=lambda t: (t.rating_avg, t.age_avg, t.size()))


def _pick_highest_rated(teams, cap):
    """Team with highest avg rating that's under cap. For below-average placement.

    Mirrors the 25-26 script's `sorted(..., reverse=True)` sort key:
    (rating, age, size) all descending. The size-descending tiebreaker looks
    counter-intuitive for balance but matches the historical behaviour —
    concentrates low-rated players on the already-larger team rather than
    smoothing sizes.
    """
    available = [t for t in teams if t.size() < cap]
    if not available:
        return None
    return max(available, key=lambda t: (t.rating_avg, t.age_avg, t.size()))


def _pick_least_same_gender(teams, player_gender, cap):
    """Team with fewest same-gender players (then fewest total) under cap.

    Used by the 5U/6U DOB-balanced path where gender balance is the primary
    placement objective.
    """
    available = [t for t in teams if t.size() < cap]
    if not available:
        return None
    return min(
        available,
        key=lambda t: (
            sum(1 for p in t.players if p.gender == player_gender),
            t.size(),
        ),
    )


def _dob_sort_key(dob: str):
    """Convert MM/DD/YYYY into a sortable tuple. Empty/malformed sort last."""
    parts = dob.split("/") if dob else []
    if len(parts) != 3:
        return ("", "", "")
    mm, dd, yyyy = parts
    return (yyyy.zfill(4), mm.zfill(2), dd.zfill(2))


def _avg_rating(players: Iterable[Player]) -> float:
    rated = [p.rating for p in players if p.rating is not None]
    return sum(rated) / len(rated) if rated else 0.0


def assemble_teams(
    players: List[Player],
    coach_assignments: List[CoachAssignment],
    volunteers: List[Volunteer],
    overrides: Dict,
    division: str,
    extra_player_ids: Optional[Set[str]] = None,
    balance_by: Optional[str] = None,
):
    """Return (teams, log).

    `balance_by` controls the placement-pass strategy after coach kids,
    groups, and extras are placed:
        "rating" — above-average → below-average passes (8U+ default)
        "dob"    — DOB-sorted single pass with gender balance (5U/6U default)
    If None, inferred from `division`.
    """
    extra_player_ids = extra_player_ids or set()
    log: List[LogEntry] = []

    if balance_by is None:
        balance_by = "dob" if division.startswith(("5U", "6U")) else "rating"
    if balance_by not in ("rating", "dob"):
        raise ValueError(f"balance_by must be 'rating' or 'dob', got {balance_by!r}")

    max_per = division_max(division)
    teams = _initialize_teams(coach_assignments)

    if not teams:
        log.append(LogEntry(
            "BLOCKER", "no_teams",
            "No teams to assemble — every coach assignment was TBD or empty."
        ))
        return teams, log

    parent_index = _build_parent_index(players)
    placed: Set[str] = set()

    # Step 1: coach kids
    for team in teams:
        for ca in team.coaches:
            kids = _resolve_coach_children(
                ca, players, parent_index, volunteers,
                overrides.get("coach_children", {}), log,
            )
            for kid in kids:
                _place(team, kid, placed)

    # Step 2: groups
    groups = _resolve_groups(overrides.get("groups", []), players, log)
    glookup = _group_lookup(groups)
    for group in groups:
        anchor_team = None
        for member in group:
            for team in teams:
                if member in team.players:
                    anchor_team = team
                    break
            if anchor_team:
                break
        if anchor_team:
            for member in group:
                if member.player_id not in placed:
                    if anchor_team.size() < max_per:
                        _place(anchor_team, member, placed)
                    else:
                        log.append(LogEntry(
                            "WARNING", "group_overflow",
                            f"Group member {member.full_name} cannot fit on "
                            f"team {anchor_team.label} (at cap of {max_per})."
                        ))

    # Step 3: EXTRA players (10U/12U)
    if extra_player_ids:
        extras = [p for p in players if p.player_id in extra_player_ids and p.player_id not in placed]
        for player in extras:
            target = _pick_lowest_rated(teams, max_per, player_count_factor=True)
            if not target or not _place_with_group(target, player, placed, glookup, max_per, log):
                log.append(LogEntry(
                    "BLOCKER", "extra_overflow",
                    f"No room for EXTRA player {player.full_name}."
                ))
                if target:
                    _place(target, player, placed)

    # Step 4 + 5: placement passes (rating-based) OR single DOB pass
    if balance_by == "rating":
        avg = _avg_rating(players)
        rated_remaining = [
            p for p in players if p.player_id not in placed and p.rating is not None
        ]

        above = sorted(
            [p for p in rated_remaining if p.rating >= avg],
            key=lambda p: -p.rating,
        )
        half_cap = max_per // 2
        for player in above:
            if player.player_id in placed:
                continue
            target = _pick_lowest_rated(teams, half_cap)
            if target and _place_with_group(target, player, placed, glookup, half_cap, log):
                continue
            target = _pick_lowest_rated(teams, max_per)
            if target:
                _place_with_group(target, player, placed, glookup, max_per, log)

        below = sorted(
            [p for p in players if p.player_id not in placed and p.rating is not None],
            key=lambda p: p.rating,
        )
        for player in below:
            if player.player_id in placed:
                continue
            target = _pick_highest_rated(teams, max_per)
            if target:
                _place_with_group(target, player, placed, glookup, max_per, log)
    else:  # balance_by == "dob"
        remaining = sorted(
            [p for p in players if p.player_id not in placed],
            key=lambda p: _dob_sort_key(p.dob),
            reverse=True,  # oldest first
        )
        for player in remaining:
            if player.player_id in placed:
                continue
            target = _pick_least_same_gender(teams, player.gender, max_per)
            if target:
                _place_with_group(target, player, placed, glookup, max_per, log)

    # Step 6: cleanup (unrated + true stragglers)
    unassigned = [p for p in players if p.player_id not in placed]
    for player in unassigned:
        target = min(teams, key=lambda t: t.size())
        if target.size() < max_per:
            _place(target, player, placed)
            log.append(LogEntry(
                "WARNING", "cleanup_placement",
                f"{player.full_name} placed on smallest team {target.label} "
                f"during cleanup (unrated or could not balance)."
            ))
        else:
            log.append(LogEntry(
                "BLOCKER", "unassigned",
                f"Could not place {player.full_name} — every team at cap of {max_per}."
            ))

    # Mark which teams carry EXTRA players
    for team in teams:
        if any(p.player_id in extra_player_ids for p in team.players):
            team.extras_present = True

    # Step 7: surface overrides notes as INFO
    for player_name, note in overrides.get("notes", {}).items():
        log.append(LogEntry(
            "INFO", "player_note",
            f"{player_name}: {note}"
        ))

    return teams, log
