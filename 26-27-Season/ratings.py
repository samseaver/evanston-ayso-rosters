"""Resolve player ratings via the documented fallback chain.

Replaces the opaque coefficient-of-variation heuristic from the 24-25
script. The new chain is explicit and bounded:

    1. current-season ratings TSV  (Player First/Last → int)
    2. previous-season ratings TSV (carry-over for returning players)
    3. Player's Experience Level enum from the registration form:
         "Has played competitive soccer" → 4
         "Has played recreational soccer" → 3
         "No or limited soccer experience" → 2
    4. None — caller adds the player to a NEEDS_RATING list for the
       validation report; no silent default.

EXTRA-league players (10U/12U tryout-selected) get a floor of 4 applied
on top of whichever source produced the rating, so they reliably
influence the team-balance math during placement.
"""

from typing import Iterable, Optional

from names import normalise, split_first_last


# Experience-level substrings to ratings. Substring match because AYSO's
# enum values include parenthetical explanations like
# "Has played recreational soccer (AYSO or similar)".
EXPERIENCE_LEVEL_TO_RATING = [
    ("has played competitive soccer", 4),
    ("has played recreational soccer", 3),
    ("no or limited soccer experience", 2),
]

EXTRA_RATING_FLOOR = 4


def _experience_to_rating(level_text: str) -> Optional[int]:
    if not level_text or level_text == "No Answer":
        return None
    s = level_text.lower()
    for needle, rating in EXPERIENCE_LEVEL_TO_RATING:
        if needle in s:
            return rating
    return None


def resolve_one(
    player,
    current_ratings: dict,
    previous_ratings: dict,
    is_extra: bool = False,
) -> Optional[int]:
    """Return the resolved rating for a single player, or None if unknown.

    `current_ratings` and `previous_ratings` are dicts keyed by
    (normalised_first, normalised_last) → int — the shape produced by
    loaders.load_ratings().
    """
    first, last = split_first_last(normalise(player.full_name))
    key = (first, last)

    rating = current_ratings.get(key)
    if rating is None:
        rating = previous_ratings.get(key)
    if rating is None:
        rating = _experience_to_rating(player.experience_level)

    if rating is None:
        return None

    if is_extra:
        rating = max(EXTRA_RATING_FLOOR, rating)

    return rating


def resolve_all(
    players: Iterable,
    current_ratings: dict,
    previous_ratings: dict,
    extra_player_ids: Optional[set] = None,
) -> list:
    """Fill each player's .rating field in place. Return the list of
    full_names that could not be resolved (the "needs rating" list).

    Callers feed the needs-rating list into the validation report as
    BLOCKERs — the pipeline shouldn't proceed with arbitrarily-defaulted
    ratings.
    """
    extra_player_ids = extra_player_ids or set()
    needs_rating = []
    for player in players:
        is_extra = player.player_id in extra_player_ids
        rating = resolve_one(player, current_ratings, previous_ratings, is_extra)
        if rating is None:
            needs_rating.append(player.full_name)
        else:
            player.rating = rating
    return needs_rating
