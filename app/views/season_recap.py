"""
season_recap.py - one season in numbers: matches, runs, run rate, sixes, hundreds and fifties, ties, against the season
before; the champions; the season's leaders and records. READ-ONLY (dom_app.sqlite: results, innings, bat_edition,
bowl_edition). The Season recap sub-tab of Competitions (owner, 2026-11-10, feature 8).
The competition is the header's (all competitions when none is picked); the season is picked here (the header's season
when one is picked, else the latest). Run rate: team runs (extras included) per 6 legal balls, both innings. A season
with fewer than 10 matches is marked Small.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Season recap", "One season in numbers: scoring, champions, leaders and records, against the season before.")
comp, season, _ = c.scope()
seasons = c.seasons_for(comp)                     # newest first
if not seasons:
    c.thin(c.scope_label(comp, c.SEASON_ALL), "seasons")
    c.stop()
if st.session_state.get("recap_season") not in seasons:
    st.session_state.recap_season = season if season in seasons else seasons[0]
pick = st.selectbox("Season", seasons, key="recap_season",
                    help="The competition is the one picked at the top; the season is picked here.")
rc = c.season_recap(comp, pick)
where = pick if comp == c.COMP_ALL else f"{comp} {pick}"
c.section(f"{where} in numbers", f"{rc['matches']} matches in {rc['n_ed']} edition{'s' if rc['n_ed'] != 1 else ''}"
                                 + (f" ({c.SMALL} season: under {c.SMALL_INNS} matches)" if rc["matches"] < c.SMALL_INNS
                                    else "") + ".")
prev = rc["prev"]


def vs(now, before, nd, unit=""):
    if before is None or pd.isna(before):
        return "no season before to compare"
    d = round(round(now, nd) - round(before, nd), nd)     # the change between the numbers as shown
    return (f"{'+' if d > 0 else ''}{d:,.{nd}f}{unit} on {rc['prev_season']}" if d else f"level with {rc['prev_season']}")


c.cards([("Matches", f"{rc['matches']}", f"{rc['no_result']} no result, {rc['ties']} tied"),
         ("Runs", f"{rc['runs']:,}", "team runs, extras included"),
         ("Run rate", c.fmt(rc["rr"], 2), vs(rc["rr"], prev.get("rr"), 2)),
         ("Sixes", f"{rc['sixes']:,}", f"{c.fmt(rc['six20'], 2)} per 20 overs; " + vs(rc["six20"], prev.get("six20"), 2)),
         ("Hundreds", f"{rc['hundreds']}", f"{rc['fifties']} fifties"),
         ("Highest total", rc["top_total"], rc["top_total_note"])], lead=True, detail=True)

c.section("Champions", f"Each edition of {pick}.")
c.table(rc["champions"], {"Matches": c.col_int(), "Teams": c.col_int()})

c.section("Leaders and records", f"In {where}. The first by the stated order is named; Others level: players or sides "
                                 "with the same number.")
c.table(rc["leaders"], {"Others level": c.col_int(), "Figure": c.col_text(width="small")})
c.note(f"Most runs: then fewer balls. Most wickets: then fewer runs. Best strike rate and economy need the one-season "
       f"leaderboard minimum ({c.LB_RULES['one']['bf']} balls faced or {c.LB_RULES['one']['bb'] // 6} overs, and "
       f"{c.MIN_INNS} innings). Run rate: team runs per 6 legal balls, both innings. Against {rc['prev_season'] or 'the season before'}: "
       "the same competition choice, the season before this one.")
c.footer()
