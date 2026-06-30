"""Per-division and season-level summary writers.

Two markdown artifacts that replace the workflow byproducts of the
24-25/25-26 scripts:

    `<DIV>/<DIV>_summary.md`
        Human-readable team breakdown, balance metrics, override usage.
        Collapses the _Ratings.tsv / _Team_Ratings.tsv / _Extra_Teams.txt
        trio into a single artifact.

    `<SEASON>/season_summary.md`
        One-table view of every division (status, team/player counts,
        blocker/warning/note counts). At-a-glance "what's safe to upload
        right now".

Both renderers are pure functions returning strings; the write_* wrappers
do the file I/O. Timestamps for the season summary are injectable so tests
get deterministic output.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from assembly import LogEntry, TeamRoster
from output import team_display_name


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _format_avg(values: List[float], precision: int = 2) -> str:
    if not values:
        return "—"
    return f"{_avg(values):.{precision}f}"


def render_division_summary(
    division: str,
    teams: List[TeamRoster],
    log: Iterable[LogEntry],
    overrides: Optional[dict] = None,
) -> str:
    overrides = overrides or {}
    log_list = list(log)
    blockers = [e for e in log_list if e.severity == "BLOCKER"]

    status = "BLOCKED" if blockers else "READY"
    total_players = sum(t.size() for t in teams)
    all_ratings = [p.rating for t in teams for p in t.players if p.rating is not None]
    div_avg = _format_avg(all_ratings)

    lines: List[str] = [
        f"# {division} summary",
        "",
        f"**Status:** {status} · {len(teams)} teams · {total_players} players "
        f"· avg rating {div_avg}",
        "",
    ]

    for i, team in enumerate(teams, start=1):
        tname = team_display_name(division, i, team)
        ratings = [p.rating for p in team.players if p.rating is not None]
        ages = [p.age for p in team.players if p.age is not None]
        f_count = sum(1 for p in team.players if p.gender == "f")
        m_count = sum(1 for p in team.players if p.gender == "m")

        lines += [
            f"## Team {i} — {tname}",
            "",
            f"*{team.size()} players · avg rating {_format_avg(ratings)} "
            f"· {f_count}F {m_count}M · age {_format_avg(ages, 1)}*",
            "",
        ]
        if team.coaches:
            coach_strs = [f"{c.first_name} {c.last_name} ({c.role})" for c in team.coaches]
            lines += [f"**Coaches:** {', '.join(coach_strs)}", ""]

        lines += [
            "| Player | Rating | Age | Gender |",
            "|--------|--------|-----|--------|",
        ]
        for p in team.players:
            r = p.rating if p.rating is not None else "—"
            a = p.age if p.age is not None else "—"
            g = p.gender.upper() if p.gender else "—"
            lines.append(f"| {p.full_name} | {r} | {a} | {g} |")
        lines.append("")

    used = []
    for coach, kids in overrides.get("coach_children", {}).items():
        used.append(f"- `coach_children` · {coach} → {', '.join(kids)}")
    for i, group in enumerate(overrides.get("groups", [])):
        used.append(f"- `groups[{i}]` · {', '.join(group)}")
    for player, team_name in overrides.get("extra_team_assignments", {}).items():
        used.append(f"- `extra_team_assignments` · {player} → {team_name}")
    notes_count = len(overrides.get("notes", {}))
    if notes_count:
        used.append(f"- `notes` · {notes_count} surfaced (see validation_report.md)")
    if used:
        lines += ["## Overrides used", ""] + used + [""]

    lines += [
        "## Files",
        "",
        f"- Upload to SportConnect: `{division}_Teams.csv`",
        f"- Validation log: `{division}_validation_report.md`",
        "",
    ]
    return "\n".join(lines)


def write_division_summary(output_path, division, teams, log, overrides=None):
    with open(output_path, "w") as f:
        f.write(render_division_summary(division, teams, log, overrides))


@dataclass
class DivisionResult:
    """Aggregate per-division stats used to build the season summary."""
    division: str
    status: str            # "READY" | "BLOCKED" | "FAILED"
    teams_count: int
    players_count: int
    blockers_count: int
    warnings_count: int
    notes_count: int
    exit_code: int

    @classmethod
    def from_run(cls, division: str, teams, log, exit_code: int) -> "DivisionResult":
        blockers = [e for e in log if e.severity == "BLOCKER"]
        warnings = [e for e in log if e.severity == "WARNING"]
        infos = [e for e in log if e.severity == "INFO"]
        status = "BLOCKED" if blockers else "READY"
        return cls(
            division=division,
            status=status,
            teams_count=len(teams),
            players_count=sum(t.size() for t in teams),
            blockers_count=len(blockers),
            warnings_count=len(warnings),
            notes_count=len(infos),
            exit_code=exit_code,
        )

    @classmethod
    def failed(cls, division: str, message: str = "") -> "DivisionResult":
        return cls(
            division=division,
            status="FAILED",
            teams_count=0,
            players_count=0,
            blockers_count=0,
            warnings_count=0,
            notes_count=0,
            exit_code=2,
        )


def render_season_summary(
    season_label: str,
    results: List[DivisionResult],
    generated_at: Optional[datetime] = None,
) -> str:
    """Top-level markdown summary across every division.

    `generated_at` defaults to the current UTC time; tests pass a fixed
    datetime so output is reproducible.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    lines = [
        f"# {season_label} season summary",
        "",
        f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "| Division | Status | Teams | Players | Blockers | Warnings | Notes |",
        "|----------|--------|-------|---------|----------|----------|-------|",
    ]
    for r in results:
        lines.append(
            f"| {r.division} | {r.status} | {r.teams_count} | {r.players_count} "
            f"| {r.blockers_count} | {r.warnings_count} | {r.notes_count} |"
        )
    lines.append("")

    ready = [r for r in results if r.status == "READY"]
    not_ready = [r for r in results if r.status != "READY"]
    if not not_ready:
        lines.append(
            f"**Overall:** {len(results)} division(s), all READY for SportConnect upload."
        )
    else:
        names = ", ".join(r.division for r in not_ready)
        lines.append(
            f"**Overall:** {len(ready)}/{len(results)} READY. "
            f"{len(not_ready)} division(s) need attention: {names}."
        )
    lines.append("")

    lines += ["Per-division files:"]
    for r in results:
        lines.append(f"- `{r.division}/{r.division}_summary.md`")
    lines.append("")
    return "\n".join(lines)


def write_season_summary(output_path, season_label, results, generated_at=None):
    with open(output_path, "w") as f:
        f.write(render_season_summary(season_label, results, generated_at))
