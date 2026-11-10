"""
records.py - record lists for the chosen competition and season: highest and lowest team totals, biggest wins by runs
and by wickets, record partnerships, fastest fifties, best bowling, and ties decided by an eliminator over.
READ-ONLY (dom_app.sqlite: innings, results, stands, stand_batters, rec_bat, rec_bowl).
Each list shows the top 10 and any row level with the 10th (at most 25). Lists are never filtered to one player.
Lowest totals: innings that were all out or lasted the full 20 overs. Partnerships: innings with a complete fall of
wickets only. Fastest fifties: balls faced to reach 50, only where the ball-by-ball agrees with the scorecard for that
batter's innings.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Records", "The best and worst of the chosen competition and season: totals, wins, stands, fifties, bowling.")
comp, season, eids = c.scope()
label = c.scope_label(comp, season)
r = c.in_scope(c.results(), eids)
if r.empty:
    c.thin(label)
    c.stop()

tn = c.team_names()
info = r.set_index("p_match")[["date", "edition_name"]]


def with_match(d):
    """Edition and date columns from the match."""
    d = d.join(info, on="p_match")
    d["Date"] = d.date.map(c.date_fmt)
    d["Edition"] = d.edition_name
    return d


INT = c.col_int()
with st.container(key="tc_rec_tabs"):
    tabs = c.tabs(["Team totals", "Biggest wins", "Partnerships", "Fifties", "Best bowling", "Ties"], key="rec_tab")
t_tot, t_win, t_par, t_fif, t_bowl, t_tie = tabs

with t_tot:
    if t_tot.open:
        inn = with_match(c.in_scope(c.innings_table(), eids).copy())
        inn["Score"] = [f"{int(x)}" + ("" if w == 10 else f"/{int(w)}") for x, w in zip(inn.runs, inn.wkts)]
        inn["Overs"] = [c.overs(b) for b in inn.balls]
        inn["Team"], inn["Opponent"] = inn.team, inn.opp
        cols = ["#", "Score", "Overs", "Team", "Opponent", "Edition", "Date"]
        cfg = {"#": INT, "Score": c.col_text(width="small"), "Overs": c.col_text(width="small")}
        c.section("Highest totals", f"In {label}. Both innings of every match.")
        hi = c.top_ranked(inn, ["runs", "wkts", "balls", "date"], [False, True, True, True], ["runs"])
        c.table(hi[cols], cfg)
        c.section("Lowest totals", "Innings that were all out or batted the full 20 overs.")
        done = inn[(inn.wkts == 10) | (inn.balls == 120)]
        lo = c.top_ranked(done, ["runs", "balls", "date"], [True, True, True], ["runs"])
        if lo.empty:
            c.empty("No innings was all out or lasted 20 overs here.")
        else:
            c.table(lo[cols], cfg)
        c.note("Ranked by runs; a shared rank means the same total. An innings cut short by rain and not all out is "
               "left out of the lowest totals.")

with t_win:
    if t_win.open:
        d = with_match(r[["p_match", "winner", "team_1", "team_2", "score_1", "score_2", "margin", "margin_kind", "dls",
                          "balls_2"]].copy())
        d["Winner"] = d.winner
        d["Loser"] = np.where(d.winner == d.team_1, d.team_2, d.team_1)
        d["Scores"] = d.score_1.fillna("-") + " v " + d.score_2.fillna("-")
        d["Rain rule"] = np.where(d.dls == 1, "DLS", "")
        cfg = {"#": INT, "Margin": c.col_text(width="small"), "Scores": c.col_text(width="large")}
        c.section("By runs", f"In {label}. The side batting first won.")
        runs = d[d.margin_kind == "run"].copy()
        runs["Margin"] = runs.margin.astype(int).map(lambda x: f"{x} run{'s' if x != 1 else ''}")
        tr = c.top_ranked(runs, ["margin", "date"], [False, True], ["margin"])
        if tr.empty:
            c.empty("No match was won by runs here.")
        else:
            c.table(tr[["#", "Margin", "Winner", "Loser", "Scores", "Edition", "Date", "Rain rule"]], cfg)
        c.section("By wickets", "The side batting second won. Level margins: fewer balls used first.")
        wk = d[d.margin_kind == "wicket"].copy()
        wk["Margin"] = wk.margin.astype(int).map(lambda x: f"{x} wicket{'s' if x != 1 else ''}")
        wk["Balls used"] = wk.balls_2.astype(int)
        tw = c.top_ranked(wk, ["margin", "balls_2", "date"], [False, True, True], ["margin", "balls_2"])
        if tw.empty:
            c.empty("No match was won by wickets here.")
        else:
            c.table(tw[["#", "Margin", "Balls used", "Winner", "Loser", "Scores", "Edition", "Date", "Rain rule"]],
                    cfg | {"Balls used": c.col_int(help="Balls the chasing side needed (legal balls, from the scorecard).")})
        c.note("Margins as the result gives them. DLS: the target was revised for rain (Duckworth-Lewis-Stern).")

with t_par:
    if t_par.open:
        inn = c.in_scope(c.innings_table(), eids)
        done = inn[inn.fow_complete == 1][["p_match", "innings", "team", "opp"]]
        s = c.stands().merge(done, on=["p_match", "innings"]).merge(
            c.rec_table("stand_batters"), on=["p_match", "innings", "wicket"], how="left")
        s = with_match(s)
        known = s.bat_a.notna()
        s["Runs"] = [f"{int(x)}{'*' if e == 0 else ''}" for x, e in zip(s.runs, s.ended)]
        s["Wicket"] = s.wicket.map(c.wicket_label)
        s["Batters"] = [f"{c.name(int(a))} and {c.name(int(b))}" if pd.notna(a) else "not known"
                        for a, b in zip(s.bat_a, s.bat_b)]
        s["Team"], s["Opponent"] = s.team, s.opp
        c.section("Highest partnerships", f"In {label}, any wicket.")
        top = c.top_ranked(s, ["runs", "date"], [False, True], ["runs"])
        if top.empty:
            c.empty("No innings here has a complete fall of wickets.")
        else:
            c.table(top[["#", "Runs", "Wicket", "Batters", "Team", "Opponent", "Edition", "Date"]],
                    {"#": INT, "Runs": c.col_text(width="small"), "Batters": c.col_text(width="large")})
        c.section("Best stand for each wicket")
        rows = []
        for w_, g in s.groupby("wicket"):
            b = g.sort_values(["runs", "date"], ascending=[False, True]).iloc[0]
            rows.append({"Wicket": c.wicket_label(w_), "Runs": b.Runs, "Batters": b.Batters, "Team": b.Team,
                         "Opponent": b.Opponent, "Edition": b.Edition, "Date": b.Date})
        if rows:
            c.table(pd.DataFrame(rows), {"Runs": c.col_text(width="small"), "Batters": c.col_text(width="large")})
        n_inn = len(inn)
        c.note(f"From the {len(done):,} of {n_inn:,} innings whose fall of wickets is complete. * unbroken. The two "
               f"batters are known for {int(known.sum()):,} of {len(s):,} stands here ({c.pct(int(known.sum()), len(s)):.0f}%): "
               "the scorecards often do not say at which wicket a batter fell; the first stand is always the openers.")

with t_fif:
    if t_fif.open:
        f = with_match(c.in_scope(c.rec_table("rec_bat"), eids).copy())
        f["Player"] = f.player_id.map(c.name)
        f["Score"] = [f"{int(x)}{'*' if n else ''}" for x, n in zip(f.runs, f.not_out)]
        f["Team"], f["Opponent"] = f.team_id.map(tn), f.opp_id.map(tn)
        c.section("Fastest fifties", "Balls faced to reach 50, from the ball-by-ball record.")
        fb = f[f.fifty_balls.notna()].copy()
        if fb.empty:
            c.empty(f"No ball-by-ball fifty in {label}.",
                    " Balls to reach 50 are known only where the ball-by-ball record agrees with the scorecard; try "
                    "All seasons.")
        else:
            fb["Balls to 50"] = fb.fifty_balls.astype(int)
            t = c.top_ranked(fb, ["fifty_balls", "date"], [True, True], ["fifty_balls"])
            c.table(t[["#", "Balls to 50", "Player", "Score", "Team", "Opponent", "Edition", "Date"]],
                    {"#": INT, "Balls to 50": INT, "Score": c.col_text(width="small")})
        c.note(f"Known for {len(fb)} of the {len(f)} scores of 50 or more here: only innings whose ball-by-ball record "
               "agrees with the scorecard, ball by ball, for that batter.")
        c.section("Fewest balls for a score of 50 or more", "From the scorecards: balls faced in the whole innings.")
        f["Balls"] = f.balls.astype(int)
        f["SR"] = (100 * f.runs / f.balls).round(1)
        t = c.top_ranked(f[f.balls > 0], ["balls", "runs", "date"], [True, False, True], ["balls"])
        if t.empty:
            c.empty(f"No score of 50 or more in {label}.")
        else:
            c.table(t[["#", "Balls", "Score", "SR", "Player", "Team", "Opponent", "Edition", "Date"]],
                    {"#": INT, "Balls": INT, "Score": c.col_text(width="small"), "SR": c.col_1(help=c.HELP["SR"])})
        c.note("The whole innings, not the balls to reach 50: a batter who went on after 50 faced more balls. "
               "Level balls: more runs first.")

with t_bowl:
    if t_bowl.open:
        w = with_match(c.in_scope(c.rec_table("rec_bowl"), eids).copy())
        w["Figures"] = [c.best_text(a, b) for a, b in zip(w.wickets, w.runs)]
        w["Overs"] = [c.overs(b) for b in w.balls]
        w["Player"] = w.player_id.map(c.name)
        w["Team"], w["Opponent"] = w.team_id.map(tn), w.opp_id.map(tn)
        c.section("Best bowling in an innings", f"In {label}. Most wickets, then fewest runs.")
        t = c.top_ranked(w, ["wickets", "runs", "balls", "date"], [False, True, True, True], ["wickets", "runs"])
        if t.empty:
            c.empty(f"Nobody took 3 wickets in an innings in {label}.")
        else:
            c.table(t[["#", "Figures", "Overs", "Player", "Team", "Opponent", "Edition", "Date"]],
                    {"#": INT, "Figures": c.col_text(width="small"), "Overs": c.col_text(width="small")})
        c.note("Wickets as the scorecard credits them to the bowler (run outs are not his). A shared rank means the "
               "same wickets and runs.")

with t_tie:
    if t_tie.open:
        tie = r[r.tied == 1].sort_values(["date", "p_match"], ascending=False)
        c.section("Ties", f"In {label}: matches level after both innings, decided by a one-over eliminator or a Super Over.")
        if tie.empty:
            c.empty(f"No tied match in {label}.")
        else:
            c.table(pd.DataFrame({"Date": tie.date.map(c.date_fmt), "Edition": tie.edition_name,
                                  "Match": tie.team_1 + " v " + tie.team_2,
                                  "Scores": tie.score_1.fillna("-") + " v " + tie.score_2.fillna("-"),
                                  "Decided by": tie.result.str.replace("Tied; ", "", regex=False)}),
                    {"Match": c.col_text(width="large"), "Decided by": c.col_text(width="large")})
            c.note("Newest first. The winner of the eliminator over is from the match report (data corrections, "
                   "Method).")
c.footer()
