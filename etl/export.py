"""Stage 5: export every table to Parquet (analytical layer for later phases)
and CSV (the downloadable clean-dataset layer)."""

from __future__ import annotations

import os

import duckdb


def export(db_path: str = "data/ipl.duckdb",
           parquet_dir: str = "data/parquet",
           csv_dir: str = "data/csv") -> None:
    os.makedirs(parquet_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)
    con = duckdb.connect(db_path, read_only=True)

    tables = [r[0] for r in con.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'main' ORDER BY table_name
    """).fetchall()]

    for t in tables:
        pq = os.path.join(parquet_dir, f"{t}.parquet")
        csv = os.path.join(csv_dir, f"{t}.csv")
        con.execute(f"COPY (SELECT * FROM {t}) TO '{pq}' (FORMAT PARQUET)")
        con.execute(f"COPY (SELECT * FROM {t}) TO '{csv}' (HEADER, DELIMITER ',')")
    con.close()
    print(f"Exported {len(tables)} tables to {parquet_dir}/ and {csv_dir}/")


if __name__ == "__main__":
    export()
