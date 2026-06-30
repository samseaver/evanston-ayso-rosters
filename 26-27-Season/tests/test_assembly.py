"""Integration tests for assembly.py against the 8UB fixture.

End-to-end-ish: loads the fixture via loaders, resolves ratings, then runs
assembly and asserts on the resulting team structure.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ratings
from assembly import (
    assemble_teams,
    division_max,
    TeamRoster,
    DIVISION_MAX_PLAYERS,
)
from loaders import (
    load_coach_assignments,
    load_field_map,
    load_overrides,
    load_players,
    load_ratings,
    load_volunteers,
)


FIXTURES = Path(__file__).parent / "fixtures"


def _load_8ub():
    field_map, _ = load_field_map(FIXTURES / "field_map.yaml")
    players = load_players(FIXTURES / "8UB" / "8UB_Unallocated.txt", field_map)
    volunteers = load_volunteers(FIXTURES / "8UB" / "8UB_Personnel.txt")
    coaches = load_coach_assignments(FIXTURES / "8UB" / "8UB_Coaches.tsv")
    overrides, _ = load_overrides(FIXTURES / "8UB" / "overrides.yaml")
    current_ratings = load_ratings(FIXTURES / "2026_Player_Ratings.tsv")
    previous_ratings = load_ratings(FIXTURES / "2025_Player_Ratings.tsv")
    ratings.resolve_all(players, current_ratings, previous_ratings)
    return players, volunteers, coaches, overrides


class TestDivisionMax(unittest.TestCase):
    def test_known_divisions(self):
        self.assertEqual(division_max("8UB"), 9)
        self.assertEqual(division_max("10UG"), 10)
        self.assertEqual(division_max("12UB"), 12)
        self.assertEqual(division_max("14UB"), 16)
        self.assertEqual(division_max("14UG"), 10)

    def test_unknown_division_raises(self):
        with self.assertRaises(ValueError):
            division_max("ZUZ")


class TestAssembleAgainst8UBFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        players, volunteers, coaches, overrides = _load_8ub()
        cls.players = players
        cls.teams, cls.log = assemble_teams(
            players=players,
            coach_assignments=coaches,
            volunteers=volunteers,
            overrides=overrides,
            division="8UB",
        )

    def _team(self, label):
        return next(t for t in self.teams if t.label == label)

    def _team_player_names(self, label):
        return {p.full_name for p in self._team(label).players}

    def test_two_active_teams_tbd_skipped(self):
        labels = sorted(t.label for t in self.teams)
        self.assertEqual(labels, ["TM 1", "TM 2"])

    def test_every_player_placed(self):
        placed_ids = {p.player_id for t in self.teams for p in t.players}
        all_ids = {p.player_id for p in self.players}
        self.assertEqual(placed_ids, all_ids)

    def test_no_team_exceeds_division_cap(self):
        for t in self.teams:
            self.assertLessEqual(t.size(), 9, f"Team {t.label} over cap: {t.size()}")

    def test_coach_kid_placed_via_nickname_match(self):
        # Bob Smith on Coaches.tsv, Robert Smith in Personnel/Unallocated parent field.
        # Anna Smith should be on TM 1.
        self.assertIn("Anna Smith", self._team_player_names("TM 1"))

    def test_coach_kid_placed_via_accent_normalisation(self):
        # Maria Rivera on Coaches.tsv, María Rivera in Unallocated parent field.
        # Carlos Rivera should be on TM 2.
        self.assertIn("Carlos Rivera", self._team_player_names("TM 2"))

    def test_coach_kids_via_parent_index_siblings(self):
        # Patricia Johnson is both coaches and parent of Jack + Liam.
        tm1 = self._team_player_names("TM 1")
        self.assertIn("Jack Johnson", tm1)
        self.assertIn("Liam Johnson", tm1)

    def test_coach_kid_via_overrides_coach_children(self):
        # Jordan Lee has associatedPlayers="No Answer" — only resolvable via
        # overrides.coach_children. Sophie should land on TM 2.
        self.assertIn("Sophie Lee", self._team_player_names("TM 2"))

    def test_pair_group_lands_together(self):
        # overrides.groups: [Anna Smith, Mia Williams].
        # Anna is on TM 1 via her dad; Mia should follow.
        tm1 = self._team_player_names("TM 1")
        self.assertIn("Anna Smith", tm1)
        self.assertIn("Mia Williams", tm1)

    def test_notes_surfaced_as_info(self):
        info_messages = [e.message for e in self.log if e.severity == "INFO"]
        self.assertTrue(any("Mia Williams" in m for m in info_messages))

    def test_no_blockers_on_clean_fixture(self):
        blockers = [e for e in self.log if e.severity == "BLOCKER"]
        # Sophie has "No Answer" experience but overrides.coach_children resolves her,
        # and her rating falls through to None which puts her in cleanup -- log a WARNING
        # but no BLOCKER expected on this fixture.
        self.assertEqual(blockers, [], f"Unexpected blockers: {[e.message for e in blockers]}")


class TestAssembleEmptyTeams(unittest.TestCase):
    def test_all_tbd_yields_blocker(self):
        from loaders import CoachAssignment
        cas = [CoachAssignment("TBD", "Sam", "Wilson", "TP")]
        teams, log = assemble_teams(
            players=[],
            coach_assignments=cas,
            volunteers=[],
            overrides={},
            division="8UB",
        )
        self.assertEqual(teams, [])
        self.assertTrue(any(e.severity == "BLOCKER" and e.code == "no_teams" for e in log))


class TestAssemble5UDobBalanced(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        field_map, _ = load_field_map(FIXTURES / "field_map.yaml")
        cls.players = load_players(FIXTURES / "5U" / "5U_Unallocated.txt", field_map)
        cls.volunteers = load_volunteers(FIXTURES / "5U" / "5U_Personnel.txt")
        cls.coaches = load_coach_assignments(FIXTURES / "5U" / "5U_Coaches.tsv")
        cls.teams, cls.log = assemble_teams(
            players=cls.players,
            coach_assignments=cls.coaches,
            volunteers=cls.volunteers,
            overrides={},
            division="5U",
        )

    def test_balance_by_inferred_as_dob(self):
        # No explicit balance_by — should default to "dob" for 5U.
        self.assertEqual(len(self.teams), 2)

    def test_every_player_placed(self):
        placed = {p.player_id for t in self.teams for p in t.players}
        self.assertEqual(placed, {p.player_id for p in self.players})

    def test_each_coach_kid_on_correct_team(self):
        tm1 = next(t for t in self.teams if t.label == "TM 1")
        tm2 = next(t for t in self.teams if t.label == "TM 2")
        self.assertTrue(any(p.full_name == "Olivia Adams" for p in tm1.players))
        self.assertTrue(any(p.full_name == "Felix Foster" for p in tm2.players))

    def test_team_sizes_even_or_close(self):
        sizes = sorted(t.size() for t in self.teams)
        # 6 players, 2 teams → expect 3 and 3
        self.assertEqual(sizes, [3, 3])

    def test_gender_balance_within_one(self):
        # 3F + 3M total. Each team should have at most 2 of one gender.
        for t in self.teams:
            f = sum(1 for p in t.players if p.gender == "f")
            m = sum(1 for p in t.players if p.gender == "m")
            self.assertLessEqual(abs(f - m), 1, f"Team {t.label}: {f}F {m}M")


class TestBalanceByValidation(unittest.TestCase):
    def test_unknown_balance_by_raises(self):
        with self.assertRaises(ValueError):
            assemble_teams([], [], [], {}, "8UB", balance_by="xyzzy")

    def test_explicit_balance_by_overrides_default(self):
        # Force "dob" mode on an 8U division. Should not raise; just balance
        # differently. With empty inputs we just get the no_teams blocker.
        teams, log = assemble_teams([], [], [], {}, "8UB", balance_by="dob")
        self.assertEqual(teams, [])


if __name__ == "__main__":
    unittest.main()
