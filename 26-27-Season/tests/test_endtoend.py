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
        cls.exit_code = process.run(season, "8UB")
        cls.output_path = season / "8UB" / "8UB_Teams.csv"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_exit_code_zero(self):
        self.assertEqual(self.exit_code, 0)

    def test_output_csv_written(self):
        self.assertTrue(self.output_path.exists())

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


if __name__ == "__main__":
    unittest.main()
