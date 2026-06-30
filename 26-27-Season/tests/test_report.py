"""Tests for report.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assembly import LogEntry, TeamRoster
from report import render_report


class TestRenderReport(unittest.TestCase):
    def test_clean_report(self):
        body = render_report("8UB", [TeamRoster("TM 1")], [])
        self.assertIn("# 8UB validation report", body)
        self.assertIn("**Status:** READY", body)
        self.assertIn("## Clean", body)
        self.assertNotIn("## BLOCKERs", body)

    def test_blocker_sets_blocked_status(self):
        log = [LogEntry("BLOCKER", "unassigned", "Foo Bar could not be placed")]
        body = render_report("8UB", [], log)
        self.assertIn("**Status:** BLOCKED", body)
        self.assertIn("## BLOCKERs", body)
        self.assertIn("unassigned", body)
        self.assertIn("Foo Bar", body)

    def test_warning_only_keeps_ready_status(self):
        log = [LogEntry("WARNING", "cleanup_placement", "X placed during cleanup")]
        body = render_report("8UB", [TeamRoster("TM 1")], log)
        self.assertIn("**Status:** READY", body)
        self.assertIn("## Warnings", body)
        self.assertNotIn("## BLOCKERs", body)

    def test_info_renders_notes_section(self):
        log = [LogEntry("INFO", "player_note", "Anna Smith: special note")]
        body = render_report("8UB", [TeamRoster("TM 1")], log)
        self.assertIn("## Notes", body)
        self.assertIn("Anna Smith: special note", body)

    def test_counts_summary(self):
        log = [
            LogEntry("BLOCKER", "x", "a"),
            LogEntry("BLOCKER", "y", "b"),
            LogEntry("WARNING", "z", "c"),
            LogEntry("INFO", "w", "d"),
        ]
        body = render_report("8UB", [TeamRoster("TM 1"), TeamRoster("TM 2")], log)
        self.assertIn("2 team(s)", body)
        self.assertIn("2 blocker(s), 1 warning(s), 1 note(s)", body)


if __name__ == "__main__":
    unittest.main()
