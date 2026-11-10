"""
venues.py - the grounds: matches, first-innings par, chasing record, toss, and day against floodlit matches, for the
chosen competition and season. READ-ONLY (dom_app.sqlite results, scorecards only).
Par: the average first-innings score of first innings that lasted 20 overs or were all out, in matches without a
rain rule (DLS). Chasing and toss records count matches won or lost (ties and no results left out).
Scoring level (owner, 2026-11-09): a ground's average first-innings score divided by the average first-innings score of
the same editions (each of its matches set against its own edition's average, same par rule). 1.10: first innings
there are 10% higher than in those editions as a whole.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Venues", "Every ground: how many matches, the first-innings par, the chasing record, toss and lights.")
comp, season, eids = c.scope()
label = c.scope_label(comp, season)
r = c.in_scope(c.results(), eids).copy()
if r.empty:
    c.thin(label)
    c.stop()

r["par_ok"] = r.runs_1.notna() & ((r.balls_1 == 120) | (r.wkts_1 == 10)) & (r.dls == 0)
r["decided"] = (r.no_result == 0) & (r.tied == 0) & r.winner_id.notna()
r["chase_won"] = r.decided & (r.winner_id == r.team_2_id)
r["toss_won"] = r.decided & (r.winner_id == r.toss_winner_id)
r["lights"] = r.light.map(c.LIGHT).fillna(c.UNKNOWN)
r["ed_par"] = r.edition_id.map(r[r.par_ok].groupby("edition_id").runs_1.mean())   # each edition's own par (all grounds)
INT = c.col_int()


def summary(g):
    d, p = int(g.decided.sum()), g[g.par_ok]
    return {"Matches": len(g), "Par": round(p.runs_1.mean(), 1) if len(p) >= c.MIN_INNS else np.nan,
            "Par from": len(p), "Chasing won %": round(100 * g.chase_won.sum() / d, 1) if d >= c.MIN_INNS else np.nan,
            "Toss winner won %": round(100 * g.toss_won.sum() / d, 1) if d >= c.MIN_INNS else np.nan,
            "Decided": d, "Sample": c.SMALL if len(p) < c.SMALL_INNS else "",
            "Scoring level": round(p.runs_1.sum() / p.ed_par.sum(), 2) if len(p) >= c.MIN_INNS else np.nan}


rows = [{"Ground": g_, **summary(g), "Under lights": int(g.lights.isin(["Day-night", "Night"]).sum())}
        for g_, g in r.groupby("ground")]
t = pd.DataFrame(rows).sort_values(["Matches", "Ground"], ascending=[False, True])
allr = summary(r)
c.cards([("Grounds", f"{len(t)}", f"in {label}"),
         ("Par score", c.fmt(allr["Par"], 1), f"average first innings, {allr['Par from']} matches"),
         ("Chasing side won", c.fmt(allr["Chasing won %"], 1) + "%" if pd.notna(allr["Chasing won %"]) else "-",
          f"of {allr['Decided']} matches won or lost"),
         ("Toss winner won", c.fmt(allr["Toss winner won %"], 1) + "%" if pd.notna(allr["Toss winner won %"]) else "-",
          f"of {allr['Decided']} matches won or lost")], lead=True, detail=True)

c.section("Grounds", f"In {label}, most matches first.")
c.bar_chart(t, "Ground", "Matches", title="Matches")
cfg = {"Matches": INT, "Par": c.col_1(help="Average first-innings score: first innings of 20 overs or all out, no "
                                           "rain rule. Blank under 5 such innings."),
       "Par from": INT, "Chasing won %": c.col_1(help="Matches won by the side batting second, of matches won or lost."),
       "Toss winner won %": c.col_1(), "Decided": INT, "Under lights": INT, "Sample": c.col_text(width="small"),
       "Scoring level": c.col_2(help="The ground's average first-innings score divided by the average first-innings "
                                     "score of the same editions. Above 1: higher scoring than usual. Blank under 5.")}
c.table(t[["Ground", "Matches", "Par", "Par from", "Scoring level", "Chasing won %", "Toss winner won %", "Decided",
           "Under lights", "Sample"]], cfg)
c.note("Par from: the first innings it is based on. Decided: matches won or lost (ties and no results left out). "
       "Rates are blank under 5 matches; Small: par from fewer than 10 innings. Scoring level 1.10: first innings at "
       "this ground were 10% higher than in the same editions as a whole.")

c.section("One ground")
opts = list(t.Ground)
want = st.query_params.get("ground", "")
by_slug = {c.slug(g): g for g in opts}
if st.session_state.get("venue_pick") not in opts:
    st.session_state.venue_pick = by_slug.get(want, opts[0])
g_ = st.selectbox("Ground", opts, key="venue_pick")
c.link_set(ground=c.slug(g_))
g = r[r.ground == g_]
s = summary(g)
c.cards([("Matches", f"{len(g)}", f"{c.date_fmt(g.date.min())} to {c.date_fmt(g.date.max())}"),
         ("Par score", c.fmt(s["Par"], 1), f"from {s['Par from']} first innings" +
          (f", {c.SMALL} sample" if s["Par from"] < c.SMALL_INNS else "") if pd.notna(s["Par"]) else "not enough innings"),
         ("Chasing side won", c.fmt(s["Chasing won %"], 1) + "%" if pd.notna(s["Chasing won %"]) else "-",
          f"of {s['Decided']} matches won or lost"),
         ("Toss winner chose to field", f"{int((g.toss_choice == 'bowl').sum())}", f"of {len(g)} tosses")], detail=True)
if len(g) < 10:
    c.note(f"Only {len(g)} matches at this ground in {label}: read its rates with care.")

# ---- ground profile (owner, 2026-11-09): scoring level, chase and defend, toss effect
c.section("Ground profile", f"{g_} in {label}.")
lvl = s["Scoring level"]
if pd.notna(lvl):
    diff = round(100 * (lvl - 1))
    lvl_note = (f"{abs(diff)}% {'above' if diff > 0 else 'below'} the same editions' first innings" if diff else
                "level with the same editions' first innings") + f", {s['Par from']} innings"
    lvl_note += f", {c.SMALL} sample" if s["Par from"] < c.SMALL_INNS else ""
else:
    lvl_note = f"not enough first innings ({s['Par from']} of {c.MIN_INNS})"
dec = g[g.decided]
first_won = int((dec.winner_id == dec.team_1_id).sum())
c.cards([("Scoring level", f"{lvl:.2f}" if pd.notna(lvl) else "-", lvl_note),
         ("Side batting first won", f"{first_won}", f"of {len(dec)} matches won or lost"),
         ("Side batting second won", f"{len(dec) - first_won}", f"of {len(dec)} matches won or lost"),
         ("Toss winner won", f"{int(dec.toss_won.sum())}", f"of {len(dec)} matches won or lost")], detail=True)
rows = []
for k_, lab_ in (("bat", "Chose to bat"), ("bowl", "Chose to field")):
    x_ = dec[dec.toss_choice == k_]
    w_ = int(x_.toss_won.sum())
    rows.append({"Toss winner": lab_, "Decided": len(x_), "Toss winner won": w_, "Toss winner lost": len(x_) - w_,
                 "Won %": round(100 * w_ / len(x_), 1) if len(x_) >= c.MIN_INNS else np.nan,
                 "Sample": c.NOT_ENOUGH if len(x_) < c.MIN_INNS else (c.SMALL if len(x_) < c.SMALL_INNS else "")})
c.table(pd.DataFrame(rows), {"Decided": INT, "Toss winner won": INT, "Toss winner lost": INT, "Won %": c.col_1(),
                             "Sample": c.col_text(width="small")})
c.note("Matches won or lost only (ties and no results left out). Won % is blank under 5 matches and Small under 10.")

c.section("Day and floodlit", "The same records for day matches and matches under lights (day-night or night).")
lt = pd.DataFrame([{"Light": k, **summary(x)} for k, x in g.groupby("lights")])
order = {"Day": 0, "Day-night": 1, "Night": 2, c.UNKNOWN: 3}
lt = lt.sort_values("Light", key=lambda s_: s_.map(order))
c.table(lt[["Light", "Matches", "Par", "Par from", "Chasing won %", "Toss winner won %", "Decided"]], cfg)
c.note("Unknown: the source does not say whether the match was played under lights.")

c.section("Matches at this ground", "Newest first.")
mm = g.sort_values(["date", "p_match"], ascending=False)
c.table(pd.DataFrame({"Date": mm.date.map(c.date_fmt), "Edition": mm.edition_name, "Match": mm.team_1 + " v " + mm.team_2,
                      "Scores": mm.score_1.fillna("-") + " v " + mm.score_2.fillna("-"), "Result": mm.result}),
        {"Match": c.col_text(width="large"), "Result": c.col_text(width="large")},
        search="venue_matches" if len(mm) > 15 else None)
c.footer()
