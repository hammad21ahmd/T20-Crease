"""
home.py - the chosen competition and season at a glance: summary cards, champions, and five leader cards with a
"See all" link to Leaderboards. READ-ONLY (dom_app.sqlite).
Leader cards follow the Leaderboards rules (same sort, minimum balls and 5 innings for rates): label, name
(a link to his Player page), number, '+N tied' when others share it, a short caption; 'not enough data' when
nobody qualifies.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Overview", "Leaders, champions and results of Pakistan's domestic T20 cups, 2004/05 to 2025/26.")
comp, season, eids = c.scope()
label = c.scope_label(comp, season)
r = c.in_scope(c.results(), eids)
if r.empty:
    c.thin(label)
    c.stop()

bat = c.in_scope(c.bat_edition(), eids)
bowl = c.in_scope(c.bowl_edition(), eids)
ed = c.editions()
ed = ed[ed.edition_id.isin(eids)].sort_values("order", ascending=False)
nr = int(r.no_result.sum())
c.cards([("Matches", f"{len(r):,}", f"{len(ed)} edition{'s' if len(ed) != 1 else ''}" + (f", {nr} no result" if nr else "")),
         ("Runs", f"{int(bat.runs.sum()):,}", "off the bat, extras not counted"),
         ("Wickets", f"{int(bowl.wickets.sum()):,}", "credited to bowlers (no run outs)"),
         ("Sixes", f"{int(bat.sixes.sum()):,}", f"{int(bat.fours.sum()):,} fours"),
         ("Hundreds", f"{int(bat.hundreds.sum()):,}", f"{int(bat.fifties.sum()):,} fifties")], lead=True, detail=True)
if len(r) < 10:
    c.note(f"Only {len(r)} matches in {label}: the leaders below rest on very few games.")

c.section("Leaders", f"In {label}. Rates need a minimum of balls and {c.MIN_INNS} innings. Tap a name for his record.")
bs = c.bat_summary(bat, ["player_id"])
ws = c.bowl_summary(bowl, ["player_id"])
rules = c.lb_rules(eids)


def leader(lab, df, sort, asc, key, value, caption, empty_caption):
    """The first row of the Leaderboards board for this scope (same sort and minimums), the others level with him on
    the shown number, or 'not enough data'."""
    if df is None or df.empty:
        return {"label": lab, "pid": None, "caption": empty_caption}
    d = df.sort_values(sort, ascending=asc)
    t = d.iloc[0]
    tied = int((d[key] == t[key]).sum()) - 1
    return {"label": lab, "pid": int(t.player_id), "value": value(t), "caption": caption(t), "tied": tied}


q_bat = bs[bs.runs > 0] if len(bs) else bs
q_wk = ws[ws.wickets > 0] if len(ws) else ws
hs = c.best_innings(eids).copy()
hs["key"] = hs.high * 2 + hs.high_not_out.fillna(0)
q_sr = bs[(bs.balls >= rules["bf"]) & bs.sr.notna()].assign(k=lambda d: d.sr.round(1)) if len(bs) else bs
q_ec = ws[(ws.balls >= rules["bb"]) & ws.econ.notna()].assign(k=lambda d: d.econ.round(2)) if len(ws) else ws
c.leader_cards([
    leader("Most runs", q_bat, ["runs", "balls"], [False, True], "runs", lambda t: f"{int(t.runs):,}",
           lambda t: f"runs · {int(t.innings)} innings", "nobody scored a run"),
    leader("Most wickets", q_wk, ["wickets", "runs"], [False, True], "wickets", lambda t: f"{int(t.wickets)}",
           lambda t: f"wickets · {int(t.innings)} innings", "nobody took a wicket"),
    leader("Highest score", hs, ["high", "high_not_out"], [False, False], "key",
           lambda t: f"{int(t.high)}{'*' if t.high_not_out else ''}", lambda t: f"runs · {t.edition_name}", "no innings"),
    leader("Best strike rate", q_sr, ["sr", "runs"], [False, False], "k", lambda t: f"{t.sr:.1f}",
           lambda t: f"strike rate · {int(t.balls)} balls", f"nobody faced {rules['bf']} balls in {c.MIN_INNS} innings"),
    leader("Best economy", q_ec, ["econ", "wickets"], [True, False], "k", lambda t: f"{t.econ:.2f}",
           lambda t: f"economy · {t.overs} overs", f"nobody bowled {rules['bb'] // 6} overs in {c.MIN_INNS} innings"),
], comp, season)
with st.container(key="tc_see_all"):
    st.page_link("views/leaderboards.py", label="See all leaderboards")

c.section("Champions", "The winner of each edition's final.")
c.table(pd.DataFrame({"Edition": ed.edition_name, "Champion": ed.champion.fillna("No final"),
                      "Teams": ed.teams, "Matches": ed.matches}),
        {"Teams": c.col_int(), "Matches": c.col_int()}, search="champions" if len(ed) > 15 else None)
c.footer()
