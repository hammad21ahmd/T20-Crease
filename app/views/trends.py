"""
trends.py - how scoring changed: runs per over and sixes per 20 overs season by season (every season of the chosen
competition, whatever season is picked), and which competition scores fastest in the chosen season.
READ-ONLY (dom_app.sqlite innings, bat_edition, results; scorecards only).
Run rate: team runs (extras included) per 6 legal balls, both innings. Sixes per 20 overs: sixes hit per 120 legal
balls. A season or competition with fewer than 10 matches is marked Small.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Trends", "How fast sides score and how often they hit sixes, season by season, and which competition scores "
                 "fastest.")
comp, season, eids = c.scope()
comp_label = c.scope_label(comp, c.SEASON_ALL)
e_all = c.editions()
e_all = e_all if comp == c.COMP_ALL else e_all[e_all.competition == comp]


def rates(eids_, by):
    """Matches, runs, legal balls and sixes by `by` (season or competition) for the editions."""
    inn = c.in_scope(c.innings_table(), eids_).merge(c.editions()[["edition_id", "season", "competition", "first_date"]],
                                                     on="edition_id")
    six = c.in_scope(c.bat_edition(), eids_).groupby("edition_id").sixes.sum()
    g = inn.groupby(by).agg(first=("first_date", "min"), Matches=("p_match", "nunique"), runs=("runs", "sum"),
                            balls=("balls", "sum"), eds=("edition_id", lambda s: tuple(sorted(set(s)))))
    g["sixes"] = [int(six.reindex(list(e)).fillna(0).sum()) for e in g.eds]
    g["Run rate"] = (6 * g.runs / g.balls).round(2)
    g["Sixes per 20 overs"] = (120 * g.sixes / g.balls).round(2)
    g["Sample"] = [c.SMALL if m < c.SMALL_INNS else "" for m in g.Matches]
    return g.sort_values("first").reset_index()


CFG = {"Matches": c.col_int(), "Run rate": c.col_2(help="Team runs, extras included, per 6 legal balls (both innings)."),
       "Sixes per 20 overs": c.col_2(help="Sixes hit per 120 legal balls."), "Sixes": c.col_int(),
       "Sample": c.col_text(width="small")}

t = rates(tuple(int(x) for x in e_all.edition_id), "season").rename(columns={"season": "Season", "sixes": "Sixes"})
c.section("Scoring rate by season", f"{comp_label[0].upper() + comp_label[1:]}: every season, whatever season is picked "
                                    "at the top.")
if len(t) < 2:
    c.note("This competition has one season only, so there is no trend to show.")
else:
    c.trend_chart(t, "Season", "Run rate", fmt=",.2f", title="Runs per over")
    c.section("Sixes by season")
    c.trend_chart(t, "Season", "Sixes per 20 overs", fmt=",.2f", title="Sixes per 20 overs")
c.table(t[["Season", "Matches", "Run rate", "Sixes", "Sixes per 20 overs", "Sample"]], CFG,
        search="trends" if len(t) > 15 else None)
c.note("Both innings of every match. Small (hollow amber point): a season with fewer than 10 matches, so its rate can "
       "swing on a few games.")

e_cmp = c.editions() if season == c.SEASON_ALL else c.editions()[c.editions().season == season]
cp = rates(tuple(int(x) for x in e_cmp.edition_id), "competition")
cp = cp.rename(columns={"competition": "Competition", "sixes": "Sixes"}).sort_values(["Run rate", "Matches"],
                                                                                      ascending=[False, False])
c.section("Which competition scores fastest",
          f"Every competition, {season if season != c.SEASON_ALL else 'all seasons'}, fastest first.")
if len(cp) < 2:
    c.note(f"Only one competition was played in {season}. Pick All seasons at the top to compare every competition.")
cp["bar"] = [f"{v:.2f}" + (f" ({c.SMALL})" if smp == c.SMALL else "") for v, smp in zip(cp["Run rate"], cp.Sample)]
c.bar_chart(cp, "Competition", "Run rate", fmt=",.2f", title="Runs per over", text="bar")
c.table(cp[["Competition", "Matches", "Run rate", "Sixes", "Sixes per 20 overs", "Sample"]], CFG)
c.note("Small: fewer than 10 matches. Competitions were played in different years, on different grounds and with different sides: a gap between "
       "them is not only the standard of play. The competition picked at the top does not narrow this list.")
c.footer()
