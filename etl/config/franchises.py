"""Franchise identity policy.

Maps every team-name *variant* that appears in the Cricsheet data to a stable
``franchise_id``. This encodes the merge policy agreed for the data core:

  * Pure rebrands collapse into one continuous franchise
    (Delhi Daredevils = Delhi Capitals, Kings XI Punjab = Punjab Kings,
    RCB Bangalore = Bengaluru, Rising Pune Supergiant(s)).
  * Deccan Chargers and Sunrisers Hyderabad stay SEPARATE franchises
    (they were legally distinct entities), even though both played in Hyderabad.

``franchise_name`` is the canonical display name (the current/most recent name).
The per-season name a team actually used is preserved separately on each match,
so season pages can still show "Delhi Daredevils" for 2008-2018.
"""

# franchise_id -> (canonical display name, [all name variants in the data])
FRANCHISES = {
    "csk":    ("Chennai Super Kings",        ["Chennai Super Kings"]),
    "deccan": ("Deccan Chargers",            ["Deccan Chargers"]),
    "dc":     ("Delhi Capitals",             ["Delhi Capitals", "Delhi Daredevils"]),
    "gl":     ("Gujarat Lions",              ["Gujarat Lions"]),
    "gt":     ("Gujarat Titans",             ["Gujarat Titans"]),
    "pbks":   ("Punjab Kings",               ["Punjab Kings", "Kings XI Punjab"]),
    "ktk":    ("Kochi Tuskers Kerala",       ["Kochi Tuskers Kerala"]),
    "kkr":    ("Kolkata Knight Riders",      ["Kolkata Knight Riders"]),
    "lsg":    ("Lucknow Super Giants",       ["Lucknow Super Giants"]),
    "mi":     ("Mumbai Indians",             ["Mumbai Indians"]),
    "pwi":    ("Pune Warriors",              ["Pune Warriors"]),
    "rr":     ("Rajasthan Royals",           ["Rajasthan Royals"]),
    "rps":    ("Rising Pune Supergiants",    ["Rising Pune Supergiants", "Rising Pune Supergiant"]),
    "rcb":    ("Royal Challengers Bengaluru", ["Royal Challengers Bengaluru", "Royal Challengers Bangalore"]),
    "srh":    ("Sunrisers Hyderabad",        ["Sunrisers Hyderabad"]),
}

# name variant (exact string from data) -> franchise_id
NAME_TO_FRANCHISE = {
    name: fid
    for fid, (_canonical, variants) in FRANCHISES.items()
    for name in variants
}


def franchise_id(team_name: str) -> str:
    """Resolve a raw team name to its franchise_id. Raises on unknown names so a
    new/renamed team can never be silently mis-bucketed."""
    try:
        return NAME_TO_FRANCHISE[team_name]
    except KeyError:
        raise KeyError(
            f"Unknown team name {team_name!r}. Add it to etl/config/franchises.py."
        )
