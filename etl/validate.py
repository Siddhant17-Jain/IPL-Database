"""Stage 6: data-quality assertions run after every build. These catch
structural breakage and counting-rule regressions before anything ships."""

from __future__ import annotations

import duckdb


class ValidationError(AssertionError):
    pass


def _scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def validate(db_path: str = "data/ipl.duckdb") -> list[str]:
    con = duckdb.connect(db_path, read_only=True)
    checks: list[str] = []

    def check(name, ok, detail=""):
        status = "PASS" if ok else "FAIL"
        line = f"[{status}] {name}" + (f": {detail}" if detail else "")
        checks.append(line)
        if not ok:
            raise ValidationError(line)

    # --- structural ---
    n_matches = _scalar(con, "SELECT count(*) FROM matches")
    check("matches present", n_matches > 1200, f"{n_matches} matches")

    n_deliveries = _scalar(con, "SELECT count(*) FROM deliveries")
    check("deliveries present", n_deliveries > 290000, f"{n_deliveries} deliveries")

    orphan_deliv = _scalar(con, """
        SELECT count(*) FROM deliveries d
        LEFT JOIN matches m USING (match_id) WHERE m.match_id IS NULL
    """)
    check("no orphan deliveries", orphan_deliv == 0, f"{orphan_deliv} orphans")

    orphan_players = _scalar(con, """
        SELECT count(*) FROM deliveries d
        LEFT JOIN players p ON p.player_id = d.batter_id WHERE p.player_id IS NULL
    """)
    check("every batter resolves to a player", orphan_players == 0, f"{orphan_players} unresolved")

    orphan_team = _scalar(con, """
        SELECT count(*) FROM matches m
        LEFT JOIN teams t ON t.franchise_id = m.team1 WHERE t.franchise_id IS NULL
    """)
    check("every team resolves to a franchise", orphan_team == 0, f"{orphan_team} unresolved")

    # --- runs reconciliation: deliveries sum to innings totals ---
    mismatch = _scalar(con, """
        WITH d AS (
            SELECT match_id, innings_no, sum(runs_total) AS r
            FROM deliveries GROUP BY 1, 2
        )
        SELECT count(*) FROM innings i
        JOIN d USING (match_id, innings_no)
        WHERE i.total_runs <> d.r
    """)
    check("innings totals == sum of deliveries", mismatch == 0, f"{mismatch} mismatched innings")

    # --- runs reconciliation: win-by-runs margin matches innings totals ---
    # For a side batting first that wins by runs: 1st-innings total - 2nd-innings total == margin.
    margin_bad = _scalar(con, """
        WITH first AS (SELECT match_id, total_runs FROM innings WHERE innings_no = 1 AND is_super_over = FALSE),
             second AS (SELECT match_id, total_runs FROM innings WHERE innings_no = 2 AND is_super_over = FALSE)
        SELECT count(*) FROM matches m
        JOIN first f USING (match_id) JOIN second s USING (match_id)
        WHERE m.win_by_runs IS NOT NULL
          AND m.method IS NULL                       -- exclude DLS-adjusted results
          AND (f.total_runs - s.total_runs) <> m.win_by_runs
    """)
    check("win-by-runs margins reconcile (non-DLS)", margin_bad == 0, f"{margin_bad} bad margins")

    # --- identity: franchise merge sanity ---
    n_franchises = _scalar(con, "SELECT count(*) FROM teams")
    check("franchise count == 15", n_franchises == 15, f"{n_franchises} franchises")

    delhi = _scalar(con, "SELECT matches FROM team_records WHERE franchise_id = 'dc'")
    check("Delhi (Daredevils+Capitals) merged", delhi and delhi > 200, f"{delhi} Delhi matches")

    con.close()
    return checks


if __name__ == "__main__":
    for line in validate():
        print(line)
