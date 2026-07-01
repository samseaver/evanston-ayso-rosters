"""Integration tests for loaders.py against the 8UB fixture.

The fixture under tests/fixtures/ mirrors the column structure of real
25-26 AYSO exports but contains only synthetic data — see file headers in
the fixture for the naming conventions used.

Run from the 26-27-Season directory:
    python -m unittest tests.test_loaders
or
    python tests/test_loaders.py
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loaders import (
    Player,
    Volunteer,
    CoachAssignment,
    ValidationError,
    load_field_map,
    load_overrides,
    load_players,
    load_volunteers,
    load_coach_assignments,
    load_extras,
    load_ratings,
)


FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadPlayers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.field_map, _ = load_field_map(FIXTURES / "field_map.yaml")
        cls.players = load_players(FIXTURES / "8UB" / "8UB_Unallocated.txt", cls.field_map)

    def test_count(self):
        self.assertEqual(len(self.players), 10)

    def test_first_player_fields(self):
        p = self.players[0]
        self.assertEqual(p.player_id, "90000001")
        self.assertEqual(p.full_name, "Anna Smith")
        self.assertEqual(p.age, 7)
        self.assertEqual(p.gender, "f")
        self.assertEqual(p.parent_first, "Robert")
        self.assertEqual(p.parent_last, "Smith")
        self.assertEqual(p.payment_status, "Paid")
        self.assertEqual(p.years_experience, 2)

    def test_no_answer_years_experience_becomes_none(self):
        # Sophie has "No Answer" in the years_experience column but a real
        # experience_level enum — exercises the per-column parse path.
        sophie = next(p for p in self.players if p.full_name == "Sophie Lee")
        self.assertIsNone(sophie.years_experience)
        self.assertIn("recreational", sophie.experience_level.lower())

    def test_payment_warning_detectable(self):
        mia = next(p for p in self.players if p.full_name == "Mia Williams")
        self.assertNotEqual(mia.payment_status, "Paid")

    def test_accented_parent_name_preserved(self):
        carlos = next(p for p in self.players if p.full_name == "Carlos Rivera")
        self.assertEqual(carlos.parent_first, "María")

    def test_missing_column_raises(self):
        bad = FIXTURES / "8UB" / "8UB_Unallocated.txt"
        bad_field_map = {"fields": {"years_experience": "Does Not Exist(00000000)",
                                    "experience_level": "Player's Experience Level(99999002)"}}
        with self.assertRaises(ValidationError):
            load_players(bad, bad_field_map)


class TestLoadVolunteers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.volunteers = load_volunteers(FIXTURES / "8UB" / "8UB_Personnel.txt")

    def test_count(self):
        self.assertEqual(len(self.volunteers), 5)

    def test_associated_players_parsed(self):
        patricia = next(v for v in self.volunteers if v.full_name == "Patricia Johnson")
        self.assertEqual(patricia.associated_players, ["Jack Johnson", "Liam Johnson"])

    def test_no_answer_associated_players_yields_empty_list(self):
        jordan = next(v for v in self.volunteers if v.full_name == "Jordan Lee")
        self.assertEqual(jordan.associated_players, [])

    def test_role(self):
        sam = next(v for v in self.volunteers if v.full_name == "Sam Wilson")
        self.assertEqual(sam.role, "Team Parent")


class TestLoadCoachAssignments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coaches = load_coach_assignments(FIXTURES / "8UB" / "8UB_Coaches.tsv")

    def test_count(self):
        self.assertEqual(len(self.coaches), 5)

    def test_tbd_kept(self):
        tbd = [c for c in self.coaches if c.team_label == "TBD"]
        self.assertEqual(len(tbd), 1)
        self.assertEqual(tbd[0].first_name, "Sam")

    def test_nickname_in_coaches_file_preserved(self):
        bob = next(c for c in self.coaches if c.first_name == "Bob")
        self.assertEqual(bob.last_name, "Smith")
        self.assertEqual(bob.team_label, "TM 1")


class TestLoadRatings(unittest.TestCase):
    def test_current_season(self):
        ratings = load_ratings(FIXTURES / "2026_Player_Ratings.tsv")
        self.assertEqual(ratings[("anna", "smith")], 4)
        self.assertEqual(ratings[("jack", "johnson")], 3)
        self.assertEqual(ratings[("liam", "johnson")], 2)
        self.assertEqual(len(ratings), 3)

    def test_previous_season(self):
        ratings = load_ratings(FIXTURES / "2025_Player_Ratings.tsv")
        self.assertEqual(ratings[("emma", "davis")], 4)


class TestLoadExtras(unittest.TestCase):
    def test_loads_10ub_fixture(self):
        extras = load_extras(FIXTURES / "10UB" / "10UB_Extra_Allocated.csv")
        self.assertEqual(len(extras), 4)
        self.assertIn(("Logan", "Brown"), extras)
        self.assertIn(("Ben", "Chen"), extras)

    def test_missing_file_returns_empty(self):
        extras = load_extras(FIXTURES / "8UB" / "8UB_Extra_Allocated.csv")
        # 8UB fixture intentionally doesn't have one — should not raise.
        self.assertEqual(extras, [])

    def test_missing_required_column_raises(self):
        # Synthetic path that exists but won't have the column.
        bogus = FIXTURES / "8UB" / "8UB_Coaches.tsv"
        with self.assertRaises(ValidationError):
            load_extras(bogus)


class TestLoadOverrides(unittest.TestCase):
    def test_full_fixture_overrides_parse(self):
        data, warnings = load_overrides(FIXTURES / "8UB" / "overrides.yaml")
        self.assertEqual(warnings, [])
        self.assertEqual(data["groups"], [["Anna Smith", "Mia Williams"]])
        self.assertEqual(data["coach_children"]["Jordan Lee"], ["Sophie Lee"])
        self.assertIn("Mia Williams", data["notes"])


if __name__ == "__main__":
    unittest.main()
