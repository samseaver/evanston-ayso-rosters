"""Write a structured validation report for one division.

Turns the list[LogEntry] returned by assembly.assemble_teams into a markdown
file at <DIV>/<DIV>_validation_report.md. Replaces the scattered print()
warnings of the 24-25/25-26 scripts with a single artifact the operator
reads before the SportConnect upload.

Three sections, in order:
  - BLOCKERs    (script will produce wrong output; resolve before upload)
  - Warnings    (script proceeded; review before upload)
  - Notes       (INFO; surfaced from overrides.notes)

Status line at top: READY (no blockers) or BLOCKED (one or more blockers).
"""

from typing import Iterable, List

from assembly import LogEntry, TeamRoster


def render_report(division: str, teams: List[TeamRoster], log: Iterable[LogEntry]) -> str:
    """Return the markdown body for the validation report (no file I/O)."""
    log = list(log)
    blockers = [e for e in log if e.severity == "BLOCKER"]
    warnings = [e for e in log if e.severity == "WARNING"]
    infos = [e for e in log if e.severity == "INFO"]

    status = "BLOCKED" if blockers else "READY"
    total_placed = sum(t.size() for t in teams)

    lines = [
        f"# {division} validation report",
        "",
        f"**Status:** {status}",
        "",
        f"- {len(teams)} team(s), {total_placed} player(s) placed",
        f"- {len(blockers)} blocker(s), {len(warnings)} warning(s), {len(infos)} note(s)",
        "",
    ]

    if blockers:
        lines += [
            "## BLOCKERs",
            "",
            "These prevent a clean upload. Resolve before re-running.",
            "",
        ]
        for e in blockers:
            lines.append(f"- **{e.code}** — {e.message}")
        lines.append("")

    if warnings:
        lines += [
            "## Warnings",
            "",
            "The pipeline proceeded — review before upload.",
            "",
        ]
        for e in warnings:
            lines.append(f"- _{e.code}_ — {e.message}")
        lines.append("")

    if infos:
        lines += [
            "## Notes",
            "",
            "Surfaced from `overrides.yaml notes:`. Not acted on automatically; "
            "make sure the coach is aware.",
            "",
        ]
        for e in infos:
            lines.append(f"- {e.message}")
        lines.append("")

    if not blockers and not warnings and not infos:
        lines += ["## Clean", "", "No blockers, warnings, or notes.", ""]

    return "\n".join(lines)


def write_report(output_path, division: str, teams, log) -> None:
    """Write the validation report to disk."""
    body = render_report(division, teams, log)
    with open(output_path, "w") as f:
        f.write(body)
