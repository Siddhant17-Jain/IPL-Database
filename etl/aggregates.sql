-- Stage 4: derived stat tables, built from the fact tables.
-- Standard career/season stats EXCLUDE super-over deliveries (is_super_over = FALSE).
-- Counting rules are applied upstream in ingest.py (balls_faced, bowler_runs,
-- is_bowler_wicket, etc.); here we only sum and group.

------------------------------------------------------------------------------
-- Per-player matches played (from playing XIs)
------------------------------------------------------------------------------
CREATE OR REPLACE TABLE appearances_career AS
SELECT player_id, count(DISTINCT match_id) AS matches_played
FROM appearances GROUP BY player_id;

------------------------------------------------------------------------------
-- BATTING
------------------------------------------------------------------------------
CREATE OR REPLACE TABLE batting_innings AS
WITH bat AS (
    SELECT d.match_id, d.innings_no, d.batter_id AS player_id, d.batting_team AS team,
           m.season, m.season_year,
           sum(d.runs_batter)      AS runs,
           sum(d.balls_faced)      AS balls,
           sum(d.is_four::INT)     AS fours,
           sum(d.is_six::INT)      AS sixes
    FROM deliveries d JOIN matches m USING (match_id)
    WHERE d.is_super_over = FALSE
    GROUP BY 1, 2, 3, 4, 5, 6
),
outs AS (  -- a batter is "out" unless retired hurt / retired not out
    SELECT match_id, innings_no, player_out_id AS player_id
    FROM dismissals
    WHERE is_super_over = FALSE AND player_out_id IS NOT NULL
      AND kind NOT IN ('retired hurt', 'retired not out')
)
SELECT b.*,
       (o.player_id IS NOT NULL) AS is_out
FROM bat b
LEFT JOIN outs o USING (match_id, innings_no, player_id);

CREATE OR REPLACE TABLE batting_career AS
SELECT
    bi.player_id,
    p.display_name,
    COALESCE(ac.matches_played, count(DISTINCT bi.match_id))            AS matches,
    count(*)                                                            AS innings,
    sum(CASE WHEN bi.is_out THEN 0 ELSE 1 END)                         AS not_outs,
    sum(bi.runs)                                                        AS runs,
    sum(bi.balls)                                                       AS balls,
    max(bi.runs)                                                        AS highest_score,
    arg_max(NOT bi.is_out, bi.runs * 2 + (NOT bi.is_out)::INT)         AS highest_not_out,
    round(sum(bi.runs) * 1.0
          / NULLIF(sum(bi.is_out::INT), 0), 2)                         AS average,
    round(sum(bi.runs) * 100.0 / NULLIF(sum(bi.balls), 0), 2)          AS strike_rate,
    sum(bi.fours)                                                       AS fours,
    sum(bi.sixes)                                                       AS sixes,
    sum(CASE WHEN bi.runs >= 50 AND bi.runs < 100 THEN 1 ELSE 0 END)   AS fifties,
    sum(CASE WHEN bi.runs >= 100 THEN 1 ELSE 0 END)                    AS hundreds,
    sum(CASE WHEN bi.runs = 0 AND bi.is_out THEN 1 ELSE 0 END)         AS ducks
FROM batting_innings bi
JOIN players p USING (player_id)
LEFT JOIN appearances_career ac USING (player_id)
GROUP BY bi.player_id, p.display_name, ac.matches_played;

CREATE OR REPLACE TABLE batting_by_season AS
SELECT
    bi.player_id, p.display_name, bi.season, bi.season_year,
    count(*)                                                           AS innings,
    sum(CASE WHEN bi.is_out THEN 0 ELSE 1 END)                        AS not_outs,
    sum(bi.runs)                                                       AS runs,
    sum(bi.balls)                                                      AS balls,
    max(bi.runs)                                                       AS highest_score,
    round(sum(bi.runs) * 1.0 / NULLIF(sum(bi.is_out::INT), 0), 2)     AS average,
    round(sum(bi.runs) * 100.0 / NULLIF(sum(bi.balls), 0), 2)         AS strike_rate,
    sum(bi.fours) AS fours, sum(bi.sixes) AS sixes,
    sum(CASE WHEN bi.runs >= 50 AND bi.runs < 100 THEN 1 ELSE 0 END)  AS fifties,
    sum(CASE WHEN bi.runs >= 100 THEN 1 ELSE 0 END)                   AS hundreds
FROM batting_innings bi JOIN players p USING (player_id)
GROUP BY bi.player_id, p.display_name, bi.season, bi.season_year;

------------------------------------------------------------------------------
-- BOWLING
------------------------------------------------------------------------------
CREATE OR REPLACE TABLE bowling_innings AS
WITH balls AS (
    SELECT d.match_id, d.innings_no, d.bowler_id AS player_id, m.season, m.season_year,
           sum(d.is_legal_ball::INT)                                       AS legal_balls,
           sum(d.bowler_runs)                                              AS runs,
           sum(CASE WHEN d.is_legal_ball AND d.runs_total = 0 THEN 1 ELSE 0 END) AS dots,
           sum(d.extra_wides)                                              AS wides,
           sum(d.extra_noballs)                                            AS noballs
    FROM deliveries d JOIN matches m USING (match_id)
    WHERE d.is_super_over = FALSE
    GROUP BY 1, 2, 3, 4, 5
),
wkts AS (
    SELECT match_id, innings_no, bowler_id AS player_id, count(*) AS wickets
    FROM dismissals
    WHERE is_super_over = FALSE AND bowler_credited
    GROUP BY 1, 2, 3
)
SELECT b.*, COALESCE(w.wickets, 0) AS wickets
FROM balls b LEFT JOIN wkts w USING (match_id, innings_no, player_id);

CREATE OR REPLACE TABLE bowling_career AS
SELECT
    bi.player_id, p.display_name,
    COALESCE(ac.matches_played, count(DISTINCT bi.match_id))           AS matches,
    count(*)                                                           AS innings,
    sum(bi.legal_balls)                                                AS balls,
    sum(bi.runs)                                                       AS runs,
    sum(bi.wickets)                                                    AS wickets,
    sum(bi.dots)                                                       AS dots,
    sum(bi.wides) AS wides, sum(bi.noballs) AS noballs,
    round(sum(bi.runs) * 1.0 / NULLIF(sum(bi.wickets), 0), 2)         AS average,
    round(sum(bi.runs) * 6.0 / NULLIF(sum(bi.legal_balls), 0), 2)     AS economy,
    round(sum(bi.legal_balls) * 1.0 / NULLIF(sum(bi.wickets), 0), 2)  AS strike_rate,
    arg_max(bi.wickets, bi.wickets * 1000 - bi.runs)                  AS best_wickets,
    arg_max(bi.runs,    bi.wickets * 1000 - bi.runs)                  AS best_runs,
    sum(CASE WHEN bi.wickets >= 3 THEN 1 ELSE 0 END)                  AS three_wkt_hauls,
    sum(CASE WHEN bi.wickets >= 4 THEN 1 ELSE 0 END)                  AS four_wkt_hauls,
    sum(CASE WHEN bi.wickets >= 5 THEN 1 ELSE 0 END)                  AS five_wkt_hauls
FROM bowling_innings bi
JOIN players p USING (player_id)
LEFT JOIN appearances_career ac USING (player_id)
GROUP BY bi.player_id, p.display_name, ac.matches_played;

CREATE OR REPLACE TABLE bowling_by_season AS
SELECT
    bi.player_id, p.display_name, bi.season, bi.season_year,
    count(*)                                                          AS innings,
    sum(bi.legal_balls) AS balls, sum(bi.runs) AS runs, sum(bi.wickets) AS wickets,
    round(sum(bi.runs) * 1.0 / NULLIF(sum(bi.wickets), 0), 2)        AS average,
    round(sum(bi.runs) * 6.0 / NULLIF(sum(bi.legal_balls), 0), 2)    AS economy,
    round(sum(bi.legal_balls) * 1.0 / NULLIF(sum(bi.wickets), 0), 2) AS strike_rate,
    arg_max(bi.wickets, bi.wickets * 1000 - bi.runs)                 AS best_wickets,
    arg_max(bi.runs,    bi.wickets * 1000 - bi.runs)                 AS best_runs
FROM bowling_innings bi JOIN players p USING (player_id)
GROUP BY bi.player_id, p.display_name, bi.season, bi.season_year;

------------------------------------------------------------------------------
-- FIELDING
------------------------------------------------------------------------------
CREATE OR REPLACE TABLE fielding_career AS
SELECT
    f.fielder_id AS player_id, p.display_name,
    count(*) FILTER (WHERE f.is_catch)    AS catches,
    count(*) FILTER (WHERE f.is_stumping) AS stumpings,
    count(*) FILTER (WHERE f.is_runout)   AS runouts,
    count(*)                              AS dismissals_involved
FROM fielding_events f
JOIN players p ON p.player_id = f.fielder_id
WHERE f.is_super_over = FALSE
GROUP BY f.fielder_id, p.display_name;

------------------------------------------------------------------------------
-- TEAM RECORDS  (super-over result credited to the eliminator winner)
------------------------------------------------------------------------------
CREATE OR REPLACE TABLE team_records AS
WITH played AS (
    SELECT team1 AS team, match_id, COALESCE(winner, eliminator_winner) AS w, result FROM matches
    UNION ALL
    SELECT team2 AS team, match_id, COALESCE(winner, eliminator_winner) AS w, result FROM matches
)
SELECT
    t.franchise_id, t.franchise_name, t.first_season, t.last_season,
    count(*)                                                          AS matches,
    sum(CASE WHEN pl.w = pl.team THEN 1 ELSE 0 END)                  AS won,
    sum(CASE WHEN pl.w IS NOT NULL AND pl.w <> pl.team THEN 1 ELSE 0 END) AS lost,
    sum(CASE WHEN pl.result = 'no result' THEN 1 ELSE 0 END)         AS no_result,
    sum(CASE WHEN pl.result = 'tie' THEN 1 ELSE 0 END)               AS tied_on_field,
    round(100.0 * sum(CASE WHEN pl.w = pl.team THEN 1 ELSE 0 END)
          / NULLIF(sum(CASE WHEN pl.result = 'no result' THEN 0 ELSE 1 END), 0), 2) AS win_pct
FROM played pl JOIN teams t ON t.franchise_id = pl.team
GROUP BY t.franchise_id, t.franchise_name, t.first_season, t.last_season;

------------------------------------------------------------------------------
-- HEAD TO HEAD  (one row per ordered (team, opponent) pair)
------------------------------------------------------------------------------
CREATE OR REPLACE TABLE head_to_head AS
WITH pairs AS (
    SELECT match_id, team1 AS a, team2 AS b, COALESCE(winner, eliminator_winner) AS w, result FROM matches
    UNION ALL
    SELECT match_id, team2 AS a, team1 AS b, COALESCE(winner, eliminator_winner) AS w, result FROM matches
)
SELECT
    ta.franchise_name AS team, tb.franchise_name AS opponent,
    pairs.a AS team_id, pairs.b AS opponent_id,
    count(*)                                                AS matches,
    sum(CASE WHEN w = a THEN 1 ELSE 0 END)                 AS won,
    sum(CASE WHEN w = b THEN 1 ELSE 0 END)                 AS lost,
    sum(CASE WHEN result = 'no result' THEN 1 ELSE 0 END)  AS no_result
FROM pairs
JOIN teams ta ON ta.franchise_id = pairs.a
JOIN teams tb ON tb.franchise_id = pairs.b
GROUP BY ta.franchise_name, tb.franchise_name, pairs.a, pairs.b;

------------------------------------------------------------------------------
-- VENUE STATS
------------------------------------------------------------------------------
CREATE OR REPLACE TABLE venue_stats AS
SELECT
    v.venue_id, v.venue_name, v.city,
    (SELECT count(*) FROM matches m WHERE m.venue_id = v.venue_id)     AS matches,
    round(avg(CASE WHEN i.innings_no = 1 THEN i.total_runs END), 1)    AS avg_first_innings,
    max(i.total_runs)                                                  AS highest_total
FROM venues v
JOIN matches m ON m.venue_id = v.venue_id
JOIN innings i ON i.match_id = m.match_id AND i.is_super_over = FALSE
GROUP BY v.venue_id, v.venue_name, v.city;

------------------------------------------------------------------------------
-- LEADERBOARDS / RECORDS  (top 100 each)
------------------------------------------------------------------------------
CREATE OR REPLACE TABLE lb_most_runs AS
SELECT display_name, matches, innings, runs, average, strike_rate, hundreds, fifties
FROM batting_career ORDER BY runs DESC LIMIT 100;

CREATE OR REPLACE TABLE lb_most_wickets AS
SELECT display_name, matches, innings, wickets, average, economy,
       best_wickets || '/' || best_runs AS best_figures
FROM bowling_career ORDER BY wickets DESC LIMIT 100;

CREATE OR REPLACE TABLE lb_highest_scores AS
SELECT p.display_name,
       bi.runs || (CASE WHEN bi.is_out THEN '' ELSE '*' END) AS score,
       bi.balls, bi.fours, bi.sixes, m.season, m.date
FROM batting_innings bi
JOIN players p USING (player_id)
JOIN matches m USING (match_id)
ORDER BY bi.runs DESC, bi.balls ASC LIMIT 100;

CREATE OR REPLACE TABLE lb_best_bowling AS
SELECT p.display_name,
       bi.wickets || '/' || bi.runs AS figures,
       bi.legal_balls AS balls, m.season, m.date
FROM bowling_innings bi
JOIN players p USING (player_id)
JOIN matches m USING (match_id)
WHERE bi.wickets > 0
ORDER BY bi.wickets DESC, bi.runs ASC LIMIT 100;

CREATE OR REPLACE TABLE lb_highest_totals AS
SELECT t.franchise_name AS team, i.total_runs, i.wickets, i.legal_balls AS balls,
       opp.franchise_name AS opponent, m.season, m.date
FROM innings i
JOIN matches m USING (match_id)
JOIN teams t ON t.franchise_id = i.batting_team
JOIN teams opp ON opp.franchise_id = i.bowling_team
WHERE i.is_super_over = FALSE
ORDER BY i.total_runs DESC LIMIT 100;
