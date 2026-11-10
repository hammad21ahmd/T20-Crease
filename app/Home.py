"""
Home.py - T20 Crease (Pakistan domestic T20 analytics): entry point and page router.
READ-ONLY: the pages read dom_app.sqlite only (built by export/domestic_export.py, kept outside the repo).

Sets the page config and CSS, draws the same header on every page (brand, competition + season picker), then runs
the chosen page from views/.

Run locally from the project folder (so .streamlit/config.toml is read):
  streamlit run app/Home.py
The data file is found by app/data_files.py (DOM_APP_DB, the local build, or the hosted download).
"""

import sys
from pathlib import Path

import streamlit as st

# favicon: a teal-blue tile with "TC" in white and an amber rule (app/assets/favicon.png)
st.set_page_config(page_title="T20 Crease", page_icon=str(Path(__file__).parent / "assets" / "favicon.png"),
                   layout="wide", initial_sidebar_state="collapsed")
loading = None
if "common" not in sys.modules:
    loading = st.empty()
    loading.markdown('<p style="color:#4A5E68;font-family:Georgia,serif;font-size:1.05rem;padding:2rem 0">'
                     'Loading T20 Crease...</p>', unsafe_allow_html=True)

import common as c  # noqa: E402

st.markdown(c.CSS, unsafe_allow_html=True)
_db, _problem = c.data_files.locate()
if _db is None:
    if loading is not None:
        loading.empty()
    st.markdown('<div class="tc-brand"><b>T20 <span>Crease</span></b></div>', unsafe_allow_html=True)
    c.empty("The data is not available right now.", " " + _problem)
    st.stop()

# Eight tabs, in this order (owner, 2026-11-10). Player and Compare, Records and Trends, Teams and Venues are sub-tabs.
pages = [
    st.Page("views/home.py", title="Home", default=True),
    st.Page("views/competitions.py", title="Competitions", url_path="competitions"),
    st.Page("views/leaderboards.py", title="Leaderboards", url_path="leaderboards"),
    st.Page("views/players.py", title="Players", url_path="players"),
    st.Page("views/records_trends.py", title="Records & Trends", url_path="records-trends"),
    st.Page("views/teams_venues.py", title="Teams & Venues", url_path="teams-venues"),
    st.Page("views/insights.py", title="Insights", url_path="insights"),
    st.Page("views/method.py", title="Method", url_path="method"),
]
HOST = {p.url_path: p for p in pages}


def _old_url(host, key, sub):
    """An old page's URL (/player, /compare, /records, /trends, /teams, /venues): open its sub-tab on the new page,
    with the same query parameters (?player=, ?team=, ?ground=, ?comp=, ?season=)."""
    def go():
        st.session_state[key] = sub
        st.switch_page(HOST[host], query_params={k: v for k, v in st.query_params.items() if k != "view"})
    go.__name__ = f"old_{sub.lower()}"
    return go


old = [st.Page(_old_url(h, k, s), title=s, url_path=u, visibility="hidden")
       for u, h, k, s in (("player", "players", "players_view", "Player"), ("compare", "players", "players_view", "Compare"),
                          ("records", "records-trends", "rt_view", "Records"), ("trends", "records-trends", "rt_view", "Trends"),
                          ("teams", "teams-venues", "tv_view", "Teams"), ("venues", "teams-venues", "tv_view", "Venues"))]
nav = st.navigation(pages + old, position="top")
if loading is not None:
    loading.empty()
c.header(show_scope=nav.url_path != "method")
c.widened_note()
c.mobile_nav(pages, current=nav)
c.reset_table_keys()
nav.run()
