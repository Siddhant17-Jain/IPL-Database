"""Stage 3 + 4: load the normalized records into DuckDB and build the derived
stat tables from ``aggregates.sql``."""

from __future__ import annotations

import os

import duckdb
import pandas as pd

from . import ingest

HERE = os.path.dirname(__file__)
AGG_SQL = os.path.join(HERE, "aggregates.sql")


def _load_table(con: duckdb.DuckDBPyConnection, name: str, rows: list[dict]) -> None:
    """Create a DuckDB table from a list-of-dicts. Empty lists still create a
    table with the right columns by relying on at least one row existing."""
    df = pd.DataFrame(rows)
    con.register("_staging_df", df)
    con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM _staging_df")
    con.unregister("_staging_df")


def build(json_dir: str = "ipl_json", db_path: str = "data/ipl.duckdb") -> str:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)  # idempotent: always rebuild from source

    print(f"Parsing match JSON from {json_dir}/ ...")
    tables = ingest.load_all(json_dir)
    for name, rows in tables.items():
        print(f"  {name:16s} {len(rows):>8,} rows")

    con = duckdb.connect(db_path)
    for name in ("seasons", "teams", "venues", "players",
                 "matches", "innings", "deliveries", "dismissals", "fielding_events",
                 "appearances"):
        _load_table(con, name, tables[name])

    # Enrich dimension tables with facts derived from matches.
    con.execute("""
        CREATE OR REPLACE TABLE teams AS
        SELECT t.*,
               fs.first_season, fs.last_season
        FROM teams t
        LEFT JOIN (
            SELECT fid AS franchise_id,
                   min(season_year) AS first_season,
                   max(season_year) AS last_season
            FROM (
                SELECT team1 AS fid, season_year FROM matches
                UNION ALL
                SELECT team2 AS fid, season_year FROM matches
            ) GROUP BY fid
        ) fs USING (franchise_id)
    """)

    print("Building derived stat tables ...")
    with open(AGG_SQL) as fh:
        con.execute(fh.read())

    con.close()
    print(f"Built {db_path}")
    return db_path


if __name__ == "__main__":
    build()
