"""Shared fixtures: ensure the database is built, then hand tests a read-only
connection."""

import os

import duckdb
import pytest

DB_PATH = "data/ipl.duckdb"


@pytest.fixture(scope="session")
def con():
    if not os.path.exists(DB_PATH):
        from etl import build_db
        build_db.build()
    connection = duckdb.connect(DB_PATH, read_only=True)
    yield connection
    connection.close()


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]
