"""
editions.py - every edition: champion, results, a win-loss table and leaders. READ-ONLY (dom_app.sqlite).
The Editions sub-tab of Competitions (competitions.py runs it; owner, 2026-11-10).
Results lists show teams, scores and winner only (owner's decision 2026-11-09: no scorecards).
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Competitions", "Every edition of Pakistan's domestic T20 cups: champion, results, wins and losses, leaders.")
comp, season, eids = c.scope()
label = c.scope_label(comp, season)
ed = c.editions()
ed = ed[ed.edition_id.isin(eids)].sort_values("order", ascending=False)
if ed.empty:
    c.thin(label, "editions")
    c.stop()

if len(ed) > 1:
    c.section("Editions", f"In {label}, newest first.")
    c.table(pd.DataFrame({"Edition": ed.edition_name, "From": ed.first_date.map(c.date_fmt),
                          "To": ed.last_date.map(c.date_fmt), "Teams": ed.teams, "Matches": ed.matches,
                          "Champion": ed.champion.fillna("No final")}),
            {"Teams": c.col_int(), "Matches": c.col_int()})

# Scoring by season: every season of the chosen competition (all competitions when none is chosen), so the trend is
# there whatever season is picked. First innings only; runs per over is fair to rain-shortened innings.
e_all = c.editions()
e_all = e_all if comp == c.COMP_ALL else e_all[e_all.competition == comp]
ra = c.results()
ra = ra[ra.edition_id.isin(e_all.edition_id) & (ra.no_result == 0) & ra.runs_1.notna() & (ra.balls_1 > 0)]
trend = (ra.groupby("season").agg(first=("date", "min"), Matches=("p_match", "count"), runs=("runs_1", "sum"),
                                  balls=("balls_1", "sum")).sort_values("first").reset_index())
trend["Average first-innings score"] = (trend.runs / trend.Matches).round(1)
trend["First-innings runs per over"] = (6 * trend.runs / trend.balls).round(2)
trend = trend.rename(columns={"season": "Season"})
c.section("Scoring by season", f"{c.scope_label(comp, c.SEASON_ALL)[0].upper() + c.scope_label(comp, c.SEASON_ALL)[1:]}: "
                               "first-innings runs per over, every match with a result.")
if len(trend) >= 2:
    c.line_chart(trend, "Season", "First-innings runs per over", fmt=",.2f", title="Runs per over")
    c.table(trend[["Season", "Matches", "Average first-innings score", "First-innings runs per over"]],
            {"Matches": c.col_int(), "Average first-innings score": c.col_1(),
             "First-innings runs per over": c.col_2()}, search="trend" if len(trend) > 15 else None)
    c.note("Runs per over counts every legal ball of the first innings, so rain-shortened innings compare fairly; "
           "the average score does not adjust for them.")
else:
    c.note("This competition has one season only, so there is no trend to show.")

c.section("One edition")
opts = list(ed.edition_id)
want = st.query_params.get("edition")
if "comp_edition" not in st.session_state or st.session_state.comp_edition not in opts:
    st.session_state.comp_edition = int(want) if want and want.isdigit() and int(want) in opts else opts[0]
names_e = dict(zip(ed.edition_id, ed.edition_name))
eid = st.selectbox("Edition", opts, key="comp_edition", format_func=names_e.get)
c.link_set(edition=eid if len(opts) > 1 else None)
e = ed[ed.edition_id == eid].iloc[0]
r = c.results()
r = r[r.edition_id == eid].sort_values(["date", "p_match"], ascending=False)

final = r[r.stage == "final"]
runner = None
if len(final) and pd.notna(final.iloc[0].winner):
    f = final.iloc[0]
    runner = f.team_2 if f.winner == f.team_1 else f.team_1
c.cards([("Champion", e.champion if isinstance(e.champion, str) else "No final", f"beat {runner}" if runner else ""),
         ("Matches", f"{int(e.matches)}", f"{c.date_fmt(e.first_date)} to {c.date_fmt(e.last_date)}"),
         ("Teams", f"{int(e.teams)}", "sides that played at least one match"),
         ("No result", f"{int(r.no_result.sum())}", "matches without a result")], lead=True, detail=True)
if isinstance(e.notes, str) and e.notes:
    c.note(f"About this edition: {e.notes}")
if int(e.matches) < 10:
    c.note(f"A small edition: {int(e.matches)} matches.")

t_res, t_tab, t_lead = c.tabs(["Results", "Wins and losses", "Leaders"], key="comp_tab")
with t_res:
    if t_res.open:
        stages = ["All stages"] + list(dict.fromkeys(r.stage.str.capitalize()))
        st.session_state.setdefault("comp_stage", "All stages")
        if st.session_state.comp_stage not in stages:
            st.session_state.comp_stage = "All stages"
        stg = st.selectbox("Stage", stages, key="comp_stage") if len(stages) > 2 else "All stages"
        rr = r if stg == "All stages" else r[r.stage.str.capitalize() == stg]
        show = pd.DataFrame({"Date": rr.date.map(c.date_fmt), "Stage": rr.stage.str.capitalize(),
                             "Match": rr.team_1 + " v " + rr.team_2,
                             "Scores": rr.score_1.fillna("-") + " v " + rr.score_2.fillna("-"),
                             "Result": rr.result, "Ground": rr.ground})
        c.table(show, {"Match": c.col_text(width="large"), "Result": c.col_text(width="large")}, search="results")
        c.note("Newest first. Scores: the side batting first, then the side batting second. A tie is decided by a "
               "one-over eliminator or a Super Over.")
with t_tab:
    if t_tab.open:
        rows = []
        for t in sorted(set(r.team_1) | set(r.team_2)):
            m = r[(r.team_1 == t) | (r.team_2 == t)]
            done = m[(m.no_result == 0) & (m.tied == 0)]
            rows.append({"Team": t, "Played": len(m), "Won": int((done.winner == t).sum()),
                         "Lost": int(((done.winner != t) & done.winner.notna()).sum()), "Tied": int(m.tied.sum()),
                         "No result": int(m.no_result.sum())})
        tab = pd.DataFrame(rows).sort_values(["Won", "Lost", "Team"], ascending=[False, True, True])
        c.bar_chart(tab, "Team", "Won", title="Wins")
        c.table(tab, {k: c.col_int() for k in ("Played", "Won", "Lost", "Tied", "No result")})
        c.note("Every match of the edition, all stages together. Not the official points table: no points, net run "
               "rate or groups. A tied match counts as tied, not as a win or a loss.")
with t_lead:
    if t_lead.open:
        names = c.players()["name"]
        bat = c.bat_summary(c.in_scope(c.bat_edition(), (eid,)), ["player_id", "team"])
        bowl = c.bowl_summary(c.in_scope(c.bowl_edition(), (eid,)), ["player_id", "team"])
        left, right = st.columns(2)
        with left:
            c.section("Most runs")
            b = bat.sort_values(["runs", "balls"], ascending=[False, True]).head(10)
            c.table(pd.DataFrame({"Player": b.player_id.map(names), "Team": b.team, "Inns": b.innings,
                                  "Runs": b.runs, "SR": b.sr}),
                    {"Inns": c.col_int(), "Runs": c.col_int(), "SR": c.col_1(help=c.HELP["SR"])})
        with right:
            c.section("Most wickets")
            w = bowl.sort_values(["wickets", "runs"], ascending=[False, True]).head(10)
            c.table(pd.DataFrame({"Player": w.player_id.map(names), "Team": w.team, "Inns": w.innings,
                                  "Wkts": w.wickets, "Econ": w.econ}),
                    {"Inns": c.col_int(), "Wkts": c.col_int(), "Econ": c.col_2(help=c.HELP["Econ"])})
        c.note("Strike rate and economy are blank under 5 innings.")

c.footer()
