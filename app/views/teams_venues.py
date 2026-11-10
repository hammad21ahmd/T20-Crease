"""
teams_venues.py - Teams & Venues: teams.py, venues.py and h2h.py (head to head) as sub-tabs (owner, 2026-11-10: eight tabs).
READ-ONLY (dom_app.sqlite).
Only the open sub-tab runs; the old URLs (teams, venues) open the matching sub-tab (app/Home.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Teams & Venues", "One side's record, every ground, and every team against every other.")
t_0, t_1, t_2 = c.sub_tabs(["Teams", "Venues", "Head to head"], key="tv_view")
with t_0:
    if t_0.open:
        c.run_view("teams.py")
with t_1:
    if t_1.open:
        c.run_view("venues.py")
with t_2:
    if t_2.open:
        c.run_view("h2h.py")
c.footer()
