"""
leaderboards.py - top 10 (or 25) by runs, highest score, strike rate, sixes and fours, wickets, best bowling,
economy and bowling average. READ-ONLY (dom_app.sqlite, scorecards only).
Scope: the header's competition and season ("Chosen season"), or every season of the chosen competition ("Career").
Rates need a minimum of balls and 5 innings (rules under each table); thin rows carry the Small badge.
Fielding: catches, wicketkeeping and run outs, shown only where the fielder is known for at least 95% of
those dismissals in the chosen span (owner's rule 2026-11-09); the coverage is written on every board.
Young talent (owner, 2026-11-10, feature 7): runs or wickets by players under 23, from the birth year only: age in a
season = the season's first year minus the birth year (approximate, can be a year out); only his seasons under 23
count; players without a birth year are left out and counted on the page.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Leaderboards", "The best batters and bowlers for the chosen competition and season, or across a career.")
comp, season, eids = c.scope()
CHOSEN, CAREER = "Chosen season", "Career"
st.session_state.setdefault("lb_span", CHOSEN)
left, right = st.columns([3, 1], vertical_alignment="center")
with left:
    span = st.segmented_control("Span", [CHOSEN, CAREER], key="lb_span", required=True, label_visibility="collapsed",
                                help="Chosen season: the competition and season at the top. Career: every season of "
                                     "the chosen competition (all competitions when none is chosen).")
with right:
    n_show = 25 if st.toggle("Show 25", key="lb_25", help="Show the top 25 instead of the top 10.") else 10
if span == CAREER:
    e = c.editions()
    eids = tuple(int(x) for x in (e if comp == c.COMP_ALL else e[e.competition == comp]).edition_id)
    label = c.scope_label(comp, c.SEASON_ALL)
    c.note(f"Career: {label}." + (" The season chosen at the top is not used." if season != c.SEASON_ALL else ""))
else:
    label = c.scope_label(comp, season)
if not eids:
    c.thin(label)
    c.stop()

c.export_context(f"In {label}.")
rules = c.lb_rules(eids)
span_txt = "one season" if c.one_season(eids) else "more than one season"
names = c.players()["name"]
teams = c.teams_by_player(eids)
bat = c.bat_summary(c.in_scope(c.bat_edition(), eids), ["player_id"])
bowl = c.bowl_summary(c.in_scope(c.bowl_edition(), eids), ["player_id"])


def named(df):
    df = df.reset_index(drop=True).copy()
    df.insert(0, "#", range(1, len(df) + 1))
    df.insert(1, "Player", df.player_id.map(names))
    df.insert(2, "Teams", df.player_id.map(teams))
    return df


INT = c.col_int()
CFG = {"#": INT, "Inns": INT, "Runs": INT, "Balls": INT, "6s": INT, "4s": INT, "Wkts": INT, "Score": INT,
       "Avg": c.col_1(help=c.HELP["Avg"]), "SR": c.col_1(help=c.HELP["SR"]), "Econ": c.col_2(help=c.HELP["Econ"]),
       "Bowl avg": c.col_1(help=c.HELP["Bowl avg"]), "Overs": c.col_text(width="small"),
       "Sample": c.col_text(help=c.HELP["Sample"], width="small"), "Teams": c.col_text(help=c.HELP["Teams"])}


def board(df, value, cols, fmt=",.0f", rule="", text=None):
    """Bars and the table from the same rows (so the chart shows the table's values), then the rule."""
    if df.empty:
        c.thin(label, "qualifying players")
    else:
        c.bar_chart(c.name_cols(df, teams="Teams"), "Name", value, fmt=fmt, text=text, tip=["Detail"])
        c.table(df[["#", "Player", "Teams"] + cols], CFG)
    if rule:
        c.note(rule)


with st.container(key="tc_lb_tabs"):
    tabs = c.tabs(["Runs", "Highest scores", "Strike rate", "Sixes and fours", "Wickets", "Best bowling", "Economy",
                   "Bowling average", "Fielding", "Young talent"], key="lb_tab")
t_runs, t_hs, t_sr, t_bd, t_wk, t_bb, t_ec, t_av, t_fd, t_yt = tabs

with t_runs:
    if t_runs.open:
        d = named(bat[bat.runs > 0].sort_values(["runs", "balls"], ascending=[False, True]).head(n_show))
        d = d.rename(columns={"innings": "Inns", "runs": "Runs", "avg": "Avg", "sr": "SR", "sample": "Sample"})
        board(d, "Runs", ["Inns", "Runs", "Avg", "SR", "Sample"],
              rule=f"All players in {label}. Average and strike rate are blank under {c.MIN_INNS} innings; "
                   f"Small: under {c.SMALL_INNS} innings.")
with t_hs:
    if t_hs.open:
        b = c.best_innings(eids).sort_values(["high", "high_not_out"], ascending=False).head(n_show)
        d = named(b)
        d["Score"] = d.high.astype(int)
        d["Not out"] = d.high_not_out.map({1: "not out"}).fillna("")
        d["Shown"] = d.Score.astype(str) + d.high_not_out.map({1: "*"}).fillna("")
        d = d.rename(columns={"edition_name": "Edition", "team": "Team"})
        if d.empty:
            c.thin(label, "innings")
        else:
            c.bar_chart(c.name_cols(d, teams="Teams"), "Name", "Score", text="Shown", tip=["Detail"])
            c.table(d[["#", "Player", "Score", "Not out", "Edition", "Team"]], CFG)
        c.note("Each player's highest score in the chosen span (his best innings only, so a player is listed once); "
               "* not out.")
with t_sr:
    if t_sr.open:
        q = bat[(bat.balls >= rules["bf"]) & bat.sr.notna()].sort_values(["sr", "runs"], ascending=False).head(n_show)
        d = named(q).rename(columns={"innings": "Inns", "balls": "Balls", "runs": "Runs", "sr": "SR", "sample": "Sample"})
        board(d, "SR", ["Inns", "Balls", "Runs", "SR", "Sample"], fmt=",.1f",
              rule=f"Minimum {rules['bf']} balls faced and {c.MIN_INNS} innings ({span_txt}).")
with t_bd:
    if t_bd.open:
        by = st.segmented_control("Sort by", ["Sixes", "Fours"], key="lb_bd_sort", default="Sixes", required=True)
        col = "sixes" if by == "Sixes" else "fours"
        q = bat[bat[col] > 0].sort_values([col, "balls"], ascending=[False, True]).head(n_show)
        d = named(q).rename(columns={"sixes": "6s", "fours": "4s", "innings": "Inns", "balls": "Balls", "sample": "Sample"})
        board(d, "6s" if col == "sixes" else "4s", ["Inns", "6s", "4s", "Balls", "Sample"],
              rule=f"All players in {label}, by {by.lower()}; ties go to the player who faced fewer balls.")
with t_wk:
    if t_wk.open:
        q = bowl[bowl.wickets > 0].sort_values(["wickets", "runs"], ascending=[False, True]).head(n_show)
        d = named(q).rename(columns={"innings": "Inns", "wickets": "Wkts", "overs": "Overs", "econ": "Econ",
                                     "avg": "Bowl avg", "sample": "Sample"})
        board(d, "Wkts", ["Inns", "Wkts", "Overs", "Econ", "Bowl avg", "Sample"],
              rule=f"All players in {label}. Economy and average are blank under {c.MIN_INNS} innings; "
                   f"Small: under {c.SMALL_INNS} innings.")
with t_bb:
    if t_bb.open:
        b = c.best_figures(eids)
        b = b[b.best_wickets > 0].head(n_show)
        d = named(b)
        d["Wkts"] = d.best_wickets.astype(int)
        d["Runs"] = d.best_runs.astype(int)
        d["Figures"] = d.Wkts.astype(str) + "/" + d.Runs.astype(str)
        d = d.rename(columns={"edition_name": "Edition", "team": "Team"})
        if d.empty:
            c.thin(label, "wickets")
        else:
            c.bar_chart(c.name_cols(d, teams="Teams"), "Name", "Wkts", text="Figures", tip=["Detail"])
            c.table(d[["#", "Player", "Figures", "Wkts", "Runs", "Edition", "Team"]], CFG)
        c.note("Each player's best figures in one innings in the chosen span: most wickets, then fewest runs; a player "
               "is listed once.")
with t_ec:
    if t_ec.open:
        q = bowl[(bowl.balls >= rules["bb"]) & bowl.econ.notna()].sort_values(["econ", "wickets"], ascending=[True, False]).head(n_show)
        d = named(q).rename(columns={"innings": "Inns", "overs": "Overs", "runs": "Runs", "econ": "Econ",
                                     "wickets": "Wkts", "sample": "Sample"})
        board(d, "Econ", ["Inns", "Overs", "Runs", "Econ", "Wkts", "Sample"], fmt=",.2f",
              rule=f"Minimum {rules['bb'] // 6} overs and {c.MIN_INNS} innings ({span_txt}). Lowest first.")
with t_av:
    if t_av.open:
        q = bowl[(bowl.balls >= rules["bb"]) & (bowl.wickets >= rules["avg_w"]) & bowl.avg.notna()] \
            .sort_values(["avg", "wickets"], ascending=[True, False]).head(n_show)
        d = named(q).rename(columns={"innings": "Inns", "wickets": "Wkts", "runs": "Runs", "avg": "Bowl avg",
                                     "econ": "Econ", "sample": "Sample"})
        board(d, "Bowl avg", ["Inns", "Wkts", "Runs", "Bowl avg", "Econ", "Sample"], fmt=",.1f",
              rule=f"Minimum {rules['bb'] // 6} overs, {rules['avg_w']} wickets and {c.MIN_INNS} innings ({span_txt}). "
                   "Lowest first.")

with t_fd:
    if t_fd.open:
        kind = st.segmented_control("Board", ["Catches", "Wicketkeeping", "Run outs"], key="lb_fd_kind", default="Catches",
                                    required=True)
        need = {"Catches": ("ct",), "Wicketkeeping": ("ct", "st"), "Run outs": ("ro",)}[kind]
        cov = c.coverage(eids)
        if not c.cover_ok(cov, need):
            words = {"ct": "catches", "ro": "run outs", "st": "stumpings"}
            low = [f"{cov[k][2]:.0f}% of {words[k]}" for k in need if cov[k][1] and cov[k][2] < c.FIELD_MIN_COVER]
            c.empty(f"No {kind.lower()} leaderboard for {label}.",
                    f" The source names the fielder for only {', '.join(low)} here; a board needs at least "
                    f"{c.FIELD_MIN_COVER:.0f}%. Try another competition or season.")
        else:
            f = c.in_scope(c.fielding(), eids).groupby("player_id")[["matches", "catches", "cb_catches", "sub_catches",
                                                                     "keeper_catches", "stumpings", "run_outs"]].sum()
            f["ct_all"] = f.catches + f.cb_catches + f.sub_catches
            f["wk_all"] = f.keeper_catches + f.stumpings
            col, sort2 = {"Catches": ("ct_all", "matches"), "Wicketkeeping": ("wk_all", "matches"),
                          "Run outs": ("run_outs", "matches")}[kind]
            q = f[f[col] > 0].sort_values([col, sort2], ascending=[False, True]).head(n_show).reset_index()
            d = named(q).rename(columns={"matches": "Matches", "ct_all": "Ct", "cb_catches": "C&b", "sub_catches": "As sub",
                                         "keeper_catches": "Keeper ct", "stumpings": "St", "wk_all": "Dismissals",
                                         "run_outs": "Run outs"})
            cols = {"Catches": ["Matches", "Ct", "C&b", "As sub"], "Wicketkeeping": ["Matches", "Dismissals", "Keeper ct", "St"],
                    "Run outs": ["Matches", "Run outs"]}[kind]
            val = {"Catches": "Ct", "Wicketkeeping": "Dismissals", "Run outs": "Run outs"}[kind]
            for k_ in cols:
                CFG[k_] = INT
            rule = {"Catches": "Catches in the field, caught and bowled and catches as a substitute included; a "
                                "wicketkeeper's catches are on Wicketkeeping.",
                    "Wicketkeeping": "Catches as wicketkeeper plus stumpings.",
                    "Run outs": "Every fielder named in a run out is credited."}[kind]
            board(d, val, cols, rule=f"{rule} Ties go to the player with fewer matches. {c.cover_text(cov, 'in ' + label)}")

with t_yt:
    if t_yt.open:
        kind = st.segmented_control("Board", ["Runs", "Wickets"], key="lb_yt_kind", default="Runs", required=True)
        yb, yw, n_unknown = c.young_rows(eids)
        if kind == "Runs":
            s_ = c.bat_summary(yb, ["player_id"]) if len(yb) else pd.DataFrame()
            q = s_[s_.runs > 0].sort_values(["runs", "balls"], ascending=[False, True]).head(n_show) if len(s_) else s_
            d = named(q) if len(q) else q
            if len(d):
                d["Age"] = d.player_id.map(c.young_ages(yb))
                d["Teams"] = d.player_id.map(c.young_teams(yb))
                d = d.rename(columns={"innings": "Inns", "runs": "Runs", "sr": "SR", "avg": "Avg", "sample": "Sample"})
            cols = ["Age", "Inns", "Runs", "Avg", "SR", "Sample"]
        else:
            s_ = c.bowl_summary(yw, ["player_id"]) if len(yw) else pd.DataFrame()
            q = s_[s_.wickets > 0].sort_values(["wickets", "runs"], ascending=[False, True]).head(n_show) if len(s_) else s_
            d = named(q) if len(q) else q
            if len(d):
                d["Age"] = d.player_id.map(c.young_ages(yw))
                d["Teams"] = d.player_id.map(c.young_teams(yw))
                d = d.rename(columns={"innings": "Inns", "wickets": "Wkts", "overs": "Overs", "econ": "Econ",
                                     "avg": "Bowl avg", "sample": "Sample"})
            cols = ["Age", "Inns", "Wkts", "Overs", "Econ", "Bowl avg", "Sample"]
        CFG["Age"] = c.col_text("Age", help="Approximate age in the seasons counted: the season's first year minus the "
                                            "birth year.", width="small")
        board(d, "Runs" if kind == "Runs" else "Wkts", cols,
              rule=f"Under 23: only the seasons in which he was {c.YOUNG_MAX} or younger count, in {label}. Age is "
                   "approximate (the season's first year minus the birth year; the app keeps the birth year only), so it "
                   f"can be a year out. {n_unknown} player{'s' if n_unknown != 1 else ''} here with no known birth year "
                   f"{'are' if n_unknown != 1 else 'is'} left out. Rates are blank under {c.MIN_INNS} innings; Small: "
                   f"under {c.SMALL_INNS} innings.")

c.footer()
