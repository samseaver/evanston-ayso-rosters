"""Tests for ratings.py."""

import os
import sys
import unittest
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ratings
from ratings import resolve_one, resolve_all


@dataclass
class FakePlayer:
    player_id: str
    full_name: str
    experience_level: str = ""
    rating: Optional[int] = None


class TestResolveOne(unittest.TestCase):
    def test_uses_current_season_first(self):
        current = {("anna", "smith"): 4}
        previous = {("anna", "smith"): 3}
        p = FakePlayer("1", "Anna Smith")
        self.assertEqual(resolve_one(p, current, previous), 4)

    def test_falls_back_to_previous_season(self):
        previous = {("anna", "smith"): 3}
        p = FakePlayer("1", "Anna Smith")
        self.assertEqual(resolve_one(p, {}, previous), 3)

    def test_falls_back_to_experience_competitive(self):
        p = FakePlayer("1", "Anna Smith", experience_level="Has played competitive soccer (club)")
        self.assertEqual(resolve_one(p, {}, {}), 4)

    def test_falls_back_to_experience_recreational(self):
        p = FakePlayer("1", "Anna Smith", experience_level="Has played recreational soccer (AYSO or similar)")
        self.assertEqual(resolve_one(p, {}, {}), 3)

    def test_falls_back_to_experience_none(self):
        p = FakePlayer("1", "Anna Smith", experience_level="No or limited soccer experience")
        self.assertEqual(resolve_one(p, {}, {}), 2)

    def test_no_answer_returns_none(self):
        p = FakePlayer("1", "Anna Smith", experience_level="No Answer")
        self.assertIsNone(resolve_one(p, {}, {}))

    def test_extra_floor_applied(self):
        current = {("anna", "smith"): 2}
        p = FakePlayer("1", "Anna Smith")
        self.assertEqual(resolve_one(p, current, {}, is_extra=True), 4)

    def test_extra_floor_no_downgrade(self):
        current = {("anna", "smith"): 5}
        p = FakePlayer("1", "Anna Smith")
        self.assertEqual(resolve_one(p, current, {}, is_extra=True), 5)

    def test_accent_in_name_normalised(self):
        # ratings dict was loaded with normalised keys; the player's name has accents
        current = {("maria", "rivera"): 4}
        p = FakePlayer("1", "María Rivera")
        self.assertEqual(resolve_one(p, current, {}), 4)


class TestResolveAll(unittest.TestCase):
    def test_mutates_rating_field(self):
        players = [
            FakePlayer("1", "Anna Smith"),
            FakePlayer("2", "Bob Jones", experience_level="Has played recreational soccer"),
        ]
        current = {("anna", "smith"): 5}
        needs = resolve_all(players, current, {})
        self.assertEqual(players[0].rating, 5)
        self.assertEqual(players[1].rating, 3)
        self.assertEqual(needs, [])

    def test_collects_needs_rating(self):
        players = [
            FakePlayer("1", "Anna Smith"),
            FakePlayer("2", "Bob Jones", experience_level="No Answer"),
        ]
        current = {("anna", "smith"): 5}
        needs = resolve_all(players, current, {})
        self.assertEqual(needs, ["Bob Jones"])
        self.assertIsNone(players[1].rating)

    def test_extras_set_applies_floor(self):
        players = [
            FakePlayer("1", "Anna Smith"),
            FakePlayer("2", "Bob Jones"),
        ]
        current = {("anna", "smith"): 2, ("bob", "jones"): 5}
        resolve_all(players, current, {}, extra_player_ids={"1"})
        self.assertEqual(players[0].rating, 4)  # floored
        self.assertEqual(players[1].rating, 5)  # not in extras


if __name__ == "__main__":
    unittest.main()
