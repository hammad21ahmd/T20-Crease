"""
h2h.py - every team against every other in the chosen competition and season: a heatmap of the row team's win % against
each opponent, with the wins and losses in each cell, and the same grid as a table. READ-ONLY (dom_app.sqlite results).
Shown as the Head to head sub-tab of Teams & Venues (owner, 2026-11-10, feature 6).
Teams are kept by team ID (spelling variants are one team, eras are not linked). Win %: of matches won or lost (ties
and no results left out), blank under 5 such matches, Small under 10. Teams with the most matches first.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Head to head", "Every side against every other: the row team's wins and losses against each opponent.")
comp, season, eids = c.scope()
label = c.scope_label(comp, season)
h = c.h2h_pairs(eids)
if h.empty:
    c.thin(label)
    c.stop()

order = c.h2h_order(eids)
SHOW = {"Top 8": 8, "Top 12": 12, "All": len(order)}
st.session_state.setdefault("h2h_n", "Top 12" if len(order) > 12 else "All")
if len(order) > 8:
    pick = st.segmented_control("Teams shown", list(SHOW), key="h2h_n", required=True,
                                help="Teams with the most matches in the chosen competition and season first.")
    n = SHOW[pick]
else:
    n = len(order)
teams = order[:n]
d = h[h.Team.isin(teams) & h.Opponent.isin(teams)].reset_index(drop=True)
if d.empty:
    c.thin(label, "matches between these sides")
    c.stop()

c.section("Win % against each opponent", f"In {label}: {len(teams)} of {len(order)} teams, most matches first. "
                                          "Read across: the row team's wins and losses against the column team.")
c.h2h_heatmap(d, teams)
grid = c.h2h_grid(d, teams)
c.table(grid, {k: c.col_text(width="small") for k in grid.columns if k != "Team"})
c.note(f"Each cell: wins-losses of the row team against the column team; '-' they did not meet. Colour: win % of "
       f"matches won or lost (ties and no results left out); grey when fewer than {c.MIN_INNS} matches were won or "
       f"lost, and an amber dashed border marks a {c.SMALL} sample (under {c.SMALL_INNS}). Hover a cell for the counts.")
if n < len(order):
    c.note(f"{len(order) - n} more teams played in {label}; choose All to see them.")
c.footer()
