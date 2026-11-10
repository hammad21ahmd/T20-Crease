"""
competitions.py - Competitions: Editions (editions.py: every edition's champion, results, wins and losses, leaders) and
Season recap (season_recap.py: one season in numbers) as sub-tabs (owner, 2026-11-10, feature 8).
READ-ONLY (dom_app.sqlite). Only the open sub-tab runs; ?view=season-recap opens the recap.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Competitions", "Every edition of Pakistan's domestic T20 cups, and each season in numbers.")
t_0, t_1 = c.sub_tabs(["Editions", "Season recap"], key="comp_view")
with t_0:
    if t_0.open:
        c.run_view("editions.py")
with t_1:
    if t_1.open:
        c.run_view("season_recap.py")
c.footer()
