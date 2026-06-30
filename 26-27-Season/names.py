"""Name normalisation and matching for the AYSO rosters pipeline.

Replaces the substring-based `find_player` from the 24-25/25-26 scripts.
The new approach: normalise both sides to a canonical form, then compare
with nickname-awareness on the first name only.

Normalisation:
    - lowercase
    - strip diacritics (José → jose, García → garcia)
    - drop parenthetical annotations (\"John Smith (13)\" → \"john smith\")
    - drop punctuation except hyphens (hyphenated surnames are common)
    - collapse internal whitespace

Matching:
    - last names must match exactly after normalisation
    - first names match if they share a canonical form in the NICKNAMES table
      (bob/robert/rob/bobby all canonicalise to robert)

Caller is expected to disambiguate when find_matches returns 0 or >1
candidates — either by adding an entry to the division's overrides.yaml,
or by raising a BLOCKER in the validation report.
"""

import re
import unicodedata


# Common English nickname → canonical mappings. Bidirectional once built.
# Keep this hand-curated rather than pulling in a library; the set is small
# and we want to know exactly what's matched.
NICKNAMES = {
    "bob": "robert", "rob": "robert", "bobby": "robert", "robbie": "robert",
    "bill": "william", "will": "william", "billy": "william", "willie": "william",
    "jim": "james", "jimmy": "james", "jamie": "james",
    "tom": "thomas", "tommy": "thomas",
    "tim": "timothy",
    "mike": "michael", "mickey": "michael", "mick": "michael",
    "rick": "richard", "ricky": "richard", "dick": "richard", "rich": "richard",
    "dan": "daniel", "danny": "daniel",
    "joe": "joseph", "joey": "joseph",
    "sam": "samuel", "sammy": "samuel",
    "andy": "andrew", "drew": "andrew",
    "ed": "edward", "eddie": "edward",
    "tony": "anthony",
    "nick": "nicholas",
    "chris": "christopher",
    "matt": "matthew",
    "dave": "david", "davey": "david",
    "ben": "benjamin", "benny": "benjamin",
    "alex": "alexander",
    "nate": "nathan",
    "zach": "zachary",

    "liz": "elizabeth", "beth": "elizabeth", "betty": "elizabeth", "eliza": "elizabeth",
    "kate": "katherine", "katie": "katherine", "kathy": "katherine", "kat": "katherine",
    "pat": "patricia", "patty": "patricia", "patsy": "patricia", "trish": "patricia",
    "jen": "jennifer", "jenny": "jennifer",
    "maggie": "margaret", "meg": "margaret", "peggy": "margaret",
    "sue": "susan", "susie": "susan",
    "cathy": "catherine", "cat": "catherine",
    "abby": "abigail",
    "vicky": "victoria", "tori": "victoria",
    "becky": "rebecca",
    "annie": "anne",
}


def _build_alias_groups():
    """canonical → set of names (canonical + every alias mapping to it)."""
    groups = {}
    for alias, canonical in NICKNAMES.items():
        groups.setdefault(canonical, {canonical}).add(alias)
    return groups


_ALIAS_GROUPS = _build_alias_groups()


def normalise(name):
    """Canonical form of a name for comparison.

    >>> normalise("José García")
    'jose garcia'
    >>> normalise("Mary-Anne O'Brien")
    "mary-anne obrien"
    >>> normalise("  John   Smith (13 yrs)  ")
    'john smith'
    """
    s = re.sub(r"\s*\(.*?\)", "", name)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def aliases_of(token):
    """All names that share a canonical form with this token (including itself)."""
    if token in NICKNAMES:
        canonical = NICKNAMES[token]
    elif token in _ALIAS_GROUPS:
        canonical = token
    else:
        return {token}
    return _ALIAS_GROUPS[canonical]


def split_first_last(normalised):
    """Split a normalised full name into (first_token, rest_joined).

    The last name is the joined tail, which preserves multi-word surnames
    like "van der berg".

    >>> split_first_last("john smith")
    ('john', 'smith')
    >>> split_first_last("maria van der berg")
    ('maria', 'van der berg')
    >>> split_first_last("madonna")
    ('madonna', '')
    """
    parts = normalised.split()
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], " ".join(parts[1:]))


def names_match(a, b):
    """True if two names refer to the same person under nickname-aware
    normalisation.

    Last names must match exactly after normalisation; first names match
    if they share a canonical form in the NICKNAMES table.

    >>> names_match("Bob Smith", "Robert Smith")
    True
    >>> names_match("José García", "Jose Garcia")
    True
    >>> names_match("John Smith", "John Jones")
    False
    """
    na, nb = normalise(a), normalise(b)
    if na == nb:
        return True
    fa, la = split_first_last(na)
    fb, lb = split_first_last(nb)
    if la != lb:
        return False
    return bool(aliases_of(fa) & aliases_of(fb))


def find_matches(target, candidates):
    """Return the subset of candidates whose name matches the target.

    Empty list = no match (record as BLOCKER, prompt overrides.yaml entry).
    Length 1 = unambiguous resolution.
    Length >1 = ambiguous (record as BLOCKER, prompt overrides.yaml entry).
    """
    return [c for c in candidates if names_match(target, c)]
