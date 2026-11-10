"""
teams.py - one team in the chosen competition and season: results by edition, head to head, top players,
partnerships by wicket and the collapse index, extras and discipline, toss. READ-ONLY (dom_app.sqlite, scorecards).
Teams are kept by team ID: spelling variants are one team, eras are not linked (CLAUDE.md).
Partnerships and collapses use only innings whose fall of wickets is complete; extras are the innings' extras as
the scorecard gives them (runs, not deliveries).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Teams", "One side's results, opponents, best players, partnerships, extras and toss calls.")
comp, season, eids = c.scope()
label = c.scope_label(comp, season)
r = c.in_scope(c.results(), eids)
if r.empty:
    c.thin(label)
    c.stop()

tm = pd.concat([r[["team_1_id", "team_1"]].set_axis(["team_id", "team"], axis=1),
                r[["team_2_id", "team_2"]].set_axis(["team_id", "team"], axis=1)])
played = tm.groupby(["team_id", "team"]).size().rename("n").reset_index().sort_values(["n", "team"], ascending=[False, True])
opts = [int(x) for x in played.team_id]
tname = c.team_names()
want = st.query_params.get("team", "")
if st.session_state.get("team_pick") not in opts:
    st.session_state.team_pick = int(want) if want.isdigit() and int(want) in opts else opts[0]
tid = st.selectbox("Team", opts, key="team_pick", format_func=lambda x: tname.get(x, str(x)),
                   help="Teams that played in the competition and season chosen at the top, most matches first.")
c.link_set(team=tid)
team = tname[tid]
mine = r[(r.team_1_id == tid) | (r.team_2_id == tid)].copy()
mine["opp"] = np.where(mine.team_1_id == tid, mine.team_2, mine.team_1)
mine["won"] = (mine.winner_id == tid) & (mine.tied == 0)
mine["lost"] = mine.winner_id.notna() & (mine.winner_id != tid) & (mine.tied == 0)


def wl(g):
    """Played, won, lost, tied, no result and win % (of matches won or lost, blank under 5)."""
    w, lo = int(g.won.sum()), int(g.lost.sum())
    return {"Played": len(g), "Won": w, "Lost": lo, "Tied": int(g.tied.sum()), "No result": int(g.no_result.sum()),
            "Win %": round(100 * w / (w + lo), 1) if w + lo >= c.MIN_INNS else np.nan}


tot = wl(mine)
c.cards([("Matches", f"{tot['Played']}", f"in {label}"),
         ("Won", f"{tot['Won']}", f"{tot['Lost']} lost"),
         ("Win %", c.fmt(tot["Win %"], 1) if pd.notna(tot["Win %"]) else "-",
          "of matches won or lost" if pd.notna(tot["Win %"]) else "not enough matches"),
         ("Tied or no result", f"{tot['Tied'] + tot['No result']}", "ties are decided by an eliminator over")],
        lead=True, detail=True)

with st.container(key="tc_team_tabs"):
    tabs = c.tabs(["Results", "Opponents", "Top players", "Partnerships", "Extras", "Toss"], key="team_tab")
t_res, t_h2h, t_top, t_par, t_ext, t_toss = tabs
INT = c.col_int()

with t_res:
    if t_res.open:
        rows = []
        for eid, g in mine.groupby("edition_id"):
            e_all = r[r.edition_id == eid]
            rows.append({"Edition": g.edition_name.iloc[0], "order": g.order.iloc[0], **wl(g),
                         "Finish": c.stage_reached(e_all[(e_all.team_1_id == tid) | (e_all.team_2_id == tid)], team)})
        t = pd.DataFrame(rows).sort_values("order", ascending=False).drop(columns="order")
        if len(t) > 1:
            c.bar_chart(t, "Edition", "Won", title="Wins by edition")
        c.table(t, {k: INT for k in ("Played", "Won", "Lost", "Tied", "No result")} | {"Win %": c.col_1()})
        c.note("Newest first. Win %: of matches won or lost (ties and no results left out), blank under 5. Finish: the "
               "last stage the team reached (Champion: won the final).")
        c.section("Matches", f"{team} in {label}, newest first.")
        mm = mine.sort_values(["date", "p_match"], ascending=False)
        c.table(pd.DataFrame({"Date": mm.date.map(c.date_fmt), "Edition": mm.edition_name, "Opponent": mm.opp,
                              "Scores": mm.score_1.fillna("-") + " v " + mm.score_2.fillna("-"), "Result": mm.result}),
                {"Result": c.col_text(width="large")}, search="team_matches" if len(mm) > 15 else None)
        c.note("Scores: the side batting first, then the side batting second.")

with t_h2h:
    if t_h2h.open:
        rows = [{"Opponent": o, **wl(g)} for o, g in mine.groupby("opp")]
        t = pd.DataFrame(rows).sort_values(["Played", "Won", "Opponent"], ascending=[False, False, True])
        if len(t) <= 15:
            c.bar_chart(t, "Opponent", "Played", title="Matches against each side")
        c.table(t, {k: INT for k in ("Played", "Won", "Lost", "Tied", "No result")} | {"Win %": c.col_1()},
                search="h2h" if len(t) > 15 else None)
        c.note(f"Every match against each opponent in {label}. Win %: of matches won or lost, blank under 5.")

with t_top:
    if t_top.open:
        names = c.players()["name"]
        bat = c.bat_summary(c.in_scope(c.bat_edition(), eids).pipe(lambda d: d[d.team_id == tid]), ["player_id"])
        bowl = c.bowl_summary(c.in_scope(c.bowl_edition(), eids).pipe(lambda d: d[d.team_id == tid]), ["player_id"])
        c.section("Most runs", f"For {team} in {label}.")
        if bat.empty:
            c.thin(label, "batting")
        else:
            b = bat[bat.runs > 0].sort_values(["runs", "balls"], ascending=[False, True]).head(10)
            d = pd.DataFrame({"Player": b.player_id.map(names), "Inns": b.innings, "Runs": b.runs, "HS": b.hs,
                              "Avg": b.avg, "SR": b.sr, "Sample": b["sample"]})
            c.bar_chart(c.name_cols(d.assign(player_id=b.player_id.values)), "Name", "Runs", tip=["Detail"])
            c.table(d, {"Inns": INT, "Runs": INT, "HS": c.col_text(help=c.HELP["HS"], width="small"),
                        "Avg": c.col_1(help=c.HELP["Avg"]), "SR": c.col_1(help=c.HELP["SR"]),
                        "Sample": c.col_text(help=c.HELP["Sample"], width="small")})
        c.section("Most wickets", f"For {team} in {label}.")
        if bowl.empty or bowl.wickets.max() == 0:
            c.thin(label, "wickets")
        else:
            w = bowl[bowl.wickets > 0].sort_values(["wickets", "runs"], ascending=[False, True]).head(10)
            d = pd.DataFrame({"Player": w.player_id.map(names), "Inns": w.innings, "Wkts": w.wickets, "Best": w.best,
                              "Econ": w.econ, "Bowl avg": w.avg, "Sample": w["sample"]})
            c.bar_chart(c.name_cols(d.assign(player_id=w.player_id.values)), "Name", "Wkts", tip=["Detail"])
            c.table(d, {"Inns": INT, "Wkts": INT, "Best": c.col_text(help=c.HELP["Best"], width="small"),
                        "Econ": c.col_2(help=c.HELP["Econ"]), "Bowl avg": c.col_1(help=c.HELP["Bowl avg"]),
                        "Sample": c.col_text(help=c.HELP["Sample"], width="small")})
        c.note("Rates are blank under 5 innings and marked Small under 10.")

inn = c.in_scope(c.innings_table(), eids)
with t_par:
    if t_par.open:
        mi = inn[inn.team_id == tid]
        ok = mi[mi.fow_complete == 1]
        s = c.stands().merge(ok[["p_match", "innings"]], on=["p_match", "innings"])
        c.section("Partnerships by wicket", f"{team} batting in {label}: from {len(ok)} of {len(mi)} innings "
                                            "(those whose fall of wickets is complete).")
        if s.empty:
            c.thin(label, "innings with a complete fall of wickets")
        else:
            g = s.groupby("wicket").agg(Stands=("runs", "size"), ended=("ended", "sum"), Runs=("runs", "sum"),
                                        Best=("runs", "max"), fifty=("runs", lambda x: int((x >= 50).sum())))
            g = g.reindex(range(1, 11)).fillna(0).astype(int).reset_index()
            g = g[g.Stands > 0]
            t = pd.DataFrame({"Wicket": g.wicket.map(c.wicket_label), "Stands": g.Stands, "Runs": g.Runs,
                              "Average": c.rate(g.Runs, g.ended, n=g.Stands).round(1), "Best": g.Best,
                              "50+ stands": g.fifty, "Sample": c.count_label(g.Stands)})
            if t.Average.notna().sum() >= 2:
                c.bar_chart(t, "Wicket", "Average", fmt=",.1f", title="Average stand (runs)")
            c.table(t, {"Stands": INT, "Runs": INT, "Average": c.col_1(help="Runs per stand that ended (unbroken "
                                                                           "stands add runs but not a stand)."),
                        "Best": INT, "50+ stands": INT, "Sample": c.col_text(width="small")})
            c.note("The nth-wicket stand runs from the fall of wicket n-1 to wicket n (team runs, extras included). "
                   "Average is blank under 5 stands; Small: under 10.")
        c.section("Collapse index", f"Innings with a collapse: {c.COLLAPSE_WKTS} wickets for {c.COLLAPSE_RUNS} runs or "
                                    "fewer, counted from the score at the wicket before.")
        allok = inn[inn.fow_complete == 1]
        bat_n, bat_c = len(ok), int(ok.collapse.sum())
        bo = allok[allok.opp_id == tid]
        bowl_n, bowl_c = len(bo), int(bo.collapse.sum())
        lg = 100 * allok.collapse.mean() if len(allok) else np.nan

        def pc(k, n):
            return c.fmt(100 * k / n, 1) + "%" if n >= c.MIN_INNS else "-"
        c.cards([("Collapsed when batting", pc(bat_c, bat_n), f"{bat_c} of {bat_n} innings" +
                  (f", {c.SMALL} sample" if bat_n < c.SMALL_INNS else "")),
                 ("Caused when bowling", pc(bowl_c, bowl_n), f"{bowl_c} of {bowl_n} innings" +
                  (f", {c.SMALL} sample" if bowl_n < c.SMALL_INNS else "")),
                 ("All sides", c.fmt(lg, 1) + "%" if pd.notna(lg) else "-", f"of {len(allok)} innings in {label}")],
                detail=True)
        c.note("Blank under 5 innings. Only innings whose fall of wickets is complete count.")

with t_ext:
    if t_ext.open:
        bw = inn[inn.opp_id == tid]
        c.section("Extras given away", f"{team} bowling in {label}: per innings, as the scorecard gives them (runs).")
        if bw.empty:
            c.thin(label, "innings")
        else:
            def per_inns(g):
                n = len(g)
                return {"Innings": n, "Extras": round(g.extras.sum() / n, 1), "Wides": round(g.wide_runs.sum() / n, 1),
                        "No-balls": round(g.noball_runs.sum() / n, 1), "Byes": round(g.byes.sum() / n, 1),
                        "Leg byes": round(g.legbyes.sum() / n, 1)}
            rows = [{"Edition": g.edition_id.map(dict(zip(c.editions().edition_id, c.editions().edition_name))).iloc[0],
                     "order": c.editions().set_index("edition_id").order[e], **per_inns(g)} for e, g in bw.groupby("edition_id")]
            t = pd.DataFrame(rows).sort_values("order", ascending=False).drop(columns="order")
            me_, allp = per_inns(bw), per_inns(inn)
            c.cards([("Extras per innings", c.fmt(me_["Extras"], 1), f"all sides {c.fmt(allp['Extras'], 1)}"),
                     ("Wides per innings", c.fmt(me_["Wides"], 1), f"all sides {c.fmt(allp['Wides'], 1)}"),
                     ("No-balls per innings", c.fmt(me_["No-balls"], 1), f"all sides {c.fmt(allp['No-balls'], 1)}"),
                     ("Byes and leg byes", c.fmt(me_["Byes"] + me_["Leg byes"], 1),
                      f"all sides {c.fmt(allp['Byes'] + allp['Leg byes'], 1)}")], detail=True)
            if len(t) > 1:
                c.bar_chart(t, "Edition", "Extras", fmt=",.1f", title="Extras per innings")
            c.table(t, {"Innings": INT, **{k: c.col_1() for k in ("Extras", "Wides", "No-balls", "Byes", "Leg byes")}})
            c.note("Runs per innings bowled. Wides and no-balls are the runs the scorecard lists for them, not the "
                   "number of deliveries; byes and leg byes are not the bowler's. Newest edition first.")

with t_toss:
    if t_toss.open:
        d = mine[mine.toss_winner_id.notna()].copy()
        d["won_toss"] = d.toss_winner_id == tid
        d["bat_first"] = d.team_1_id == tid
        rows = []
        for lab_, g in (("Won the toss", d[d.won_toss]), ("Lost the toss", d[~d.won_toss]),
                        ("Won the toss, chose to bat", d[d.won_toss & (d.toss_choice == "bat")]),
                        ("Won the toss, chose to field", d[d.won_toss & (d.toss_choice == "bowl")]),
                        ("Batted first", d[d.bat_first]), ("Batted second", d[~d.bat_first])):
            rows.append({"Situation": lab_, **wl(g)})
        t = pd.DataFrame(rows)[["Situation", "Played", "Won", "Lost", "Win %"]]
        n_t = int(d.won_toss.sum())
        c.cards([("Tosses won", f"{n_t}", f"of {len(d)} matches"),
                 ("Chose to field", f"{int((d.won_toss & (d.toss_choice == 'bowl')).sum())}", f"of {n_t} tosses won"),
                 ("Win % after winning the toss", c.fmt(t["Win %"].iloc[0], 1) if pd.notna(t["Win %"].iloc[0]) else "-",
                  "of matches won or lost")], detail=True)
        c.table(t, {k: INT for k in ("Played", "Won", "Lost")} | {"Win %": c.col_1()})
        c.note("Win %: of matches won or lost (ties and no results left out), blank under 5.")

c.footer()
