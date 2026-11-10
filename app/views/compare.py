"""
compare.py - two players side by side in the chosen competition and season: batting, bowling, and both by
competition and by season. READ-ONLY (dom_app.sqlite bat_edition and bowl_edition, scorecards only).
Players are chosen by Cricinfo player ID; rates are blank under 5 innings and marked Small under 10.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Compare", "Two players side by side: batting and bowling, by competition and by season.")
comp, season, eids = c.scope()
label = c.scope_label(comp, season)
p = c.players()
options = c.player_order()
allbat, allbowl = c.bat_edition(), c.bowl_edition()
top = c.in_scope(allbat, eids).groupby("player_id").runs.sum().sort_values(ascending=False)
top = top if len(top) >= 2 else allbat.groupby("player_id").runs.sum().sort_values(ascending=False)
for key, i in (("cmp_a", 0), ("cmp_b", 1)):
    want = st.query_params.get(key[-1], "")
    if key not in st.session_state:
        st.session_state[key] = int(want) if want.isdigit() and int(want) in p.index else int(top.index[i])
left, right = st.columns(2)
a = left.selectbox("Player A", options, key="cmp_a", format_func=c.name, placeholder="Type a name")
b = right.selectbox("Player B", options, key="cmp_b", format_func=c.name, placeholder="Type a name")
c.link_set(a=a, b=b)
if a == b:
    c.empty("Choose two different players.", " Type a name in Player B.")
    c.stop()

# plain names; "(b. 1987)" only when both players have the same name (owner, 2026-11-10)
short = tuple(c.short_names([a, b]))
if p.base_name[a] == p.base_name[b]:
    c.note(f"Two players named {p.base_name[a]}: {short[0]} is {c.player_detail(a)}; {short[1]} is {c.player_detail(b)}.")
bat = {x: c.in_scope(allbat[allbat.player_id == x], eids) for x in (a, b)}
bowl = {x: c.in_scope(allbowl[allbowl.player_id == x], eids) for x in (a, b)}
if all(bat[x].empty and bowl[x].empty for x in (a, b)):
    c.thin(label, "matches for either player")
    c.stop()


def bat_line(x):
    s = c.bat_summary(bat[x], ["player_id"])
    if s.empty:
        return {}
    s = s.iloc[0]
    return {"Matches": int(s.matches), "Innings": int(s.innings), "Runs": int(s.runs), "Average": s.avg,
            "Strike rate": s.sr, "High score": s.hs, "50s": int(s.fifties), "100s": int(s.hundreds), "4s": int(s.fours),
            "6s": int(s.sixes), "Sample": s["sample"]}


def bowl_line(x):
    s = c.bowl_summary(bowl[x], ["player_id"])
    if s.empty:
        return {}
    s = s.iloc[0]
    return {"Innings": int(s.innings), "Overs": s.overs, "Wickets": int(s.wickets), "Economy": s.econ, "Average": s.avg,
            "Strike rate": s.sr, "Best": s.best, "4w": int(s.four_w), "Sample": s["sample"]}


def side_by_side(la, lb, nd):
    keys = list(dict.fromkeys(list(la) + list(lb)))
    if not keys:
        return pd.DataFrame()

    def show(v, k):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "-"
        if isinstance(v, (int, np.integer)):
            return f"{v:,}"
        if isinstance(v, float):
            return f"{v:,.{nd.get(k, 1)}f}"
        return str(v) if v != "" else "-"
    return pd.DataFrame({"Measure": keys, short[0]: [show(la.get(k), k) for k in keys],
                         short[1]: [show(lb.get(k), k) for k in keys]})


cfg = {short[0]: c.col_text(width="medium"), short[1]: c.col_text(width="medium")}
c.section("Batting", f"In {label}.")
t = side_by_side(bat_line(a), bat_line(b), {"Average": 1, "Strike rate": 1})
if len(t):
    c.table(t, cfg)
else:
    c.empty(f"Neither player batted in {label}.")
c.section("Bowling", f"In {label}.")
t = side_by_side(bowl_line(a), bowl_line(b), {"Economy": 2, "Average": 1, "Strike rate": 1})
if len(t):
    c.table(t, cfg)
else:
    c.empty(f"Neither player bowled in {label}.")
c.note("Rates are blank under 5 innings; Sample: Small under 10 innings. Bowling strike rate: balls per wicket.")


def by(col, order_col):
    """Runs and wickets of both players by competition or season, with innings, in the order of first play."""
    rows = []
    for x, tag in ((a, "A"), (b, "B")):
        bb = bat[x].merge(c.editions()[["edition_id", "competition", "season"]], on="edition_id")
        ww = bowl[x].merge(c.editions()[["edition_id", "competition", "season"]], on="edition_id")
        g1 = bb.groupby(col).agg(**{f"Runs {tag}": ("runs", "sum"), f"Inns {tag}": ("innings", "sum"),
                                    "first": ("first_date", "min")})
        g2 = ww.groupby(col).agg(**{f"Wkts {tag}": ("wickets", "sum"), "first_w": ("first_date", "min")})
        rows.append(g1.join(g2, how="outer"))
    d = rows[0].add_suffix("_a").join(rows[1].add_suffix("_b"), how="outer")
    d.columns = [k[:-2] if k[:-2] in ("Runs A", "Inns A", "Wkts A", "Runs B", "Inns B", "Wkts B") else k for k in d.columns]
    d["first"] = d[[k for k in d.columns if k.startswith("first")]].min(axis=1)
    d = d.sort_values("first").reset_index().rename(columns={col: col.capitalize()})
    for k in ("Inns A", "Runs A", "Wkts A", "Inns B", "Runs B", "Wkts B"):
        d[k] = d[k].fillna(0).astype(int) if k in d else 0
    return d[[col.capitalize(), "Inns A", "Runs A", "Wkts A", "Inns B", "Runs B", "Wkts B"]]


INT = c.col_int()
lab_cfg = {f"{k} {x}": c.col_int(f"{k} {short[i]}") for k in ("Inns", "Runs", "Wkts") for i, x in enumerate("AB")}
t_comp, t_season = c.tabs(["By competition", "By season"], key="cmp_tab")
for tab, col in ((t_comp, "competition"), (t_season, "season")):
    with tab:
        if tab.open:
            d = by(col, "first")
            if d.empty:
                c.thin(label)
                continue
            what = "Runs" if (d["Runs A"].sum() + d["Runs B"].sum()) >= (d["Wkts A"].sum() + d["Wkts B"].sum()) * 10 else "Wkts"
            c.pair_bar_chart(d, col.capitalize(), f"{what} A", f"{what} B", names=short,
                             title="Runs" if what == "Runs" else "Wickets")
            c.table(d, lab_cfg)
            c.note(f"In order of first play. Innings: innings batted. The chart shows {'runs' if what == 'Runs' else 'wickets'}.")
c.footer()
