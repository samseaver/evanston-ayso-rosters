"""Write the SportConnect-loadable per-division Teams CSV.

Output matches the 24-25/25-26 format exactly so it can be uploaded into
SportConnect without any post-processing. Header:

    TeamName, PlayerID, VolunteerID, VolunteerTypeID, Player Name,
    Team Personnel Name, Team Personnel Role

Each team contributes one row per player (PlayerID populated, volunteer
columns blank) and one row per coach (volunteer columns populated, player
columns blank). Team name format:

    <DIVISION> - <NN> - <surname1>/<surname2>/...

where NN is a zero-padded sequence number and the surnames come from the
team's coaches in their Coaches.tsv order.
"""

import csv
from typing import Iterable

from loaders import Volunteer
from names import normalise

OUTPUT_HEADER = [
    "TeamName",
    "PlayerID",
    "VolunteerID",
    "VolunteerTypeID",
    "Player Name",
    "Team Personnel Name",
    "Team Personnel Role",
]


def team_display_name(division: str, index: int, team) -> str:
    """Build the canonical team name used in <DIV>_Teams.csv.

    Matches the 25-26 script's format exactly: DIVISION - NN - lastname/lastname/...
    where each lastname is the coach's last-name column lowercased with the
    last space-separated token retained. Punctuation like apostrophes and
    hyphens is preserved (e.g. o'example stays o'example; hyphenated-name
    stays hyphenated).

    Do NOT use names.normalise() here — that's for *matching* (dropping
    accents and punctuation to compare). Display needs the punctuation kept
    so team names in Teams.csv agree with any existing SportConnect labels.
    """
    surnames = []
    for ca in team.coaches:
        if not ca.last_name.strip():
            continue
        tokens = ca.last_name.strip().lower().split()
        if tokens:
            surnames.append(tokens[-1])
    surnames_part = "/".join(surnames) if surnames else "unknown"
    return f"{division} - {index:02d} - {surnames_part}"


def write_teams_csv(
    output_path,
    division: str,
    teams,
    volunteers: Iterable[Volunteer],
):
    """Write the SportConnect upload CSV.

    Coach VolunteerID/VolunteerTypeID are looked up by name in `volunteers`
    (from Personnel.txt). A coach with no matching volunteer record is
    written with blank volunteer fields — caller is responsible for raising
    that as a WARNING in the validation report.
    """
    from names import names_match  # local: avoids forcing names import for callers who don't need it

    volunteer_by_normalised_name = {normalise(v.full_name): v for v in volunteers}

    with open(output_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(OUTPUT_HEADER)
        for i, team in enumerate(teams, start=1):
            tname = team_display_name(division, i, team)
            for player in team.players:
                rating_disp = str(player.rating) if player.rating is not None else ""
                w.writerow([
                    tname,
                    player.player_id,
                    "",
                    "",
                    player.full_name,
                    rating_disp,
                    "",
                ])
            for ca in team.coaches:
                coach_full = f"{ca.first_name} {ca.last_name}"
                v = volunteer_by_normalised_name.get(normalise(coach_full))
                if v is None:
                    for vname, vrec in volunteer_by_normalised_name.items():
                        if names_match(coach_full, vname):
                            v = vrec
                            break
                vid = v.volunteer_id if v else ""
                vtid = v.volunteer_type_id if v else ""
                vname = v.full_name if v else coach_full
                vrole = v.role if v else ca.role
                w.writerow([tname, "", vid, vtid, "", vname, vrole])
