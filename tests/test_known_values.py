"""Spot-checks against independently known IPL truth. A regression in the
counting rules or identity resolution will fail one of these."""

from tests.conftest import scalar


def test_highest_individual_score_is_gayle_175(con):
    name, score = con.execute(
        "SELECT display_name, score FROM lb_highest_scores LIMIT 1"
    ).fetchone()
    assert name == "CH Gayle"
    assert score == "175*"


def test_first_match_mccullum_158(con):
    """McCullum's 158* in the inaugural 2008 match is the second-highest score."""
    assert scalar(con, """
        SELECT count(*) FROM lb_highest_scores
        WHERE display_name = 'BB McCullum' AND score = '158*'
    """) == 1


def test_best_bowling_figures(con):
    name, figures = con.execute(
        "SELECT display_name, figures FROM lb_best_bowling LIMIT 1"
    ).fetchone()
    assert name == "AS Joseph"
    assert figures == "6/12"


def test_highest_team_total_srh_287(con):
    team, runs = con.execute(
        "SELECT team, total_runs FROM lb_highest_totals LIMIT 1"
    ).fetchone()
    assert team == "Sunrisers Hyderabad"
    assert runs == 287


def test_kohli_is_leading_run_scorer(con):
    name = scalar(con, "SELECT display_name FROM batting_career ORDER BY runs DESC LIMIT 1")
    assert name == "V Kohli"


# --- identity resolution ---

def test_exactly_fifteen_franchises(con):
    assert scalar(con, "SELECT count(*) FROM teams") == 15


def test_delhi_rebrand_merged(con):
    """Daredevils + Capitals collapse to one franchise with combined matches."""
    rows = con.execute(
        "SELECT matches FROM team_records WHERE franchise_id = 'dc'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] > 250


def test_deccan_and_srh_stay_separate(con):
    ids = {r[0] for r in con.execute("SELECT franchise_id FROM teams").fetchall()}
    assert {"deccan", "srh"} <= ids


def test_player_alias_collapses_to_one_id(con):
    """'Navdeep Saini' and 'NA Saini' are the same person -> one player_id, one row."""
    rows = con.execute("""
        SELECT player_id FROM players
        WHERE display_name = 'Navdeep Saini' OR list_contains(aliases, 'NA Saini')
    """).fetchall()
    assert len({r[0] for r in rows}) == 1
    assert scalar(con, "SELECT count(*) FROM batting_career WHERE display_name = 'Navdeep Saini'") <= 1
