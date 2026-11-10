"""
records_trends.py - Records & Trends: records.py and trends.py as sub-tabs (owner, 2026-11-10: eight tabs).
READ-ONLY (dom_app.sqlite).
Only the open sub-tab runs; the old URLs (records, trends) open the matching sub-tab (app/Home.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Records & Trends", "Record lists, and how scoring changed season by season.")
t_0, t_1 = c.sub_tabs(["Records", "Trends"], key="rt_view")
with t_0:
    if t_0.open:
        c.run_view("records.py")
with t_1:
    if t_1.open:
        c.run_view("trends.py")
c.footer()
