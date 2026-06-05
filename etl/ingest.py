"""Stage 1 + 2: read Cricsheet match JSON and flatten into normalized records,
resolving team / venue / player identity as we go.

The output is a set of plain Python row-lists (one dict per row) that
``build_db`` loads into DuckDB:

  matches, innings, deliveries, dismissals, fielding_events, players, teams, venues, seasons

All the subtle cricket counting rules live here, at the delivery grain, so that
the downstream SQL aggregation is a straightforward sum/group-by and can be
audited against these definitions:

  * legal ball      = not a wide and not a no-ball
  * balls faced     = deliveries not a wide (a no-ball is faced by the batter)
  * bowler runs     = batter runs + wides + no-balls (byes/legbyes/penalty excluded)
  * bowler's wicket = caught, bowled, lbw, stumped, caught and bowled, hit wicket
"""

from __future__ import annotations

import glob
import json
import os
from collections import Counter, defaultdict

from .config.franchises import franchise_id
from .config.venues import resolve_venue

# Dismissal kinds credited to the bowler.
BOWLER_WICKET_KINDS = {
    "caught", "bowled", "lbw", "stumped", "caught and bowled", "hit wicket",
}
# Dismissal kinds that consume a ball-faced / count against the batting side but
# are NOT the bowler's wicket.
NON_BOWLER_KINDS = {
    "run out", "retired hurt", "retired out", "obstructing the field",
    "retired not out", "handled the ball", "timed out",
}


def _match_id_from_path(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _season_year(season) -> int:
    """Cricsheet seasons are '2009' or '2007/08'. Return the calendar year the
    tournament is known by (the later year for split seasons)."""
    s = str(season)
    if "/" in s:
        start, end = s.split("/")
        return int(start[:2] + end) if len(end) == 2 else int(end)
    return int(s)


class PlayerRegistry:
    """Resolves player names to stable Cricsheet registry ids.

    Ids are global across the dataset; names are resolved within each match's own
    registry (the ground truth for that match), and we track every spelling seen
    for each id so we can pick a canonical display name and list aliases.
    """

    def __init__(self):
        # player_id -> Counter of name spellings (weighted by appearances)
        self._names: dict[str, Counter] = defaultdict(Counter)
        # player_id -> latest date seen (for display-name tie-breaks)
        self._last_seen: dict[str, str] = {}

    def resolve(self, name: str, match_registry: dict[str, str], date: str) -> str:
        pid = match_registry.get(name)
        if pid is None:
            # Should not happen with Cricsheet data, but never crash a build over
            # one stray name; fall back to a stable synthetic id.
            pid = "x_" + name.replace(" ", "_").replace(".", "")
        self._names[pid][name] += 1
        if date >= self._last_seen.get(pid, ""):
            self._last_seen[pid] = date
        return pid

    def note(self, name: str, match_registry: dict[str, str], date: str) -> None:
        self.resolve(name, match_registry, date)

    def players_table(self) -> list[dict]:
        rows = []
        for pid, names in self._names.items():
            # display name = most frequent spelling, tie-break by longest.
            display = sorted(names.items(), key=lambda kv: (-kv[1], -len(kv[0])))[0][0]
            aliases = sorted(n for n in names if n != display)
            rows.append({
                "player_id": pid,
                "display_name": display,
                "aliases": aliases,
                "last_seen": self._last_seen.get(pid, ""),
            })
        return rows


def load_all(json_dir: str = "ipl_json") -> dict:
    """Parse every match file and return all normalized row-lists."""
    files = sorted(glob.glob(os.path.join(json_dir, "*.json")))
    if not files:
        raise FileNotFoundError(f"No match JSON found in {json_dir!r}")

    registry = PlayerRegistry()
    matches, innings_rows, deliveries, dismissals, fielding = [], [], [], [], []
    appearances = []
    season_counts: Counter = Counter()
    venues_seen: dict[str, dict] = {}

    for path in files:
        with open(path) as fh:
            data = json.load(fh)
        info = data["info"]
        match_id = _match_id_from_path(path)
        people = info.get("registry", {}).get("people", {})
        date = info.get("dates", ["0000-00-00"])[0]
        season = str(info.get("season"))
        season_counts[season] += 1

        teams = info["teams"]
        team_ids = {t: franchise_id(t) for t in teams}
        venue_id, venue_name, venue_city = resolve_venue(info["venue"])
        venues_seen[venue_id] = {"venue_id": venue_id, "venue_name": venue_name, "city": venue_city}

        def rid(name):  # resolve player id within this match
            return registry.resolve(name, people, date)

        # Playing XIs -> appearances (drives "matches played").
        for team_name, squad in info.get("players", {}).items():
            for pname in squad:
                appearances.append({
                    "match_id": match_id,
                    "player_id": rid(pname),
                    "team": team_ids[team_name],
                    "season": season,
                    "season_year": _season_year(season),
                })

        outcome = info.get("outcome", {})
        by = outcome.get("by", {})
        pom = info.get("player_of_match")
        event = info.get("event", {}) or {}
        toss = info.get("toss", {}) or {}

        matches.append({
            "match_id": match_id,
            "season": season,
            "season_year": _season_year(season),
            "date": date,
            "venue_id": venue_id,
            "city": venue_city,
            "team1": team_ids[teams[0]],
            "team2": team_ids[teams[1]],
            "team1_name": teams[0],
            "team2_name": teams[1],
            "toss_winner": team_ids.get(toss.get("winner")) if toss.get("winner") else None,
            "toss_decision": toss.get("decision"),
            "winner": team_ids.get(outcome.get("winner")) if outcome.get("winner") else None,
            "winner_name": outcome.get("winner"),
            "result": outcome.get("result"),  # 'tie' | 'no result' | None (=normal)
            "method": outcome.get("method"),  # 'D/L' on rain-affected results
            "is_eliminator": "eliminator" in outcome,
            "eliminator_winner": team_ids.get(outcome.get("eliminator")) if outcome.get("eliminator") else None,
            "win_by_runs": by.get("runs"),
            "win_by_wickets": by.get("wickets"),
            "player_of_match": rid(pom[0]) if pom else None,
            "event_name": event.get("name"),
            "match_number": event.get("match_number"),
            "stage": event.get("stage"),
            "gender": info.get("gender"),
        })

        for inn_no, inn in enumerate(data["innings"], start=1):
            bat_team = inn["team"]
            bowl_team = teams[1] if bat_team == teams[0] else teams[0]
            is_super = "super_over" in inn
            target = inn.get("target", {}) or {}
            pps = inn.get("powerplays", []) or []
            mandatory_pp = next((p for p in pps if p.get("type") == "mandatory"), pps[0] if pps else {})

            inn_runs = inn_legal = inn_wkts = 0
            delivery_seq = 0
            for over in inn.get("overs", []):
                over_no = over["over"]
                for ball_in_over, dl in enumerate(over["deliveries"], start=1):
                    delivery_seq += 1
                    extras = dl.get("extras", {}) or {}
                    e_wide = extras.get("wides", 0)
                    e_noball = extras.get("noballs", 0)
                    e_bye = extras.get("byes", 0)
                    e_legbye = extras.get("legbyes", 0)
                    e_penalty = extras.get("penalty", 0)
                    runs = dl["runs"]
                    runs_batter = runs["batter"]
                    runs_total = runs["total"]
                    is_wide = e_wide > 0
                    is_noball = e_noball > 0
                    is_legal = not is_wide and not is_noball
                    bowler_runs = runs_batter + e_wide + e_noball  # conceded to bowler

                    batter_id = rid(dl["batter"])
                    bowler_id = rid(dl["bowler"])
                    nonstriker_id = rid(dl["non_striker"])

                    inn_runs += runs_total
                    if is_legal:
                        inn_legal += 1

                    wkts = dl.get("wickets", []) or []
                    first_kind = wkts[0]["kind"] if wkts else None
                    deliveries.append({
                        "match_id": match_id,
                        "innings_no": inn_no,
                        "is_super_over": is_super,
                        "batting_team": team_ids[bat_team],
                        "bowling_team": team_ids[bowl_team],
                        "delivery_seq": delivery_seq,
                        "over": over_no,
                        "ball_in_over": ball_in_over,
                        "batter_id": batter_id,
                        "bowler_id": bowler_id,
                        "non_striker_id": nonstriker_id,
                        "runs_batter": runs_batter,
                        "runs_extras": runs["extras"],
                        "runs_total": runs_total,
                        "extra_wides": e_wide,
                        "extra_noballs": e_noball,
                        "extra_byes": e_bye,
                        "extra_legbyes": e_legbye,
                        "extra_penalty": e_penalty,
                        "is_wide": is_wide,
                        "is_noball": is_noball,
                        "is_legal_ball": is_legal,
                        "balls_faced": 0 if is_wide else 1,   # batter faces everything but wides
                        "bowler_runs": bowler_runs,
                        "is_four": runs_batter == 4,
                        "is_six": runs_batter == 6,
                        "is_wicket": bool(wkts),
                        "wicket_kind": first_kind,
                        "is_bowler_wicket": bool(wkts) and first_kind in BOWLER_WICKET_KINDS,
                    })

                    for w in wkts:
                        kind = w["kind"]
                        bowler_credited = kind in BOWLER_WICKET_KINDS
                        inn_wkts += 1
                        out_id = rid(w["player_out"]) if w.get("player_out") else None
                        dismissals.append({
                            "match_id": match_id,
                            "innings_no": inn_no,
                            "is_super_over": is_super,
                            "over": over_no,
                            "delivery_seq": delivery_seq,
                            "player_out_id": out_id,
                            "kind": kind,
                            "bowler_id": bowler_id if bowler_credited else None,
                            "bowler_credited": bowler_credited,
                            "batting_team": team_ids[bat_team],
                            "bowling_team": team_ids[bowl_team],
                        })
                        for fl in w.get("fielders", []) or []:
                            fname = fl.get("name")
                            if not fname:
                                continue  # substitute fielder with no named player
                            fielding.append({
                                "match_id": match_id,
                                "innings_no": inn_no,
                                "is_super_over": is_super,
                                "fielder_id": rid(fname),
                                "fielding_team": team_ids[bowl_team],
                                "kind": kind,
                                "is_catch": kind in ("caught", "caught and bowled"),
                                "is_stumping": kind == "stumped",
                                "is_runout": kind == "run out",
                            })

            innings_rows.append({
                "match_id": match_id,
                "innings_no": inn_no,
                "is_super_over": is_super,
                "batting_team": team_ids[bat_team],
                "bowling_team": team_ids[bowl_team],
                "batting_team_name": bat_team,
                "total_runs": inn_runs,
                "wickets": inn_wkts,
                "legal_balls": inn_legal,
                "target_runs": target.get("runs"),
                "target_overs": target.get("overs"),
                "powerplay_from": mandatory_pp.get("from"),
                "powerplay_to": mandatory_pp.get("to"),
            })

    teams_rows = []
    from .config.franchises import FRANCHISES
    for fid, (canonical, variants) in FRANCHISES.items():
        teams_rows.append({
            "franchise_id": fid,
            "franchise_name": canonical,
            "name_variants": variants,
        })

    seasons_rows = [
        {"season": s, "season_year": _season_year(s), "num_matches": n}
        for s, n in sorted(season_counts.items(), key=lambda kv: _season_year(kv[0]))
    ]

    return {
        "matches": matches,
        "innings": innings_rows,
        "deliveries": deliveries,
        "dismissals": dismissals,
        "fielding_events": fielding,
        "appearances": appearances,
        "players": registry.players_table(),
        "teams": teams_rows,
        "venues": sorted(venues_seen.values(), key=lambda v: v["venue_id"]),
        "seasons": seasons_rows,
    }
