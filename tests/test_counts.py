"""Structural integrity and runs reconciliation: the checks that catch a
broken build or a counting-rule regression."""

from tests.conftest import scalar


def test_match_and_delivery_counts(con):
    assert scalar(con, "SELECT count(*) FROM matches") == 1243
    assert scalar(con, "SELECT count(*) FROM deliveries") == 295732


def test_no_orphan_deliveries(con):
    assert scalar(con, """
        SELECT count(*) FROM deliveries d
        LEFT JOIN matches m USING (match_id) WHERE m.match_id IS NULL
    """) == 0


def test_every_player_reference_resolves(con):
    for col in ("batter_id", "bowler_id", "non_striker_id"):
        unresolved = scalar(con, f"""
            SELECT count(*) FROM deliveries d
            LEFT JOIN players p ON p.player_id = d.{col}
            WHERE p.player_id IS NULL
        """)
        assert unresolved == 0, f"{col} has {unresolved} unresolved references"


def test_innings_totals_reconcile(con):
    """Sum of per-delivery runs must equal each innings total."""
    assert scalar(con, """
        WITH d AS (SELECT match_id, innings_no, sum(runs_total) r FROM deliveries GROUP BY 1, 2)
        SELECT count(*) FROM innings i JOIN d USING (match_id, innings_no)
        WHERE i.total_runs <> d.r
    """) == 0


def test_win_by_runs_margins_reconcile(con):
    """For non-DLS results, 1st-innings total minus 2nd-innings total equals the margin."""
    assert scalar(con, """
        WITH f AS (SELECT match_id, total_runs FROM innings WHERE innings_no = 1 AND is_super_over = FALSE),
             s AS (SELECT match_id, total_runs FROM innings WHERE innings_no = 2 AND is_super_over = FALSE)
        SELECT count(*) FROM matches m JOIN f USING (match_id) JOIN s USING (match_id)
        WHERE m.win_by_runs IS NOT NULL AND m.method IS NULL
          AND (f.total_runs - s.total_runs) <> m.win_by_runs
    """) == 0


def test_super_overs_excluded_from_standard_stats(con):
    """Super-over deliveries exist in the fact table but never feed career stats."""
    assert scalar(con, "SELECT count(*) FROM deliveries WHERE is_super_over") > 0
    # batting_innings is built only from non-super-over deliveries.
    assert scalar(con, """
        SELECT count(*) FROM batting_innings bi
        JOIN deliveries d ON d.match_id = bi.match_id AND d.innings_no = bi.innings_no
        WHERE d.is_super_over
    """) == 0


def test_no_negative_aggregates(con):
    for table, col in [("batting_career", "runs"), ("bowling_career", "wickets"),
                       ("fielding_career", "catches")]:
        assert scalar(con, f"SELECT count(*) FROM {table} WHERE {col} < 0") == 0
