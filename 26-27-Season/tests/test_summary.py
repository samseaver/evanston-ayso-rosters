"""Unit tests for summary.py — the per-division and season summary renderers."""

import os
import sys
import unittest
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assembly import LogEntry, TeamRoster
from loaders import CoachAssignment
from summary import (
    DivisionResult,
    render_division_summary,
    render_season_summary,
)


@dataclass
class FakePlayer:
    player_id: str
    full_name: str
    age: Optional[int]
    gender: str
    rating: Optional[int] = None


def _build_team(label, coaches, players):
    t = TeamRoster(label=label)
    t.coaches = coaches
    t.players = list(players)
    return t


class TestDivisionSummary(unittest.TestCase):
    def _basic_team(self):
        return _build_team(
            "TM 1",
            [CoachAssignment("TM 1", "Robert", "Smith", "Coach")],
            [
                FakePlayer("1", "Anna Smith", age=7, gender="f", rating=4),
                FakePlayer("2", "Bob Jones", age=7, gender="m", rating=3),
            ],
        )

    def test_basic_structure(self):
        body = render_division_summary("8UB", [self._basic_team()], [])
        self.assertIn("# 8UB summary", body)
        self.assertIn("**Status:** READY", body)
        self.assertIn("## Team 1 — 8UB - 01 - smith", body)
        self.assertIn("| Player | Rating | Age | Gender |", body)
        self.assertIn("| Anna Smith | 4 | 7 | F |", body)
        self.assertIn("Robert Smith (Coach)", body)

    def test_blocker_sets_blocked_status(self):
        body = render_division_summary(
            "8UB", [self._basic_team()],
            [LogEntry("BLOCKER", "x", "y")],
        )
        self.assertIn("**Status:** BLOCKED", body)

    def test_overrides_used_section_renders(self):
        body = render_division_summary(
            "8UB", [self._basic_team()], [],
            overrides={
                "groups": [["A", "B"]],
                "coach_children": {"Coach One": ["Player X"]},
                "extra_team_assignments": {"Player Y": "TM 3"},
                "notes": {"Player Z": "Something"},
            },
        )
        self.assertIn("## Overrides used", body)
        self.assertIn("`coach_children` · Coach One → Player X", body)
        self.assertIn("`groups[0]` · A, B", body)
        self.assertIn("`extra_team_assignments` · Player Y → TM 3", body)
        self.assertIn("`notes` · 1 surfaced", body)

    def test_no_overrides_means_no_section(self):
        body = render_division_summary("8UB", [self._basic_team()], [])
        self.assertNotIn("## Overrides used", body)

    def test_files_section_lists_outputs(self):
        body = render_division_summary("8UB", [self._basic_team()], [])
        self.assertIn("`8UB_Teams.csv`", body)
        self.assertIn("`8UB_validation_report.md`", body)

    def test_handles_no_rating(self):
        team = _build_team("TM 1", [], [FakePlayer("1", "Anna", age=7, gender="f", rating=None)])
        body = render_division_summary("8UB", [team], [])
        # No crash, em-dash for missing values
        self.assertIn("| Anna | — | 7 | F |", body)


class TestSeasonSummary(unittest.TestCase):
    def _fixed_dt(self):
        return datetime(2026, 6, 30, 14, 33, tzinfo=timezone.utc)

    def test_all_ready(self):
        results = [
            DivisionResult("5U", "READY", 2, 6, 0, 0, 0, 0),
            DivisionResult("8UB", "READY", 2, 10, 0, 0, 1, 0),
        ]
        body = render_season_summary("26-27", results, generated_at=self._fixed_dt())
        self.assertIn("# 26-27 season summary", body)
        self.assertIn("Generated: 2026-06-30 14:33", body)
        self.assertIn("| 5U | READY | 2 | 6 | 0 | 0 | 0 |", body)
        self.assertIn("| 8UB | READY | 2 | 10 | 0 | 0 | 1 |", body)
        self.assertIn("all READY for SportConnect upload", body)
        self.assertIn("`5U/5U_summary.md`", body)

    def test_some_blocked(self):
        results = [
            DivisionResult("5U", "READY", 2, 6, 0, 0, 0, 0),
            DivisionResult("8UB", "BLOCKED", 2, 10, 3, 1, 0, 1),
            DivisionResult("10UB", "FAILED", 0, 0, 0, 0, 0, 2),
        ]
        body = render_season_summary("26-27", results, generated_at=self._fixed_dt())
        self.assertIn("1/3 READY", body)
        self.assertIn("need attention: 8UB, 10UB", body)

    def test_from_run_classmethod(self):
        team = _build_team("TM 1", [], [
            FakePlayer("1", "Anna", age=7, gender="f", rating=4),
            FakePlayer("2", "Bob", age=7, gender="m", rating=3),
        ])
        log = [
            LogEntry("BLOCKER", "x", "y"),
            LogEntry("WARNING", "z", "w"),
            LogEntry("INFO", "n", "note"),
        ]
        r = DivisionResult.from_run("8UB", [team], log, exit_code=1)
        self.assertEqual(r.status, "BLOCKED")
        self.assertEqual(r.teams_count, 1)
        self.assertEqual(r.players_count, 2)
        self.assertEqual(r.blockers_count, 1)
        self.assertEqual(r.warnings_count, 1)
        self.assertEqual(r.notes_count, 1)

    def test_failed_classmethod(self):
        r = DivisionResult.failed("10UG", "bad config")
        self.assertEqual(r.status, "FAILED")
        self.assertEqual(r.exit_code, 2)


if __name__ == "__main__":
    unittest.main()
