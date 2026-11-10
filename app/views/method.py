"""
method.py - every data source, what is covered, how each number is counted, and the corrections. READ-ONLY.
Owner's decision 2026-11-09: this page is the only place that lists the sources (no per-page credit lines).
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Method", "Where the data comes from, what it covers, and how every number is counted.")

c.section("About T20 Crease")
st.markdown("""
T20 Crease is an independent analytics project on Pakistan's domestic T20 cricket. It is not affiliated with, endorsed
by or connected to any cricket board, tournament, team or sponsor. Competition and team names are used only to say
which matches the numbers come from.
""")
info = c.export_info()
ed = c.editions().sort_values("order")
r = c.results()
p = c.players()
n_m, n_e, n_bbb = int(info["matches"]), int(info["editions"]), int(info["matches_with_bbb"])

c.section("What is covered", f"{n_m:,} matches in {n_e} editions of Pakistan's domestic T20 cups, "
                             f"{ed.season.iloc[0]} to {ed.season.iloc[-1]}.")
st.markdown("""
- Men's domestic T20 cups only: the ABN-AMRO and RBS Twenty-20 Cup, Faysal Bank T20 Cup, Super Eight T20 Cup, T20 Cup for
  Departments, Ramadan T20 Cup, Haier T20 Cup, Taqreebat-e-Azadi T20, National T20 Cup (and its Qualifiers) and the
  Champions T20 Cup. Sponsors' names are left out of the competition names.
- The Pakistan Super League and matches against touring sides are not included.
- Some scheduled matches are in no source (most likely abandoned without a ball); each edition's note says which.
""")
c.table(pd.DataFrame({"Edition": ed.edition_name, "Matches": ed.matches, "Teams": ed.teams,
                      "Note": ed.notes.fillna("")}),
        {"Matches": c.col_int(), "Teams": c.col_int(), "Note": c.col_text(width="large")})

c.section("How numbers are counted")
st.markdown(f"""
- **Runs, balls, fours and sixes**: as on the batting scorecard. Balls faced do not include wides.
- **Innings** (batting): innings in which he batted; did-not-bat is not an innings, but the match counts.
- **Average**: runs per dismissal. Retired hurt is not a dismissal.
- **Strike rate**: runs per 100 balls faced.
- **Wickets**: as on the bowling scorecard (bowled, caught, lbw, stumped, hit wicket; not run outs).
- **Runs conceded and economy**: as the scorecard credits them to the bowler, per over. Byes and leg byes are not
  the bowler's.
- **Best bowling**: most wickets in one innings, then fewest runs.
- **Leaderboards**: highest scores and best bowling list each player once, at his best in the chosen span.
- **Champion**: the winner of the edition's final. An edition without a final (Taqreebat-e-Azadi T20 2014) has no
  champion.
- **Wins and losses**: every match of the edition, all stages together. It is not the official points table (no
  points, net run rate or groups). A tie counts as a tie.
""")

c.section("Small samples")
st.markdown(f"""
- Averages, strike rates and economy are left blank ("-", "not enough innings") under {c.MIN_INNS} innings.
- Under {c.SMALL_INNS} innings a row is marked **Small**: read its rates with care.
- Leaderboards of rates need a minimum: one season, 100 balls faced or 20 overs bowled; more than one season,
  300 balls faced or 50 overs bowled; and {c.MIN_INNS} innings. Bowling average also needs 5 wickets in one season,
  10 in more.
- A page says so when the chosen competition and season have few matches.
""")

ex_by = p[p.label_kind == "birth year and seasons"].name.sort_values().iloc[0]
ex_s = p[p.label_kind == "seasons"].name.sort_values().iloc[0]
c.section("Players and names")
st.markdown(f"""
- Every player is kept apart by his player ID, never by name.
- Shown name: his PSL name for a player who also played the PSL, else his profile name. One owner correction:
  ID 1248374 is shown as Aamer Azmat.
- When two or more players share a name, the label adds the birth year and the seasons he played ("{ex_by}"),
  or only the seasons when the birth year is unknown ("{ex_s}"); if two labels were still the same, the player ID
  would be added. Never a team name. {int((p.label_kind != "").sum())} players share {p[p.label_kind != ""].base_name.nunique()} names.
- No two player IDs have been merged: a merge needs evidence, and the possible cases are still being checked.
- In charts, cards and running text a player is shown by his plain name. Only when two different players with the
  same name appear in the same chart or list does each get a short suffix, "(b. 1998)" (or "(from 2013)" when the
  birth year is not known). The full detail (birth year, seasons and teams) is in the hover and in the tables, and
  the pickers keep the full label. Chart labels are never cut short.
- Bowling style: our own style categories (Right-arm Pace, Left-arm Pace, Right-arm Off-spin, Left-arm Orthodox, Right-arm
  Leg-spin, Left-arm Wrist-spin). Where no source gives a clear style it is shown as Unknown.
""")

c.section("Teams and grounds")
st.markdown("""
- Teams are shown as they were named that season. Only spellings of the same team are joined (Sind and Sindh,
  Baluchistan and Balochistan), and the source's country tags are dropped ("Northern (Pakistan)" is shown as
  Northern). Teams of different eras, such as Rawalpindi and Rawalpindi Region, are kept apart.
- One ground with two names (Arbab Niaz Stadium and Imran Khan Cricket Stadium, Peshawar) is shown by its later name.
""")

c.section("Corrections")
ties = r[r.tied == 1].sort_values("date")
st.markdown(f"The source gives no winner for {len(ties)} tied matches; the winner of the one-over eliminator or "
            "Super Over, named in the match result, is used. Every correction is logged with its evidence.")
c.table(pd.DataFrame({"Date": ties.date.map(c.date_fmt), "Edition": ties.edition_name,
                      "Match": ties.team_1 + " v " + ties.team_2, "Result": ties.result}),
        {"Result": c.col_text(width="large")})

inn = c.innings_table()
cov = c.coverage(tuple(int(x) for x in ed.edition_id))
fc = c.field_coverage().groupby("edition_id")[["run_outs", "run_outs_known", "catches", "catches_known"]].sum()
fc["ro_pct"] = 100 * fc.run_outs_known / fc.run_outs.where(fc.run_outs > 0)
poor_ro = [n for e_, n in zip(ed.edition_id, ed.edition_name) if e_ in fc.index and fc.ro_pct.get(e_, 100) < c.FIELD_MIN_COVER]
en = c.bat_entry()
n_inn, n_ok = len(inn), int(inn.fow_complete.sum())

c.section("Teams and venues")
st.markdown(f"""
- **Teams** are kept by team ID: one team's spellings are joined, eras are not. Results by edition, head to head and toss
  count every match of the chosen competition and season. **Win %** is wins of matches won or lost (ties and no
  results left out) and is blank under {c.MIN_INNS} such matches. **Finish** is the last stage the team reached.
- **Extras** are the innings' extras as the scorecard lists them, per innings bowled: wides and no-balls are the runs
  given for them, not the number of deliveries (the bowlers' own wide and no-ball counts are often missing).
- **Venues**: {len(c.ground_names())} grounds. **Par** is the average first-innings score of first innings that lasted
  20 overs or were all out, in matches without a rain rule; blank under {c.MIN_INNS} such innings, Small under
  {c.SMALL_INNS}. **Chasing won %** and **Toss winner won %** count matches won or lost. **Under lights** is day-night or
  night; the source does not say for {int(r.light.isna().sum())} matches.
""")

c.section("Partnerships and collapses")
st.markdown(f"""
- The score at each fall of wicket comes from the dismissed batter's own fall-of-wicket entry; where that is missing,
  from the score when the next batter came in (the batter at position k comes in at wicket k - 2); for the last
  wicket of an all-out innings, the total. Retirements listed in the fall-of-wickets line are not wickets.
- An innings is used only when every wicket has a score: {n_ok:,} of {n_inn:,} innings. The build's checks compare
  every wicket with the ball-by-ball record where both exist and agree, and make sure the stands add up to each total.
- The **nth-wicket stand** runs from wicket n-1 to wicket n (team runs, extras included); the last stand is unbroken
  unless ten wickets fell. **Average** is runs per stand that ended, blank under {c.MIN_INNS} stands. The scorecards
  have no balls for a stand, so there is no partnership run rate.
- A **collapse** is {c.COLLAPSE_WKTS} wickets for {c.COLLAPSE_RUNS} runs or fewer, counted from the score at the
  wicket before the first of them. The collapse index is the share of innings with at least one.
""")

c.section("Batting position, entry and dismissals")
st.markdown(f"""
- **Position** is the batting order on the scorecard. The **score when he came in** is the team score at the wicket
  that brought him in (openers: 0 for 0). It is known for {int(en.entry_known.sum()):,} of {int(en.innings.sum()):,}
  innings; the **over** for {int(en.overs_known.sum()):,}, because older scorecards often give the score but not the
  over. A batter who came in after a team-mate retired hurt is left as not known.
- **How he gets out** compares his dismissals by type with every dismissal of every player in the editions he batted
  in. Caught and bowled is counted apart from caught. Retired hurt is not a dismissal.
""")

c.section("Fielding")
st.markdown(f"""
- A catch, run out or stumping is credited to the fielder the scorecard names: by the source's player ID where it gives
  one; else by his name, matched only within the fielding side's eleven and only when exactly one of them has that
  name; else by a spelling the source used for one player ID elsewhere, when that player is in the eleven. Caught and
  bowled goes to the bowler. A substitute is credited only when the source gives his ID. Anything else counts for
  nobody. Tested by hiding the source's IDs: the name rule gave the same fielder every time.
- Keeper catches (the keeper's mark on the scorecard), catches in the field, caught and bowled and substitute catches
  are counted apart. Every fielder named in a run out is credited.
- Fielder known for {cov['ct'][2]:.1f}% of catches, {cov['st'][2]:.1f}% of stumpings and {cov['ro'][2]:.1f}% of run outs
  in all seasons. The source often names nobody for a run out, mostly in {", ".join(poor_ro[:4])}
  {"and " + str(len(poor_ro) - 4) + " other editions" if len(poor_ro) > 4 else ""}.
- **Rule**: a fielding number or leaderboard is shown only where the fielder is known for at least
  {c.FIELD_MIN_COVER:.0f}% of those dismissals in the chosen scope (for a player, in his matches); otherwise it is left
  out and the page says why. Every fielding view states its coverage. The method was also checked against a second,
  independent scorecard source for the PSL matches of the same players: catches, stumpings and run outs agreed
  wherever both named the fielder.
""")

c.section("Compare")
st.markdown(f"""
- Two players side by side in the chosen competition and season, with the same rules as the Player page (rates blank
  under {c.MIN_INNS} innings, Small under {c.SMALL_INNS}). By competition and by season list runs, innings and wickets
  in the order the seasons were played.
""")

c.section("Search")
st.markdown("""
- The search box at the top of every page finds players (each player of a shared name has his own entry, with his
  birth year and seasons), teams and grounds. A player opens on Players, a team on Teams, a ground on Venues. If the
  pick played no match in the competition and season chosen at the top, the page widens to all competitions and all
  seasons and says so.
""")

c.section("Season recap")
st.markdown(f"""
- Competitions, Season recap: one season of the competition picked at the top (all competitions when none is), the
  season picked on the tab. Matches, runs (team runs, extras included), run rate (team runs per 6 legal balls, both
  innings), sixes (and per 20 overs), hundreds and fifties, each edition's champion and runner-up, and the season's
  leaders and records with the same rules as Leaderboards and Records (strike rate and economy need the one-season
  minimum). The change on the season before compares the same competition choice. A season with fewer than
  {c.SMALL_INNS} matches is marked Small.
""")

c.section("Young talent")
st.markdown(f"""
- Leaderboards, Young talent: runs or wickets by players under 23, in the chosen span. Only the birth year is kept, so a
  player's age in a season is the season's first year minus his birth year (2012/13 counts as 2012). This is
  approximate and can be one year out either way. Only the seasons in which he was {c.YOUNG_MAX} or younger count.
- Players without a known birth year ({int(p.birth_year.isna().sum())} of {len(p):,}) are left out; each board says
  how many in its span. Rates are blank under {c.MIN_INNS} innings and marked Small under {c.SMALL_INNS}.
""")

c.section("Head to head")
st.markdown(f"""
- Teams & Venues, Head to head: every side against every other in the chosen competition and season. Each cell is the
  row team's wins and losses against the column team; the colour is its win % of matches won or lost (ties and no
  results left out). Grey: fewer than {c.MIN_INNS} matches won or lost, so no win % is given; an amber dashed border:
  a Small sample (under {c.SMALL_INNS}). Sides are kept by team, so an older and a newer side of one city are
  separate rows. The most-played sides come first (top 8, top 12 or all).
""")

bcv = c.bbb_coverage()
bsh, bhd = bcv[bcv.shown == 1].sort_values("order"), bcv[bcv.shown == 0].sort_values("order")
c.section("Insights (ball by ball)")
st.markdown(f"""
- A ball-by-ball record exists for {int(bcv.matches_bbb.sum())} of {n_m:,} matches. It is used only for innings whose
  runs, wickets and legal balls equal the scorecard, and for a player only in innings where his own figures equal his
  scorecard figures. An edition is shown only with at least {c.BBB_MIN_MATCHES} such matches:
  {len(bsh)} editions, {int(bsh.matches.sum())} matches. Left out: {", ".join(bhd.edition_name)}.
- **Phases**: powerplay overs 1 to 6, middle 7 to 15, death 16 to 20. **Run rate** is runs (extras included) per 6
  legal balls; **boundary %** is balls faced hit for 4 or 6; **dot ball %** is legal balls with no run of any kind
  (for a batter, balls faced with no run off the bat; for a bowler, legal balls with no run to him).
- **Over by over**: each over's runs and wickets per innings that reached it.
- **Players**: a player's batting and bowling by phase; rates are blank under {c.MIN_BALLS} balls in a phase and
  marked Small under {c.SMALL_BALLS}. **Teams**: each side's run rate and wickets per innings by phase, batting or
  bowling; blank under {c.MIN_INNS} innings.
- Line, length, shot type and where the ball went are not used. Every view states the matches and innings it rests on.
""")

c.section("Records")
st.markdown(f"""
- Each list shows the top {c.REC_N} for the chosen competition and season, plus any row level with the {c.REC_N}th
  (at most {c.REC_CAP}). A shared rank (1, 2, 2, 4) means the same value. Lists are never narrowed to one player.
- **Highest totals**: both innings of every match. **Lowest totals**: only innings that were all out or batted the
  full 20 overs, so an innings stopped by rain is not a low total.
- **Biggest wins**: margins as the result gives them; level wicket margins are ordered by fewer balls used. DLS marks
  a target revised for rain.
- **Partnerships**: from innings whose fall of wickets is complete (* unbroken). The two batters are named only where
  the scorecard says at which wicket each earlier batter fell; the first stand is always the two openers. Else the
  pair is "not known".
- **Fastest fifties**: balls faced to reach 50, counted ball by ball, only where the ball-by-ball record agrees with
  the scorecard for that batter's innings. **Fewest balls for a score of 50 or more** uses the scorecard: the balls of
  the whole innings.
- **Best bowling**: most wickets in an innings, then fewest runs (innings of 3 or more wickets).
- **Ties**: matches level after both innings, decided by a one-over eliminator or a Super Over.
""")

c.section("Trends")
st.markdown(f"""
- **Run rate**: team runs (extras included) per 6 legal balls, both innings of every match, so shortened innings
  compare fairly. **Sixes per 20 overs**: sixes hit per 120 legal balls.
- **By season**: every season of the competition picked at the top (all competitions when none is), whatever season
  is picked. **Which competition scores fastest**: every competition in the season picked (all seasons when none is).
- A season or competition with fewer than {c.SMALL_INNS} matches is Small: a hollow amber point on the line, and
  "(Small)" on the bar. Competitions from different years are not like for like.
""")

c.section("Player journey")
st.markdown("""
- The Player page's Journey tab: every season from his first to his last, with the competitions and teams he played
  for, his matches (every match in the XI, batting or not), runs and wickets. His whole career, whatever competition
  and season are picked. Seasons with no match in between show 0. Totals by season only, never innings by innings.
""")

c.section("Ground profile")
st.markdown(f"""
- **Par**: the average first-innings score at the ground, from first innings of 20 overs or all out, in matches
  without a rain rule. Blank under {c.MIN_INNS} such innings, Small under {c.SMALL_INNS}.
- **Scoring level**: the ground's par divided by the par of the same editions, where each of the ground's matches is
  set against its own edition's par (all grounds of that edition, same rule). In formula: the ground's first-innings
  runs divided by the sum of those editions' pars. 1.00 is usual for those editions; 1.10 means first innings at
  the ground were 10% higher; 0.90, 10% lower. It is a plain ratio, not a model, and does not adjust for the sides
  that played there.
- **Chase and defend**: matches won by the side batting first and by the side batting second, of matches won or lost.
- **Toss effect**: how often the toss winner won, overall and by the choice made (bat or field). Blank under
  {c.MIN_INNS} matches, Small under {c.SMALL_INNS}.
""")

c.section("Data confidence meter")
st.markdown(f"""
At the top of the Insights page only: four plain shares for the chosen competition and season, each "known of all",
with the counts on hover. No part is weighted or added into a score.
- **Fall of wickets**: innings whose score at every wicket is known (and never goes down or passes the total).
- **Fielders**: catches, run outs and stumpings whose fielder is known (fielding numbers need {c.FIELD_MIN_COVER:.0f}%).
- **Entry over**: innings by batters at number 3 or lower for which the over they came in is known.
- **Ball-by-ball**: matches with a ball-by-ball record that agrees with the scorecard (used by Insights and the
  fastest fifties).
""")

c.section("Owner image export")
st.markdown("""
- For the owner only, and hidden unless an owner key is set in the app's secrets: after the key is typed in the Owner
  box under the footer, every bar chart has a Download image button. The image is drawn from the same rows as the
  chart and carries its section, scope, the T20 Crease credit line and the data credit. The key is never stored in
  the app's files or kept after it is checked.
""")

c.section("What the app file holds")
st.markdown("""
- Totals only, by player, edition and team (and by team innings, match and ground), with three exceptions kept for the
  Records lists: every score of 50 or more, every innings of 3 or more wickets, and the two batters of each
  partnership. Each such row is one player's innings, but the app never lists one player's innings one after another:
  the Records lists rank the whole scope and have no player picker, and no page shows a player's game log or a
  scorecard.
- No birth date (the birth year only), no raw profile text and no ball-by-ball rows: the ball-by-ball views use totals
  by phase and over.
""")

# Last section, short (owner, 2026-11-09): every source named in two or three lines.
c.section("Data sources")
st.markdown(
    f"ESPNcricinfo: scorecards and player profiles for all {n_m:,} matches, ball-by-ball for {n_bbb} (for Insights "
    f"where it agrees with the scorecard, and as a check). For the {int(p.in_psl.sum())} players who also played the Pakistan Super League: the developer's PSL "
    "database (Cricsheet.org data, ODC-BY; names and styles checked against Wikipedia, CC BY-SA, and the developer's "
    "own checks). T20 Crease only adds the numbers up and groups styles into its own categories; no birth dates are "
    f"shown. Built {c.date_fmt(str(info['built'])[:10])}, data version {info['data_version']}. Analysis by Hammad.")
c.footer()
