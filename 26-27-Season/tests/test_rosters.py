"""End-to-end test for rosters.py against a multi-division fixture (5U + 8UB)."""

import os
import shutil
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rosters


FIXTURES = Path(__file__).parent / "fixtures"


class TestRostersBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="ayso_rosters_"))
        cls.season = cls.tmpdir / "26-27"
        shutil.copytree(FIXTURES, cls.season)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_run_all_divisions_finds_both_fixtures(self):
        with patch("sys.stdout", new_callable=StringIO) as out:
            code = rosters.run(self.season)
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("5U: READY", text)
        self.assertIn("8UB: READY", text)
        self.assertIn("All divisions ready", text)

    def test_season_summary_md_written(self):
        with patch("sys.stdout", new_callable=StringIO):
            rosters.run(self.season)
        season_summary = self.season / "season_summary.md"
        self.assertTrue(season_summary.exists())
        body = season_summary.read_text()
        self.assertIn("26-27 season summary", body)
        self.assertIn("| 5U | READY", body)
        self.assertIn("| 8UB | READY", body)
        self.assertIn("all READY", body)

    def test_only_filters_to_one_division(self):
        with patch("sys.stdout", new_callable=StringIO) as out:
            code = rosters.run(self.season, only=["8UB"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("8UB: READY", text)
        self.assertNotIn("5U: READY", text)

    def test_skip_excludes_division(self):
        with patch("sys.stdout", new_callable=StringIO) as out:
            code = rosters.run(self.season, skip=["5U"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("8UB: READY", text)
        self.assertNotIn("5U: READY", text)

    def test_missing_season_dir_returns_2(self):
        code = rosters.run(self.tmpdir / "does_not_exist")
        self.assertEqual(code, 2)

    def test_no_divisions_found_returns_2(self):
        empty = self.tmpdir / "empty"
        empty.mkdir()
        code = rosters.run(empty)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
