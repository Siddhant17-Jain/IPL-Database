# IPL Database

A comprehensive, well-modeled database for the Indian Premier League, built to make IPL stats
accessible to anyone, the way Sports-Reference does for other sports. The data the world needs
exists but is scattered and poorly structured; this project turns the raw ball-by-ball record into
a clean, queryable, downloadable database.

This repository currently contains **Phase 1: the data core**. The browsable website (Phase 2) and
the filterable query-tool backend (Phase 3) build on top of it.

## What's here

`ipl_json/` holds the [Cricsheet](https://cricsheet.org) ball-by-ball JSON: **1,243 matches,
2008–2026, ~295,700 deliveries**. The ETL in `etl/` turns that into a normalized
[DuckDB](https://duckdb.org) database plus per-table Parquet and CSV exports.

## Build it

```bash
pip install -r requirements.txt
python -m etl.run        # parse -> build -> validate -> export  (~5s)
```

This wipes and rebuilds `data/ipl.duckdb` from `ipl_json/`, so the database is always reproducible
from source. Outputs:

- `data/ipl.duckdb`: canonical store (all tables below)
- `data/parquet/<table>.parquet`: analytical layer (also what the in-browser query tool will use)
- `data/csv/<table>.csv`: the downloadable clean datasets

## Pipeline (`etl/`)

| Stage | File | Job |
|------|------|-----|
| 1–2 | `ingest.py` | Parse JSON, flatten to rows, resolve team/venue/player identity, apply cricket counting rules at the delivery grain |
|     | `config/franchises.py`, `config/venues.py` | Identity policy: franchise merges and venue canonicalization |
| 3–4 | `build_db.py` + `aggregates.sql` | Load DuckDB; build derived stat tables |
| 5   | `export.py` | Write Parquet + CSV |
| 6   | `validate.py` | Data-quality assertions (run on every build) |
|     | `run.py` | Single entrypoint for all of the above |

## Tables

**Dimensions:** `players` (keyed on the Cricsheet registry id, with aliases), `teams`, `venues`,
`seasons`, `matches`.
**Facts:** `innings`, `deliveries` (~295k rows), `dismissals`, `fielding_events`, `appearances`.
**Derived:** `batting_career`/`batting_by_season`, `bowling_career`/`bowling_by_season`,
`fielding_career`, `team_records`, `head_to_head`, `venue_stats`, and `lb_*` leaderboards.

## Identity decisions

- **Franchises:** clear rebrands are merged into one continuous franchise (Delhi Daredevils = Delhi
  Capitals, Kings XI Punjab = Punjab Kings, RCB Bangalore = Bengaluru, Rising Pune Supergiant(s)).
  **Deccan Chargers and Sunrisers Hyderabad are kept separate.** The name a team used in a given
  season is preserved on each match.
- **Players:** the Cricsheet registry id is the identity key, so alternate spellings (e.g. "Navdeep
  Saini" / "NA Saini") collapse to one player.
- **Venues:** formatting variants and renamed grounds (e.g. Feroz Shah Kotla → Arun Jaitley Stadium)
  map to one physical venue.

## Counting rules

Applied in `ingest.py` so aggregation is auditable:

- **Legal ball** = not a wide and not a no-ball; overs / economy / strike-rate use legal balls.
- **Balls faced** = every delivery except wides.
- **Bowler's runs** = batter runs + wides + no-balls (byes / leg-byes / penalty excluded).
- **Bowler's wicket** = caught, bowled, lbw, stumped, caught-and-bowled, hit wicket (run out and
  retirements are not credited).
- **Super-over deliveries** are stored but excluded from standard career/season stats.

## Tests

```bash
python -m pytest
```

Structural integrity, runs reconciliation, and spot-checks against known records (Gayle's 175*,
Joseph's 6/12, SRH's 287, the franchise merges).
