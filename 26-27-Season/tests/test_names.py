"""Unit tests for names.py.

Run from the 26-27-Season directory:
    python -m unittest tests.test_names
or
    python tests/test_names.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from names import normalise, names_match, find_matches, aliases_of, split_first_last


class TestNormalise(unittest.TestCase):
    def test_lowercase(self):
        self.assertEqual(normalise("John Smith"), "john smith")

    def test_accent_strip(self):
        self.assertEqual(normalise("José García"), "jose garcia")
        self.assertEqual(normalise("María"), "maria")
        self.assertEqual(normalise("Zoë"), "zoe")

    def test_parenthetical_removal(self):
        self.assertEqual(normalise("John Smith (13)"), "john smith")
        self.assertEqual(normalise("John Smith (13 yrs)"), "john smith")
        self.assertEqual(normalise("Anna (age 7) Lopez"), "anna lopez")

    def test_whitespace_collapse(self):
        self.assertEqual(normalise("   John   Smith   "), "john smith")
        self.assertEqual(normalise("John\tSmith"), "john smith")

    def test_apostrophe_removal(self):
        self.assertEqual(normalise("Mary-Anne O'Brien"), "mary-anne obrien")
        self.assertEqual(normalise("D'Angelo"), "dangelo")

    def test_hyphen_preserved(self):
        self.assertEqual(normalise("Jones-Lewis"), "jones-lewis")

    def test_other_punctuation_dropped(self):
        self.assertEqual(normalise("John P. Smith"), "john p smith")


class TestSplitFirstLast(unittest.TestCase):
    def test_two_tokens(self):
        self.assertEqual(split_first_last("john smith"), ("john", "smith"))

    def test_multi_word_surname(self):
        self.assertEqual(split_first_last("maria van der berg"), ("maria", "van der berg"))

    def test_single_token(self):
        self.assertEqual(split_first_last("madonna"), ("madonna", ""))

    def test_empty(self):
        self.assertEqual(split_first_last(""), ("", ""))


class TestAliases(unittest.TestCase):
    def test_known_alias_groups_with_canonical(self):
        self.assertIn("robert", aliases_of("bob"))
        self.assertIn("bob", aliases_of("robert"))
        self.assertIn("rob", aliases_of("bobby"))

    def test_unknown_name_returns_singleton(self):
        self.assertEqual(aliases_of("xyzzy"), {"xyzzy"})


class TestNamesMatch(unittest.TestCase):
    def test_exact(self):
        self.assertTrue(names_match("John Smith", "John Smith"))

    def test_case_insensitive(self):
        self.assertTrue(names_match("JOHN smith", "john SMITH"))

    def test_accents_normalised(self):
        self.assertTrue(names_match("José García", "Jose Garcia"))

    def test_nickname_bob_robert(self):
        self.assertTrue(names_match("Bob Smith", "Robert Smith"))

    def test_nickname_liz_elizabeth(self):
        self.assertTrue(names_match("Liz Johnson", "Elizabeth Johnson"))

    def test_nickname_pat_patricia(self):
        self.assertTrue(names_match("Pat Lee", "Patricia Lee"))

    def test_different_last_name_fails(self):
        self.assertFalse(names_match("John Smith", "John Jones"))

    def test_unrelated_first_names_fail(self):
        self.assertFalse(names_match("John Smith", "Jane Smith"))

    def test_parenthetical_ignored(self):
        self.assertTrue(names_match("John Smith (13)", "John Smith"))


class TestFindMatches(unittest.TestCase):
    def test_finds_all_nickname_matches(self):
        candidates = ["Anna Smith", "Bob Johnson", "Robert Johnson", "Liz Davis"]
        self.assertEqual(
            set(find_matches("Bob Johnson", candidates)),
            {"Bob Johnson", "Robert Johnson"},
        )

    def test_no_match_returns_empty(self):
        self.assertEqual(find_matches("Bob Jones", ["John Smith", "Jane Doe"]), [])

    def test_unambiguous_match(self):
        self.assertEqual(
            find_matches("Maria Rivera", ["John Smith", "María Rivera", "Bob Lee"]),
            ["María Rivera"],
        )


if __name__ == "__main__":
    unittest.main()
