"""End-to-end test: run process.py against the 8UB fixture and check the
written Teams.csv matches the SportConnect-loadable shape."""

import csv
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import process


FIXTURES = Path(__file__).parent / "fixtures"


class TestEndToEnd8UB(unittest.TestCase):
    """Stage the fixture into a temp dir so process.py can write its
    Teams.csv output without polluting the committed fixture tree."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="ayso_e2e_"))
        season = cls.tmpdir / "26-27"
        shutil.copytree(FIXTURES, season)
        cls.result = process.run(season, "8UB")
        cls.exit_code = cls.result.exit_code
        cls.output_path = season / "8UB" / "8UB_Teams.csv"
        cls.summary_path = season / "8UB" / "8UB_summary.md"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_exit_code_zero(self):
        self.assertEqual(self.exit_code, 0)

    def test_output_csv_written(self):
        self.assertTrue(self.output_path.exists())

    def test_validation_report_md_written(self):
        report_path = self.output_path.parent / "8UB_validation_report.md"
        self.assertTrue(report_path.exists())
        body = report_path.read_text()
        self.assertIn("# 8UB validation report", body)
        self.assertIn("**Status:** READY", body)

    def test_division_summary_md_written(self):
        self.assertTrue(self.summary_path.exists())
        body = self.summary_path.read_text()
        self.assertIn("# 8UB summary", body)
        self.assertIn("**Status:** READY", body)
        self.assertIn("## Team 1 — 8UB - 01", body)
        self.assertIn("## Overrides used", body)
        self.assertIn("`coach_children` · Jordan Lee", body)

    def test_result_object_populated(self):
        self.assertEqual(self.result.division, "8UB")
        self.assertEqual(self.result.status, "READY")
        self.assertEqual(self.result.teams_count, 2)
        self.assertEqual(self.result.players_count, 10)
        self.assertEqual(self.result.blockers_count, 0)

    def test_output_header(self):
        with open(self.output_path) as f:
            reader = csv.reader(f)
            header = next(reader)
        self.assertEqual(header, [
            "TeamName", "PlayerID", "VolunteerID", "VolunteerTypeID",
            "Player Name", "Team Personnel Name", "Team Personnel Role",
        ])

    def test_output_contains_player_and_coach_rows(self):
        with open(self.output_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        player_rows = [r for r in rows if r["PlayerID"]]
        coach_rows = [r for r in rows if r["VolunteerID"]]
        self.assertEqual(len(player_rows), 10)
        self.assertGreaterEqual(len(coach_rows), 4)

    def test_team_name_format(self):
        with open(self.output_path) as f:
            reader = csv.DictReader(f)
            team_names = {r["TeamName"] for r in reader}
        # "8UB - 01 - smith/johnson" shape (surnames lowercased via normalise)
        for tn in team_names:
            self.assertTrue(tn.startswith("8UB - "), f"unexpected team name: {tn}")

    def test_player_appears_under_one_team(self):
        with open(self.output_path) as f:
            reader = csv.DictReader(f)
            player_rows = [r for r in reader if r["PlayerID"]]
        from collections import Counter
        counts = Counter(r["PlayerID"] for r in player_rows)
        for pid, c in counts.items():
            self.assertEqual(c, 1, f"PlayerID {pid} appears on {c} teams")


class TestEndToEnd10UBExtras(unittest.TestCase):
    """End-to-end against the 10UB fixture, which exercises EXTRA-league
    loading: 4 names in Extra_Allocated.csv, 3 of which match the roster
    (Ben Chen is intentionally absent to exercise the extra_not_in_core
    warning path)."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="ayso_e2e_10ub_"))
        season = cls.tmpdir / "26-27"
        shutil.copytree(FIXTURES, season)
        cls.result = process.run(season, "10UB")
        cls.season = season

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_exit_zero_despite_warning(self):
        # Ben Chen missing from roster is a WARNING, not a BLOCKER.
        self.assertEqual(self.result.exit_code, 0)

    def test_warning_logged_for_missing_extra(self):
        self.assertGreaterEqual(self.result.warnings_count, 1)

    def test_all_11_roster_players_placed(self):
        # 11 players in the Unallocated fixture; 4th extra (Ben Chen)
        # is intentionally not in the roster so it doesn't get placed.
        self.assertEqual(self.result.players_count, 11)

    def test_teams_csv_written(self):
        out = self.season / "10UB" / "10UB_Teams.csv"
        self.assertTrue(out.exists())
        body = out.read_text()
        for matched_extra in ("Logan Brown", "Hugo Patel", "Ari Choi"):
            self.assertIn(matched_extra, body, f"Expected {matched_extra} in output CSV")
        self.assertNotIn("Ben Chen", body)

    def test_validation_report_lists_missing_extra(self):
        report = (self.season / "10UB" / "10UB_validation_report.md").read_text()
        self.assertIn("extra_not_in_core", report)
        self.assertIn("Ben Chen", report)


if __name__ == "__main__":
    unittest.main()
