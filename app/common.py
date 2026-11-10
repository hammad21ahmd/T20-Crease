"""
common.py - shared code for T20 Crease (Pakistan domestic T20 analytics): theme, header, menu, cards, tables with
phone copies, number formats, lazy tabs, footer link.

READ-ONLY: opens dom_app.sqlite in read-only mode (built by export/domestic_export.py; found by data_files.py, which
downloads it on the hosted app). No MySQL, no writes. The app file has no birth date and no raw Cricinfo text; this code shows the birth year only.
Data rules (CLAUDE.md): players by Cricinfo player_id with the shared-name rule built into players.name;
rates are blank under 5 innings and marked Small under 10; leaderboards of rates need a minimum of balls.
Ball-by-ball views are not part of this version: every number comes from the scorecards.
Session 3: Teams, Venues, Compare, entry, dismissals and fielding; fielding numbers only where at least
FIELD_MIN_COVER % of fielders are known.
"""

import html
import re
import sqlite3
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import data_files  # noqa: E402  (where the data file is: local, or downloaded on the hosted app)
BRAND = "T20 Crease"
TAGLINE = "Pakistan domestic T20 analytics"
MAX_ROWS = 50
FOOTER = "T20 Crease | Pakistan domestic T20 analytics | Analysis by Hammad"
# Every page ends with this link to the Method tab, which lists every source (owner's decision 2026-11-09:
# no per-page ESPNcricinfo line and no extra line above the footer).
METHOD_LINK = "Data sources and method"
COMP_ALL, SEASON_ALL = "All competitions", "All seasons"
MIN_INNS, SMALL_INNS = 5, 10          # rates blank under 5 innings, marked Small under 10
SMALL = "Small"
NOT_ENOUGH = "not enough"
UNKNOWN = "Unknown"

# ---- Colours (owner, 2026-11-09): blue and white. White page, cool pale grey-blue cards and tables, one teal-blue
# primary (links, headings, active page pill, charts), one amber accent (card accent bars and the Small badge only).
# Kept clearly apart from the PSL app (royal blue on a filled navy header): teal-blue, white header, serif titles.
# Text colours are at least 4.5:1 on every ground they sit on (checked by tests/app_checks.py).
BLUE = "#0E7490"               # primary: links, headings, active menu pill and tab, chart bars
BLUE_SOFT = "#E0F1F6"          # hover ground for menu pills
AMBER = "#CF6F05"              # the one accent: card accent bars, Small badge border, second chart series
BADGE_BG, BADGE_INK = "#FEF3C7", "#8A3B0C"   # the Small badge: pale amber ground, dark amber text
PAGE_BG, SURFACE, SURFACE_2, BORDER = "#FFFFFF", "#F4F8FA", "#E4EEF2", "#CBDCE3"
INK, MUTED = "#13242C", "#4A5E68"
SERIF = 'Georgia, "Iowan Old Style", "Times New Roman", serif'
ACCENT = BLUE                  # kept for code that asks for the UI accent
CHART_BG = SURFACE
CHART_GREY = "#8A9BA3"         # neutral grey for chart rules

HELP = {
    "SR": "Strike rate: runs per 100 balls faced.",
    "Avg": "Batting average: runs per dismissal. Blank under 5 innings.",
    "Econ": "Economy: runs conceded per over (as the scorecard credits them to the bowler).",
    "Bowl avg": "Bowling average: runs conceded per wicket. Blank under 5 innings.",
    "Bowl SR": "Balls bowled per wicket. Blank under 5 innings.",
    "Sample": "Small: fewer than 10 innings, read the rates with care. Rates are blank under 5 innings.",
    "HS": "Highest score; * not out.",
    "Best": "Best bowling in one innings: wickets/runs.",
    "Teams": "Latest team first.",
}

CSS = f"""
<style>
/* ---- frame: hide Streamlit chrome (menu, toolbar, deploy, footer, badges) and the dataframe toolbar ---- */
#MainMenu, footer, [data-testid="stMainMenu"], [data-testid="stAppDeployButton"],
[data-testid="stToolbarActions"], [data-testid="stDecoration"], [class*="viewerBadge"],
[data-testid="stStatusWidget"] a {{ display: none !important; }}
[data-testid="stElementToolbar"], [data-testid="stElementToolbarButton"] {{ display: none !important; }}

.stApp {{ background: {PAGE_BG}; color: {INK}; font-variant-numeric: tabular-nums; }}
/* header: a white bar with a blue underline */
[data-testid="stHeader"] {{ background: #FFFFFF; border-bottom: 3px solid {BLUE}; }}
.block-container {{ max-width: 1080px; padding: 4.5rem 1.5rem 3rem 1.5rem !important; }}
h1, h2, h3 {{ color: {BLUE}; font-family: {SERIF}; }}
a {{ color: {BLUE}; }}

/* ---- top menu: blue words on white; the open page is a blue pill ---- */
[data-testid="stTopNav"] {{ gap: .15rem; }}
[data-testid="stTopNavLink"] {{ background: transparent !important; border-radius: 999px; }}
[data-testid="stTopNavLink"] * {{ color: {BLUE} !important; font-weight: 600; }}
[data-testid="stTopNavLink"]:hover {{ background: {BLUE_SOFT} !important; }}
[data-testid="stTopNavLink"][aria-current="page"] {{ background: {BLUE} !important; }}
[data-testid="stTopNavLink"][aria-current="page"] * {{ color: #FFFFFF !important; }}

/* ---- widget labels and tabs ---- */
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] * {{ color: {INK} !important; }}
[data-testid="stTab"] p, [data-testid="stTab"] {{ color: {MUTED} !important; }}
[data-testid="stTab"][aria-selected="true"] p, [data-testid="stTab"][aria-selected="true"] {{ color: {BLUE} !important;
    font-weight: 700; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {BLUE} !important; height: 3px; }}
.stTabs [data-baseweb="tab-border"] {{ background-color: {BORDER} !important; }}

/* ---- brand (every page): serif name, tagline, the crease line ---- */
.tc-brand {{ display: flex; align-items: baseline; gap: .7rem; flex-wrap: wrap; margin: .2rem 0 0 0; }}
.tc-brand b {{ font-family: {SERIF}; font-size: 1.55rem; font-weight: 700; color: {BLUE}; letter-spacing: -0.01em; }}
.tc-brand b span {{ color: {INK}; }}
.tc-brand i {{ font-style: normal; color: {MUTED}; font-size: .9rem; }}
.tc-crease {{ width: 3.2rem; height: 3px; background: {BLUE}; margin: .25rem 0 0 0; }}
.tc-rule {{ border: 0; border-top: 1px solid {BORDER}; margin: .7rem 0 1.5rem 0; }}

/* ---- page title ---- */
[data-testid="stMarkdownContainer"] p.tc-title, .tc-title {{ font-family: {SERIF}; font-size: 1.75rem; font-weight: 700;
    color: {BLUE}; margin: 0 0 .25rem 0; line-height: 1.2; }}
.tc-sub {{ color: {MUTED}; font-size: 1rem; margin: 0 0 1.25rem 0; }}
[data-testid="stMarkdownContainer"] p.tc-section, .tc-section {{ font-family: {SERIF}; font-size: 1.15rem; font-weight: 700;
    color: {BLUE}; margin: 2rem 0 .25rem 0; }}
.tc-section-help {{ color: {MUTED}; font-size: .88rem; margin: 0 0 .75rem 0; }}

/* ---- cards: pale cool ground, the amber accent bar on the left ---- */
.tc-cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: .7rem; margin: .25rem 0 1rem 0; }}
.tc-card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-left: 4px solid {AMBER}; border-radius: 3px;
            padding: .8rem .95rem; min-width: 0; }}
.tc-card-label {{ color: {MUTED}; font-size: .78rem; font-weight: 600; overflow-wrap: anywhere; }}
.tc-card-value {{ color: {INK}; font-size: 1.6rem; font-weight: 700; line-height: 1.2; margin-top: .15rem;
                  font-variant-numeric: tabular-nums; white-space: nowrap; }}
.tc-card-value.text {{ font-size: 1.1rem; line-height: 1.35; white-space: normal; overflow-wrap: break-word; }}
.tc-card-detail {{ color: {MUTED}; font-size: .8rem; margin-top: .15rem; overflow-wrap: break-word; }}
.tc-card-sub {{ color: {BLUE}; font-size: .9rem; font-weight: 700; margin-top: .15rem; line-height: 1.3;
                overflow-wrap: break-word; }}

/* ---- leader cards: label, name (link), number, tie note, caption; equal heights, caption at the foot ---- */
.tc-cards.tc-leaders {{ grid-auto-rows: 1fr; }}
.tc-lcard {{ display: flex; flex-direction: column; }}
.tc-lcard .tc-card-value {{ margin-top: .1rem; }}
/* label, name and the small second line each take exactly one line, so the numbers line up in every card */
.tc-lcard .tc-card-label {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; height: 1.3em; line-height: 1.3; }}
.tc-lcard .tc-card-name {{ display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; height: 1.3em;
                           overflow-wrap: normal; }}
.tc-card-who2 {{ color: {MUTED}; font-size: .75rem; line-height: 1.3; height: 1.3em; white-space: nowrap; overflow: hidden;
                 text-overflow: ellipsis; }}
.tc-card-name {{ color: {BLUE} !important; font-weight: 700; font-size: .98rem; line-height: 1.3; margin-top: .2rem;
                 text-decoration: none; overflow-wrap: anywhere; }}
a.tc-card-name:hover {{ text-decoration: underline; }}
.tc-card-name.none {{ color: {MUTED} !important; font-weight: 600; font-style: italic; }}
.tc-card-tie {{ color: {MUTED}; font-size: .75rem; font-weight: 700; }}
.tc-lcard .tc-card-detail {{ margin-top: auto; padding-top: .2rem; }}
/* ---- text blocks ---- */
.tc-note {{ color: {MUTED}; font-size: .84rem; margin: .35rem 0 .9rem 0; }}
.tc-lede {{ font-family: {SERIF}; font-size: 1.25rem; color: {INK}; margin: 0 0 .3rem 0; }}
.tc-meta {{ color: {MUTED}; font-size: .92rem; margin: 0 0 .6rem 0; }}
.tc-empty {{ background: {SURFACE}; border: 1px solid {BORDER}; border-left: 4px solid {MUTED}; border-radius: 3px;
             padding: 1.1rem 1.2rem; color: {MUTED}; margin: .5rem 0 1rem 0; }}
.tc-empty b {{ color: {INK}; display: block; margin-bottom: .2rem; }}
.tc-team {{ display: inline-block; background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 3px;
            padding: .05rem .45rem; font-size: .78rem; color: {INK}; margin: 0 .3rem .3rem 0; cursor: default; }}
.tc-teams {{ display: inline-block; }}
.tc-teams .tc-team:first-child {{ border-color: {BLUE}; color: {BLUE}; font-weight: 700; }}

/* ---- Small badge (thin samples) ---- */
.tc-badge {{ display: inline-block; background: {BADGE_BG}; color: {BADGE_INK}; border: 1px solid {AMBER}; border-radius: 3px;
             padding: 0 .35rem; font-size: .72rem; font-weight: 700; line-height: 1.45; letter-spacing: .02em; }}
/* ---- "See all" and other in-page links ---- */
.st-key-tc_see_all [data-testid="stPageLink-NavLink"] {{ padding: .2rem 0; min-height: 0; }}
.st-key-tc_see_all [data-testid="stPageLink-NavLink"] p {{ color: {BLUE}; font-weight: 700; text-decoration: underline; }}
/* ---- charts sit on the warm white surface, like the tables ---- */
[data-testid="stVegaLiteChart"] {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 3px; padding: 0;
                                   box-sizing: border-box; overflow: hidden; }}
.tc-loading {{ color: {MUTED}; font-family: {SERIF}; font-size: 1.05rem; padding: 2rem 0; }}

/* ---- tables: pale cool grid, grey-blue header ---- */
[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 3px; overflow: hidden; background: {SURFACE}; }}
.stTabs [data-baseweb="tab-list"] {{ gap: .2rem; overflow-x: auto; }}
.stTabs [data-baseweb="tab"] {{ padding: .45rem .75rem; }}

/* ---- phone copy of every table (common.phone_table): hidden on desktop, with its element box so the
   desktop page keeps its spacing; at 640 px or less it replaces the grid ---- */
[data-testid="stElementContainer"]:has(.tc-mtable) {{ display: none !important; }}
.tc-mtable table {{ width: 100%; border-collapse: separate; border-spacing: 0; background: {SURFACE};
                    border: 1px solid {BORDER}; border-radius: 3px; overflow: hidden; table-layout: auto; }}
.tc-mtable th, .tc-mtable td {{ padding: .35rem .28rem; border-bottom: 1px solid {BORDER}; font-size: .78rem;
                                line-height: 1.3; vertical-align: top; overflow-wrap: break-word; }}
.tc-mtable th {{ color: {INK}; font-weight: 600; background: {SURFACE_2}; position: sticky; top: 0; z-index: 1; }}
.tc-mtable td {{ color: {INK}; font-variant-numeric: tabular-nums; }}
.tc-mtable .n {{ text-align: right; }}
.tc-mtable .t {{ text-align: left; }}
.tc-mtable tr:last-child td {{ border-bottom: 0; }}
.tc-mcard {{ background: {SURFACE}; border: 1px solid {BORDER}; border-left: 3px solid {BLUE}; border-radius: 3px;
             padding: .45rem .6rem; margin: 0 0 .4rem 0; }}
.tc-mcard > p {{ margin: 0 0 .25rem 0; font-weight: 700; font-size: .88rem; color: {INK}; overflow-wrap: break-word; }}
.tc-mpairs {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); gap: .15rem .5rem; }}
.tc-mpairs > div {{ display: flex; justify-content: space-between; gap: .3rem; font-size: .78rem; min-width: 0;
                    border-bottom: 1px dotted {BORDER}; }}
.tc-mpairs span {{ color: {MUTED}; min-width: 0; overflow-wrap: break-word; }}
.tc-mpairs b {{ color: {INK}; font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }}
.tc-mpairs > div.w {{ grid-column: 1 / -1; }}
.tc-mpairs > div.w b {{ white-space: normal; overflow-wrap: break-word; min-width: 0; margin-left: .6rem; }}
/* ---- desktop wrapping table (common.html_table): shown by the table's own container query only when the
   grid would not fit its box (wider than 640 px); headers and text wrap, numbers stay on one line ---- */
[class*="st-key-tc_tbl_"] {{ container-type: inline-size; }}
[data-testid="stElementContainer"]:has(.tc-dtable) {{ display: none; }}
.tc-dtable {{ overflow-x: auto; }}
.tc-dtable table {{ width: 100%; border-collapse: separate; border-spacing: 0; background: {SURFACE};
                    border: 1px solid {BORDER}; border-radius: 3px; table-layout: auto; }}
.tc-dtable th, .tc-dtable td {{ padding: .4rem .5rem; border-bottom: 1px solid {BORDER}; font-size: .875rem;
                                line-height: 1.35; vertical-align: top; }}
.tc-dtable th {{ color: {INK}; font-weight: 600; background: {SURFACE_2}; overflow-wrap: normal; position: sticky; top: 0;
                 z-index: 1; }}
.tc-dtable th[title] {{ cursor: help; }}
.tc-dtable td {{ color: {INK}; font-variant-numeric: tabular-nums; }}
.tc-dtable td.n {{ text-align: right; white-space: nowrap; }}
.tc-dtable th.n {{ text-align: right; }}
.tc-dtable .t {{ text-align: left; overflow-wrap: break-word; }}
.tc-dtable td.s {{ white-space: nowrap; }}
.tc-dtable tr:last-child td {{ border-bottom: 0; }}
@media (max-width: 640px) {{
  [data-testid="stElementContainer"]:has(.tc-mtable) {{ display: block !important; }}
  [data-testid="stElementContainer"]:has([data-testid="stDataFrame"]) {{ display: none !important; }}
  [data-testid="stElementContainer"]:has(.tc-dtable) {{ display: none !important; }}
}}

/* ---- data confidence meter (top of Insights only, owner 2026-11-10): four small bars ---- */
.tc-conf {{ display: flex; flex-wrap: wrap; align-items: center; gap: .3rem 1.1rem; margin: 0 0 1.1rem 0;
            font-size: .75rem; color: {MUTED}; }}
.tc-conf-h {{ font-weight: 700; color: {INK}; }}
.tc-conf-i {{ display: flex; align-items: center; gap: .35rem; cursor: help; min-width: 0; }}
.tc-conf-l {{ white-space: nowrap; }}
.tc-conf-bar {{ display: inline-block; width: 46px; height: 6px; background: {SURFACE_2}; border: 1px solid {BORDER};
                border-radius: 999px; overflow: hidden; flex: none; }}
.tc-conf-bar i {{ display: block; height: 100%; background: {BLUE}; }}
.tc-conf-i b {{ color: {INK}; font-weight: 700; font-variant-numeric: tabular-nums; min-width: 2.2em; }}
@media (max-width: 640px) {{
  .tc-conf {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0 0 1rem 0; gap: .3rem .6rem; }}
  .tc-conf-h {{ grid-column: 1 / -1; }}
  .tc-conf-i {{ justify-content: space-between; }}
  .tc-conf-l {{ overflow: hidden; text-overflow: ellipsis; }}
}}

/* ---- footer ---- */
.tc-footer {{ color: {MUTED}; font-size: .85rem; border-top: 3px solid {BLUE}; margin-top: 3rem; padding-top: .9rem; }}
.tc-footer-credit {{ display: block; color: {INK}; font-family: {SERIF}; }}
.st-key-tc_footer_link [data-testid="stPageLink-NavLink"] {{ padding: 0; min-height: 0; }}
.st-key-tc_footer_link [data-testid="stPageLink-NavLink"] p {{ color: {BLUE}; font-size: .85rem; text-decoration: underline; }}

/* ---- phone first ---- */
@media (max-width: 640px) {{
  .block-container {{ padding: 4rem .9rem 2.5rem .9rem !important; }}
  .tc-brand b {{ font-size: 1.35rem; }}
  [data-testid="stMarkdownContainer"] p.tc-title, .tc-title {{ font-size: 1.35rem; }}
  .tc-cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem; }}
  .tc-card {{ padding: .65rem .7rem; }}
  .tc-card-value {{ font-size: 1.3rem; }}
  .tc-card-value.text {{ font-size: .98rem; }}
  .tc-section {{ margin-top: 1.6rem; }}
  .stTabs [role="tablist"] {{ gap: 0; }}
  .stTabs [role="tab"] {{ padding: .4rem .3rem; }}
  .stTabs [role="tab"] p {{ font-size: .84rem; }}
}}
@media (max-width: 640px) {{
  /* Leaderboards' eight tabs: two rows of four on a phone instead of a bar that scrolls sideways */
  .st-key-tc_lb_tabs [role="tablist"] {{ display: grid; grid-template-columns: repeat(4, auto); overflow-x: visible;
                                         row-gap: .1rem; }}
  .st-key-tc_lb_tabs [role="tab"] {{ justify-content: center; }}
  /* Player and Teams: six or seven tabs, three to a row */
  .st-key-tc_player_tabs [role="tablist"], .st-key-tc_team_tabs [role="tablist"], .st-key-tc_rec_tabs [role="tablist"] {{
        display: grid; grid-template-columns: repeat(3, auto); overflow-x: visible; row-gap: .1rem; }}
  .st-key-tc_player_tabs [role="tab"], .st-key-tc_team_tabs [role="tab"], .st-key-tc_rec_tabs [role="tab"] {{
        justify-content: center; }}
}}
@media (max-width: 380px) {{
  .stTabs [role="tab"] {{ padding: .4rem .2rem; }}
  .stTabs [role="tab"] p {{ font-size: .78rem; }}
}}
/* ---- phone menu: rows of page pills under the brand (hidden on desktop, where the top menu shows) ---- */
.st-key-tc_mobile_nav, [data-testid="stLayoutWrapper"]:has(> .st-key-tc_mobile_nav) {{ display: none !important; }}
@media (max-width: 768px) {{
  /* phone: the header is folded to its blue line; the page starts just below it */
  [data-testid="stHeader"] {{ height: 4px !important; min-height: 0 !important; overflow: hidden;
                              background: {BLUE} !important; border: 0; }}
  .block-container {{ padding-top: 1.25rem !important; }}
  [data-testid="stLayoutWrapper"]:has(> .st-key-tc_mobile_nav) {{ display: block !important; }}
  .st-key-tc_mobile_nav {{ display: grid !important; grid-template-columns: repeat(3, minmax(0, 1fr));
                           gap: .3rem !important; margin: 0 0 1rem 0; padding: 0; overflow: visible; border: 0; }}
  .st-key-tc_mobile_nav > div {{ width: auto !important; min-width: 0 !important; margin: 0 !important; }}
  .st-key-tc_mobile_nav > div:has(style) {{ display: none !important; }}
  .st-key-tc_mobile_nav [data-testid="stPageLink"] {{ width: 100%; }}
  .st-key-tc_mobile_nav [data-testid="stPageLink-NavLink"] {{ background: {SURFACE}; border-radius: 999px;
        border: 1px solid {BORDER};
        padding: .35rem .2rem; min-height: 2.2rem; white-space: nowrap; width: 100%; justify-content: center; margin: 0; }}
  .st-key-tc_mobile_nav [data-testid="stPageLink-NavLink"] p {{ color: {BLUE}; font-size: .84rem; font-weight: 600;
        white-space: nowrap; }}
  .tc-rule {{ margin: .4rem 0 .6rem 0 !important; }}
  /* scope: competition and season dropdowns side by side, each half the width */
  .st-key-tc_scope_bar {{ flex-wrap: wrap !important; row-gap: .4rem !important; }}
  .st-key-tc_scope_bar > div {{ flex: 1 1 0 !important; min-width: 0 !important; width: auto !important; }}
  .st-key-tc_scope_bar > div:has(.st-key-tc_gsearch), .st-key-tc_scope_bar > .st-key-tc_gsearch {{
        flex: 1 1 100% !important; }}
  /* the side menu behind the ">>" button is replaced by the page tabs above */
  [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"],
  [data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
}}
</style>
"""


# ---- tables: printf formats in column_config become Python formats with thousands separators
_PY_FMT = {"%d": "{:,.0f}", "%.1f": "{:,.1f}", "%.2f": "{:,.2f}", "%.1f%%": "{:,.1f}%", "%+.2f": "{:+,.2f}"}


def table(df, column_config=None, title=None, search=None, **kwargs):
    """search="key": a search box over the text columns (long tables). st.dataframe with protection (at most MAX_ROWS rows, toolbar hidden by CSS, no index) and
    the house number formats: thousands separators; RAA columns without decimals once any value
    reaches 100; Season and # without separators. Values stay numbers, so they sort and align right."""
    if search:
        q = st.text_input("Search", key=f"tc_search_{search}", placeholder="Type a name, team, edition or ground",
                          label_visibility="collapsed").strip().lower()
        if q:
            text_cols = [col for col in df.columns
                         if df[col].dtype == object or pd.api.types.is_string_dtype(df[col])]
            hit = pd.Series(False, index=df.index)
            for col in text_cols:
                hit |= df[col].astype(str).str.lower().str.contains(q, regex=False)
            df = df[hit]
            if df.empty:
                empty(f'Nothing matches "{q}".', " Clear the search box to see every row.")
                return
    n = len(df)
    if n > MAX_ROWS:
        df = df.head(MAX_ROWS)
    kwargs.setdefault("width", "stretch")
    kwargs.setdefault("hide_index", True)
    cfg = dict(column_config or {})
    fmts = {}
    for col, conf in list(cfg.items()):
        f = (conf or {}).get("type_config", {}).get("format") if isinstance(conf, dict) else None
        if not f or col not in df.columns:
            continue
        if col in ("Season", "#"):
            fmts[col] = "{:.0f}"
        elif f == "%+.1f":
            big = pd.to_numeric(df[col], errors="coerce").abs().max()
            fmts[col] = "{:+,.0f}" if pd.notna(big) and big >= 100 else "{:+,.1f}"
        elif f in _PY_FMT:
            fmts[col] = _PY_FMT[f]
        else:
            continue
        conf = {**conf, "type_config": {**conf["type_config"], "format": None}}
        cfg[col] = conf
    data = df.style.format(fmts, na_rep="-") if fmts else df
    if "Sample" in df.columns:          # the Small badge in the grid: pale amber cell, dark amber text
        data = (data if fmts else df.style).map(
            lambda v: f"background-color: {BADGE_BG}; color: {BADGE_INK}; font-weight: 700" if v == SMALL else "",
            subset=["Sample"])
    # Desktop (2026-11-07, cut cells at 1280 px): a canvas grid cannot wrap, and "small" columns cut headers
    # such as "Chasing side won %". Every column now gets the pixel width its header and longest cell need
    # (grid_widths); if the grid fits its box at that width it shows (sortable, as before), else a CSS
    # container query swaps in a plain HTML table whose headers and long text wrap and whose numbers stay on
    # one line. The box is measured by the browser, so a table inside st.columns decides by its own width.
    widths = grid_widths(df, cfg, fmts)
    for col, px in widths.items():
        conf = cfg.get(col)
        cfg[col] = {**conf, "width": px} if isinstance(conf, dict) else {"width": px}
    need = sum(widths.values()) + 2                       # + the grid's 1 px border a side
    key = _table_key()
    with st.container(key=key):
        st.dataframe(data, column_config=cfg, **kwargs)
        st.markdown(f"<style>@media (min-width: 641px) {{ @container (max-width: {need - 0.02:.2f}px) {{ .st-key-{key} "
                    '[data-testid="stElementContainer"]:has([data-testid="stDataFrame"]) { display: none !important; } '
                    f'.st-key-{key} [data-testid="stElementContainer"]:has(.tc-dtable) {{ display: block !important; }} }} }}'
                    "</style>" + html_table(df, cfg, fmts), unsafe_allow_html=True)
    # Phone (CSS, 640 px or less): the grid above is hidden and this plain HTML copy shows instead. A canvas
    # grid cannot wrap text, so on a phone the last columns and long text (Method's Meaning) were cut off.
    st.markdown(phone_table(df, cfg, fmts, index=not kwargs["hide_index"]), unsafe_allow_html=True)
    if n > MAX_ROWS:
        note(f"Showing the first {MAX_ROWS} of {n} rows. Narrow the competition or season to see others.")


# Advance widths of Source Sans (the grid's 400 14px font), in thousandths of an em; others count as 0.62 em.
_GLYPH = {**dict.fromkeys("0123456789", 497), " ": 200, ".": 249, ",": 249, ":": 249, ";": 249, "'": 220,
          "%": 812, "-": 311, "+": 497, "=": 497, "(": 300, ")": 300, "/": 343, "&": 640, "#": 497, "*": 420,
          "a": 486, "b": 548, "c": 445, "d": 548, "e": 497, "f": 297, "g": 490, "h": 541, "i": 246, "j": 252,
          "k": 489, "l": 254, "m": 822, "n": 543, "o": 535, "p": 548, "q": 548, "r": 342, "s": 419, "t": 330,
          "u": 541, "v": 461, "w": 707, "x": 444, "y": 461, "z": 420,
          "A": 544, "B": 600, "C": 579, "D": 626, "E": 530, "F": 495, "G": 625, "H": 655, "I": 266, "J": 470,
          "K": 590, "L": 487, "M": 731, "N": 652, "O": 671, "P": 590, "Q": 671, "R": 594, "S": 549, "T": 549,
          "U": 650, "V": 520, "W": 788, "X": 516, "Y": 486, "Z": 548}
_GRID_PAD = 22          # grid cell: 8 px padding a side, plus room for the header's sort arrow and rounding


def text_px(s, size=14):
    """Width of a line of text in the grid font, in px (a little generous: 6% added)."""
    return sum(_GLYPH.get(ch, 620) for ch in str(s)) * size / 1000 * 1.06


def grid_widths(df, cfg, fmts):
    """Pixel width per column so that no header and no cell is cut in the desktop grid."""
    out = {}
    for col in df.columns:
        conf = cfg.get(col)
        head = str(conf.get("label") or col) if isinstance(conf, dict) else str(col)
        cells = [_cell_text(v, fmts.get(col), conf) for v in df[col].tolist()]
        out[col] = int(np.ceil(max([text_px(head)] + [text_px(t) for t in cells]) + _GRID_PAD))
    return out


def _table_key():
    """A key for each table's box, unique within one run of the page (reset by Home.py before each page)."""
    n = st.session_state.get("_tc_table_n", 0) + 1
    st.session_state["_tc_table_n"] = n
    return f"tc_tbl_{n}"


def reset_table_keys():
    st.session_state["_tc_table_n"] = 0
    st.session_state["_tc_png_n"] = 0


def html_table(df, cfg, fmts):
    """The desktop table used when the grid would not fit its box: headers and long text wrap, numbers
    stay on one line, the column help shows on the header as a tooltip."""
    cols = list(df.columns)
    esc = html.escape
    th, numeric = [], []
    for col in cols:
        conf = cfg.get(col) if isinstance(cfg.get(col), dict) else {}
        n = pd.api.types.is_numeric_dtype(df[col]) or conf.get("alignment") == "right" \
            or conf.get("type_config", {}).get("type") == "number"
        numeric.append(n)
        tip = f' title="{esc(conf["help"])}"' if conf.get("help") else ""
        th.append(f'<th class="{"n" if n else "t"}"{tip}>{esc(str(conf.get("label") or col))}</th>')
    rows = [[_cell_text(v, fmts.get(col), cfg.get(col)) for col, v in zip(cols, r)] for r in df.itertuples(index=False)]
    # short text (names, grounds, cities: at most 24 characters) stays on one line; long text wraps
    kind = ["n" if n else ("t s" if max((len(r[i]) for r in rows), default=0) <= 24 else "t")
            for i, n in enumerate(numeric)]
    body = "".join("<tr>" + "".join(f'<td class="{k}">{_cell_html(v)}</td>' for v, k in zip(r, kind)) + "</tr>" for r in rows)
    return f'<div class="tc-dtable"><table><thead><tr>{"".join(th)}</tr></thead><tbody>{body}</tbody></table></div>'


PHONE_WIDTH = 326       # px of table at 360 px wide (block padding .9rem a side, 1 px border)
_CHAR_PX, _CELL_PAD = 6.9, 9   # 12.5 px type: about 6.9 px per character; cell padding left plus right


def _cell_text(v, py_fmt, conf):
    """The text a grid cell shows: the house format, else the column's printf format, else the value."""
    if v is None or (isinstance(v, float) and np.isnan(v)) or (not isinstance(v, str) and pd.isna(v)):
        return "-"
    try:
        if py_fmt:
            return py_fmt.format(v)
        f = (conf or {}).get("type_config", {}).get("format") if isinstance(conf, dict) else None
        if f and f.startswith("%"):
            return f % v
    except (TypeError, ValueError):
        pass
    return str(v)


def _cell_html(v):
    """A cell's HTML: the Small badge for thin samples, else the escaped text."""
    return f'<span class="tc-badge">{SMALL}</span>' if v == SMALL else html.escape(str(v))


def phone_table(df, cfg, fmts, index=False):
    """The phone copy of a table, as HTML that never needs sideways scrolling. If its columns fit in 360 px
    (each column as wide as its longest word, header or cell), a table whose headers and cells wrap; else
    (wide record tables) one small card per row: the row's name on top, then label and value pairs."""
    if index:
        df = df.reset_index()
    cols = list(df.columns)
    heads = [str((cfg.get(c) or {}).get("label") or c) if isinstance(cfg.get(c), dict) else str(c) for c in cols]
    rows = [[_cell_text(v, fmts.get(c), cfg.get(c)) for c, v in zip(cols, r)] for r in df.itertuples(index=False)]
    numeric = [pd.api.types.is_numeric_dtype(df[c]) or (isinstance(cfg.get(c), dict) and
               (cfg[c].get("alignment") == "right" or cfg[c].get("type_config", {}).get("type") == "number"))
               for c in cols]

    def longest_word(t):
        return max((len(w) for w in str(t).split()), default=1)

    need = sum(max([longest_word(h)] + [longest_word(r[i]) for r in rows]) * _CHAR_PX + _CELL_PAD
               for i, h in enumerate(heads))
    esc = html.escape
    if need <= PHONE_WIDTH:
        th = "".join(f'<th class="{"n" if n else "t"}">{esc(h)}</th>' for h, n in zip(heads, numeric))
        body = "".join("<tr>" + "".join(f'<td class="{"n" if n else "t"}">{_cell_html(v)}</td>' for v, n in zip(r, numeric))
                       + "</tr>" for r in rows)
        return f'<div class="tc-mtable"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'
    # cards: the title is "#" (if any) and the first text column; every other column is a label and value
    rank = cols.index("#") if "#" in cols else None
    name = next((i for i, n in enumerate(numeric) if not n and i != rank), 0)
    cards = []
    for r in rows:
        title = (f"{r[rank]}. " if rank is not None else "") + (f"{heads[name]} {r[name]}" if numeric[name] else r[name])
        # a text value (team names) takes the card's full width and may wrap; numbers stay on one line
        pairs = "".join(f'<div{"" if numeric[i] else " class=w"}><span>{esc(h)}</span><b>{_cell_html(v)}</b></div>'
                        for i, (h, v) in enumerate(zip(heads, r)) if i not in (rank, name))
        cards.append(f'<div class="tc-mcard"><p>{esc(title)}</p><div class="tc-mpairs">{pairs}</div></div>')
    return f'<div class="tc-mtable tc-mcards">{"".join(cards)}</div>'


# ---- column formats (docs/STYLE.md section 7). Numbers right-aligned, text left-aligned.
def col_int(label=None, help=None, width="small"):
    return st.column_config.NumberColumn(label, format="%d", help=help, width=width)


def col_1(label=None, help=None, width="small"):
    return st.column_config.NumberColumn(label, format="%.1f", help=help, width=width)


def col_2(label=None, help=None, width="small"):
    return st.column_config.NumberColumn(label, format="%.2f", help=help, width=width)


def col_pct(label=None, help=None, width="small"):
    return st.column_config.NumberColumn(label, format="%.1f%%", help=help, width=width)


def col_text(label=None, help=None, width="medium"):
    return st.column_config.TextColumn(label, help=help, width=width)



def date_fmt(d):
    """'2017-02-26' -> '26 Feb 2017'."""
    if d is None or d == "" or (isinstance(d, float) and np.isnan(d)):
        return ""
    t = pd.Timestamp(d)
    return f"{t.day} {t:%b %Y}"



# ------------------------------------------------------------------ shareable links (query parameters)
def link_set(**params):
    """After a widget: write the current view into the URL so it can be shared."""
    for k, v in params.items():
        if v is None:
            st.query_params.pop(k, None)
        elif st.query_params.get(k) != str(v):
            st.query_params[k] = str(v)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


# ------------------------------------------------------------------ data (read-only, cached)
def db_path():
    """The data file (data_files.locate: DOM_APP_DB, the local build, or the hosted download); None if not found."""
    return data_files.locate()[0]


def _con():
    return sqlite3.connect(f"file:{Path(db_path()).as_posix()}?mode=ro", uri=True, check_same_thread=False)


@st.cache_data(show_spinner=False)
def query(sql, params=()):
    con = _con()
    try:
        return pd.read_sql_query(sql, con, params=params)
    finally:
        con.close()


@st.cache_data(show_spinner=False)
def editions():
    e = query("SELECT * FROM editions").sort_values(["first_date", "edition_id"]).reset_index(drop=True)
    e["order"] = range(len(e))
    return e


@st.cache_data(show_spinner=False)
def competitions():
    """Competitions in the order they first appear."""
    return list(editions().drop_duplicates("competition").competition)


@st.cache_data(show_spinner=False)
def seasons_for(comp):
    """Seasons of a competition (or all), newest first."""
    e = editions()
    if comp != COMP_ALL:
        e = e[e.competition == comp]
    first = e.groupby("season").first_date.min().sort_values(ascending=False)
    return list(first.index)


@st.cache_data(show_spinner=False)
def players():
    return query("SELECT * FROM players").set_index("player_id")


@st.cache_data(show_spinner=False)
def team_names():
    return dict(query("SELECT team_id, name FROM teams").values)


@st.cache_data(show_spinner=False)
def ground_names():
    return dict(query("SELECT ground_id, shown_name FROM grounds").values)


@st.cache_data(show_spinner=False)
def results():
    r = query("SELECT * FROM results")
    e = editions()[["edition_id", "edition_name", "competition", "season", "order"]]
    r = r.merge(e, on="edition_id")
    r["ground"] = r.ground_id.map(ground_names())
    return r


@st.cache_data(show_spinner=False)
def bat_edition():
    b = query("SELECT * FROM bat_edition").merge(editions()[["edition_id", "edition_name", "order", "first_date"]], on="edition_id")
    b["team"] = b.team_id.map(team_names())
    return b


@st.cache_data(show_spinner=False)
def bowl_edition():
    b = query("SELECT * FROM bowl_edition").merge(editions()[["edition_id", "edition_name", "order", "first_date"]], on="edition_id")
    b["team"] = b.team_id.map(team_names())
    return b


@st.cache_data(show_spinner=False)
def export_info():
    return query("SELECT * FROM export_info").iloc[0].to_dict()


@st.cache_resource(show_spinner=False)
def _names():
    """player_id -> shown name, built once per server (a shared dict, not a copy per call: the Player dropdown
    formats 1,220 options on every run)."""
    return dict(players()["name"])


@st.cache_resource(show_spinner=False)
def player_order():
    """Player IDs sorted by shown name (the Player dropdown)."""
    n = _names()
    return tuple(sorted(n, key=n.get))


def name(pid):
    return _names().get(pid, str(pid))


def in_scope(df, eids):
    return df[df.edition_id.isin(eids)]


# ------------------------------------------------------------------ scope: competition + season
def _scope_from_url():
    comps = [COMP_ALL] + competitions()
    by_slug = {slug(c): c for c in comps}
    comp = by_slug.get(st.query_params.get("comp", ""), COMP_ALL)
    seas = [SEASON_ALL] + seasons_for(comp)
    s_slug = {slug(s): s for s in seas}
    season = s_slug.get(st.query_params.get("season", ""), SEASON_ALL)
    return comp, season


def header(show_scope=True):
    """Same header on every page: brand, the global search and the competition + season picker (Method: brand and
    search only). The scope is in the URL as ?comp=national-t20-cup&season=2025-26. Default (owner, 2026-11-10): all
    competitions and all seasons on first open, on every page. The picked scope is kept in _tc_scope as well, so it
    survives pages without the picker (Method), where Streamlit drops the widget keys."""
    if "scope_comp" not in st.session_state or "scope_season" not in st.session_state:
        saved = st.session_state.get("_tc_scope") or _scope_from_url()
        st.session_state.setdefault("scope_comp", saved[0])
        st.session_state.setdefault("scope_season", saved[1] if saved[0] == st.session_state.scope_comp else SEASON_ALL)

    def comp_changed():
        seas = seasons_for(st.session_state.scope_comp)
        if st.session_state.scope_season not in [SEASON_ALL] + seas:
            st.session_state.scope_season = SEASON_ALL

    goto = st.session_state.pop("_tc_goto", None)
    if goto:                                    # a global search pick: its page, with its sub-tab and pick set
        st.switch_page(goto)
    left, right = st.columns([2, 3], vertical_alignment="center")
    left.markdown(f'<div class="tc-brand"><b>T20 <span>Crease</span></b><i>{TAGLINE}</i></div><div class="tc-crease"></div>',
                  unsafe_allow_html=True)
    if not show_scope:
        with right.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small",
                             key="tc_scope_bar"):
            global_search()
        st.markdown('<hr class="tc-rule">', unsafe_allow_html=True)
        return
    comps = [COMP_ALL] + competitions()
    if st.session_state.scope_comp not in comps:
        st.session_state.scope_comp = COMP_ALL
    seas = [SEASON_ALL] + seasons_for(st.session_state.scope_comp)
    if st.session_state.scope_season not in seas:
        st.session_state.scope_season = SEASON_ALL
    with right.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small",
                         key="tc_scope_bar"):
        global_search()
        st.selectbox("Competition", comps, key="scope_comp", on_change=comp_changed, label_visibility="collapsed",
                     width=230, help="Every page shows the competition and season chosen here.")
        st.selectbox("Season", seas, key="scope_season", label_visibility="collapsed", width=130,
                     help="Seasons are named as the competition named them (2012/13, 2013).")
    st.markdown('<hr class="tc-rule">', unsafe_allow_html=True)
    comp, season = st.session_state.scope_comp, st.session_state.scope_season
    st.session_state["_tc_scope"] = (comp, season)
    default = (COMP_ALL, SEASON_ALL)
    link_set(comp=None if (comp, season) == default else slug(comp),
             season=None if (comp, season) == default else slug(season))


def scope():
    """(competition, season, edition IDs) chosen in the header."""
    saved = st.session_state.get("_tc_scope") or (COMP_ALL, SEASON_ALL)
    st.session_state.setdefault("scope_comp", saved[0])
    st.session_state.setdefault("scope_season", saved[1])
    comp, season = st.session_state.scope_comp, st.session_state.scope_season
    e = editions()
    if comp != COMP_ALL:
        e = e[e.competition == comp]
    if season != SEASON_ALL:
        e = e[e.season == season]
    return comp, season, tuple(int(x) for x in e.edition_id)


def scope_label(comp, season):
    if comp == COMP_ALL and season == SEASON_ALL:
        return "all competitions and seasons"
    if comp == COMP_ALL:
        return f"all competitions, {season}"
    if season == SEASON_ALL:
        return f"{comp}, all seasons"
    return f"{comp} {season}"


def mobile_nav(pages, current=None):
    """Phone menu: one row of page tabs under the header, shown only up to 768 px wide."""
    i = next((n for n, p in enumerate(pages, 1) if current is not None and p.url_path == current.url_path), 0)
    with st.container(key="tc_mobile_nav"):
        for p in pages:
            st.page_link(p, label=p.title)
        if i:
            chip = f'.st-key-tc_mobile_nav > div:nth-child({i}) [data-testid="stPageLink-NavLink"]'
            st.html(f'<style>{chip} {{ background: {BLUE} !important; border-color: {BLUE} !important; }}'
                    f' {chip} p {{ color: #FFFFFF !important; font-weight: 700; }}</style>')


# ------------------------------------------------------------------ page frame
def page(title, subtitle=""):
    _EMBED.head, _EMBED.sub = (title, "") if not embedded() else (getattr(_EMBED, "head", title), "")
    if embedded():          # a sub-page: the host page has the title, the sub-tab names the part
        if subtitle:
            st.markdown(f'<p class="tc-sub">{html.escape(subtitle)}</p>', unsafe_allow_html=True)
        return
    st.markdown(f'<p class="tc-title">{html.escape(title)}</p>'
                + (f'<p class="tc-sub">{html.escape(subtitle)}</p>' if subtitle else ""), unsafe_allow_html=True)


def section(title, help_text=""):
    _EMBED.head, _EMBED.sub = title, help_text          # the owner's image export names the chart after its section
    st.markdown(f'<p class="tc-section">{html.escape(title)}</p>'
                + (f'<p class="tc-section-help">{html.escape(help_text)}</p>' if help_text else ""),
                unsafe_allow_html=True)


def footer():
    if embedded():          # the host page draws the footer once
        return
    st.markdown(f'<div class="tc-footer"><div class="tc-footer-credit">{html.escape(FOOTER)}</div></div>',
                unsafe_allow_html=True)
    with st.container(key="tc_footer_link"):
        st.page_link("views/method.py", label=METHOD_LINK)
    owner_box()


def cards(items, lead=False, detail=False):
    """items: (label, value, note). detail=True shows the note under the number (phones have no
    hover); a value that is a name or phrase is shown in smaller type with the note under it."""
    cls = "tc-card lead" if lead else "tc-card"
    cells = []
    for k, v, n in items:
        is_text = not re.fullmatch(r"[+\-]?[\d,]*\.?\d*%?\*?|-", str(v).strip())
        vcls = "tc-card-value text" if is_text else "tc-card-value"
        tip = f' title="{html.escape(n)}"' if n and not is_text else ""
        second = ""
        if n and is_text:
            second = f'<div class="tc-card-sub">{html.escape(n)}</div>'
        elif n and detail:
            second = f'<div class="tc-card-detail">{html.escape(n)}</div>'.replace(
                f"{SMALL} sample", f'<span class="tc-badge">{SMALL}</span> sample')
        cells.append(f'<div class="{cls}"{tip}><div class="tc-card-label">{html.escape(k)}</div>'
                     f'<div class="{vcls}" title="{html.escape(str(v))}">{html.escape(str(v))}</div>' + second + '</div>')
    st.markdown(f'<div class="tc-cards">{"".join(cells)}</div>', unsafe_allow_html=True)


def note(text):
    st.markdown(f'<p class="tc-note">{html.escape(text)}</p>', unsafe_allow_html=True)


def empty(title, hint=""):
    st.markdown(f'<div class="tc-empty"><b>{html.escape(title)}</b>{html.escape(hint)}</div>', unsafe_allow_html=True)


def tabs(names, key):
    """Lazy tabs: only the open tab's code runs; each tab has .open."""
    return st.tabs(names, key=key, on_change="rerun")


# ------------------------------------------------------------------ numbers
def fmt(v, nd=1):
    if v is None or (isinstance(v, float) and np.isnan(v)) or pd.isna(v):
        return "-"
    return f"{v:,.{nd}f}"


def overs(balls):
    balls = int(balls)
    return f"{balls // 6}.{balls % 6}" if balls % 6 else f"{balls // 6}"


def sample(inns):
    return SMALL if inns < SMALL_INNS else ""


def bat_summary(df, by):
    """Batting by `by` from bat_edition rows: rates blank under MIN_INNS innings, Sample = Small under SMALL_INNS."""
    if df.empty:
        return pd.DataFrame()
    d = df.copy()
    d["hs_key"] = d.high.fillna(-1) * 2 + d.high_not_out.fillna(0)
    g = d.groupby(by, sort=False)
    out = g.agg(matches=("matches", "sum"), innings=("innings", "sum"), outs=("outs", "sum"), runs=("runs", "sum"),
                balls=("balls", "sum"), fours=("fours", "sum"), sixes=("sixes", "sum"), fifties=("fifties", "sum"),
                hundreds=("hundreds", "sum"), hs_key=("hs_key", "max"))
    out["not_outs"] = out.innings - out.outs
    out["hs"] = [("-" if k < 0 else f"{int(k // 2)}{'*' if k % 2 else ''}") for k in out.hs_key]
    enough = out.innings >= MIN_INNS
    out["avg"] = np.where(enough & (out.outs > 0), out.runs / out.outs.where(out.outs > 0), np.nan)
    out["sr"] = np.where(enough & (out.balls > 0), 100 * out.runs / out.balls.where(out.balls > 0), np.nan)
    out["sample"] = [sample(i) for i in out.innings]
    return out.drop(columns="hs_key").reset_index()


def bowl_summary(df, by):
    if df.empty:
        return pd.DataFrame()
    d = df.copy()
    d["best_key"] = d.best_wickets * 1000 - d.best_runs
    g = d.groupby(by, sort=False)
    out = g.agg(innings=("innings", "sum"), balls=("balls", "sum"), runs=("runs", "sum"), wickets=("wickets", "sum"),
                maidens=("maidens", "sum"), four_w=("four_wickets", "sum"), best_key=("best_key", "max"))
    out["best"] = [f"{int((k + (-k) % 1000) // 1000)}/{int((-k) % 1000)}" for k in out.best_key]   # key = 1000 w - r
    enough = out.innings >= MIN_INNS
    out["econ"] = np.where(enough & (out.balls > 0), 6 * out.runs / out.balls.where(out.balls > 0), np.nan)
    out["avg"] = np.where(enough & (out.wickets > 0), out.runs / out.wickets.where(out.wickets > 0), np.nan)
    out["sr"] = np.where(enough & (out.wickets > 0), out.balls / out.wickets.where(out.wickets > 0), np.nan)
    out["overs"] = [overs(b) for b in out.balls]
    out["sample"] = [sample(i) for i in out.innings]
    return out.drop(columns="best_key").reset_index()


def best_text(w, r):
    return f"{int(w)}/{int(r)}"


def teams_latest(df, team_col="team", order_col="order"):
    """Team names, latest first."""
    if df.empty:
        return []
    g = df.groupby(team_col)[order_col].agg(["max", "min"]).sort_values(["max", "min"], ascending=False)
    return list(g.index)


@st.cache_data(show_spinner=False)
def teams_by_player(eids):
    """player_id -> 'Team A, Team B' (latest first) within the chosen editions."""
    b = pd.concat([bat_edition()[["player_id", "team", "order"]].assign(e=bat_edition().edition_id),
                   bowl_edition()[["player_id", "team", "order"]].assign(e=bowl_edition().edition_id)])
    b = b[b.e.isin(eids)]
    g = b.groupby(["player_id", "team"]).order.agg(["max", "min"]).reset_index()
    g = g.sort_values(["player_id", "max", "min"], ascending=[True, False, False], kind="mergesort")
    return g.groupby("player_id", sort=False).team.agg(", ".join).to_dict()


def team_chips(teams):
    chips = "".join(f'<span class="tc-team">{html.escape(t)}</span>' for t in teams)
    return f'<span class="tc-teams">{chips}</span>' if chips else ""


def thin(label, what="matches"):
    """The empty state for a scope with too little data."""
    empty(f"Not enough {what} in {label}.", " Try All competitions or All seasons at the top of the page.")


# ------------------------------------------------------------------ charts (Altair, the app's own theme)
# Every chart is drawn from the same DataFrame as the table under it, so it shows the same values.
def _chart_config(ch):
    return (ch.configure(background=SURFACE, font="Source Sans Pro, sans-serif")
            .configure_view(stroke=None)
            .configure_axis(labelColor=MUTED, titleColor=MUTED, gridColor=SURFACE_2, domainColor=CHART_GREY, tickColor=CHART_GREY,
                            labelFontSize=12, titleFontSize=12, titleFontWeight=600, labelLimit=0)
            .configure_legend(labelLimit=0))


def bar_chart(df, label, value, fmt=",.0f", title=None, color=BLUE, text=None, tip=None):
    """Horizontal bars, one per row, in the table's order; the value (or `text`) is printed at the bar's end.
    Labels are never cut (labelLimit 0). tip: extra text columns for the hover (a player's full detail)."""
    if df.empty:
        return
    tip = [t for t in (tip or []) if t not in (label, value, text)]
    d = df[[label, value] + ([text] if text and text not in (label, value) else []) + tip].copy()
    order = list(d[label])
    y = alt.Y(f"{label}:N", sort=order, title=None, axis=alt.Axis(labelLimit=0))
    top = float(pd.to_numeric(d[value], errors="coerce").max() or 0)
    x = alt.X(f"{value}:Q", title=title or value, axis=alt.Axis(format=fmt, tickCount=4),
              scale=alt.Scale(domain=[0, top * 1.18 if top > 0 else 1], nice=False))   # room for the end labels
    base = alt.Chart(d)
    bars = base.mark_bar(color=color, cornerRadiusEnd=2, height={"band": 0.7}).encode(
        y=y, x=x, tooltip=[alt.Tooltip(f"{label}:N")] + [alt.Tooltip(f"{t}:N") for t in tip]
        + [alt.Tooltip(f"{value}:Q", format=fmt)])
    lab = base.mark_text(align="left", dx=4, color=INK, fontSize=11).encode(
        y=y, x=x, text=alt.Text(f"{text}:N") if text else alt.Text(f"{value}:Q", format=fmt))
    ch = (bars + lab).properties(height=max(90, 24 * len(d) + 30))
    st.altair_chart(_chart_config(ch), width="stretch", theme=None)
    if owner_on():
        export_button(d, label, value, fmt, text, title)


def line_chart(df, x, y, fmt=",.1f", title=None):
    """A line with points over ordered categories (seasons), in the table's order."""
    if df.empty:
        return
    order = list(df[x])
    enc_x = alt.X(f"{x}:N", sort=order, title=None, axis=alt.Axis(labelAngle=-45, labelLimit=0))
    enc_y = alt.Y(f"{y}:Q", title=title or y, scale=alt.Scale(zero=False), axis=alt.Axis(format=fmt, tickCount=5))
    base = alt.Chart(df[[x, y]])
    ch = (base.mark_line(color=BLUE, strokeWidth=2.5).encode(x=enc_x, y=enc_y)
          + base.mark_point(color=AMBER, filled=True, size=55).encode(
              x=enc_x, y=enc_y, tooltip=[alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{y}:Q", format=fmt)])).properties(height=260)
    st.altair_chart(_chart_config(ch), width="stretch", theme=None)


def trend_chart(df, x, y, small="Sample", fmt=",.2f", title=None):
    """A line over ordered seasons, from the same DataFrame as the table under it; a point with a thin sample
    (Sample == Small) is drawn hollow in amber and named Small in the legend and tooltip."""
    if df.empty:
        return
    d = df[[x, y, small]].copy()
    d["Sample size"] = np.where(d[small] == SMALL, "Small (under 10 matches)", "10 matches or more")
    order = list(d[x])
    enc_x = alt.X(f"{x}:N", sort=order, title=None, axis=alt.Axis(labelAngle=-45, labelLimit=0, labelOverlap="greedy"))
    enc_y = alt.Y(f"{y}:Q", title=title or y, scale=alt.Scale(zero=False), axis=alt.Axis(format=fmt, tickCount=5))
    dom = ["10 matches or more", "Small (under 10 matches)"]
    base = alt.Chart(d)
    pts = base.mark_point(size=70, strokeWidth=2).encode(
        x=enc_x, y=enc_y,
        color=alt.Color("Sample size:N", scale=alt.Scale(domain=dom, range=[BLUE, AMBER]),
                        legend=alt.Legend(title=None, orient="top")),
        fill=alt.Fill("Sample size:N", scale=alt.Scale(domain=dom, range=[BLUE, PAGE_BG]), legend=None),
        tooltip=[alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{y}:Q", format=fmt), alt.Tooltip("Sample size:N")])
    ch = (base.mark_line(color=BLUE, strokeWidth=2.5).encode(x=enc_x, y=enc_y) + pts).properties(height=260)
    st.altair_chart(_chart_config(ch), width="stretch", theme=None)


# ------------------------------------------------------------------ leaderboards
LB_RULES = {"one": {"bf": 100, "bb": 120, "avg_w": 5}, "more": {"bf": 300, "bb": 300, "avg_w": 10}}


def one_season(eids):
    """True when the editions are all in one season (one or several competitions)."""
    e = editions()
    return e[e.edition_id.isin(eids)].season.nunique() <= 1


def lb_rules(eids):
    """Minimums for rate leaderboards: one season (100 balls faced, 20 overs, 5 wickets for an average) or more
    (300 balls, 50 overs, 10 wickets); always 5 innings."""
    return LB_RULES["one" if one_season(eids) else "more"]


@st.cache_data(show_spinner=False)
def best_innings(eids):
    """Each player's highest score in the editions (from bat_edition: his best per edition and team), with the
    edition and team where he made it. Not out wins a tie."""
    b = in_scope(bat_edition(), eids)
    b = b[b.high.notna()].copy()
    b["key"] = b.high * 2 + b.high_not_out.fillna(0)
    b = b.sort_values(["key", "order"], ascending=[False, True]).drop_duplicates("player_id")
    return b[["player_id", "high", "high_not_out", "edition_name", "team"]].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def best_figures(eids):
    """Each player's best bowling in one innings in the editions: most wickets, then fewest runs."""
    b = in_scope(bowl_edition(), eids).copy()
    b = b.sort_values(["best_wickets", "best_runs", "order"], ascending=[False, True, True]).drop_duplicates("player_id")
    return b[["player_id", "best_wickets", "best_runs", "edition_name", "team"]].reset_index(drop=True)


# ------------------------------------------------------------------ session 3: teams, venues, entry, dismissals, fielding
# All from the scorecards (dom_app.sqlite tables innings, stands, bat_entry, dismissals, fielding, field_coverage),
# built by export/domestic_export.py. Fielding numbers are shown only where the fielder is known for at least
# FIELD_MIN_COVER % of that kind of dismissal (owner's rule 2026-11-09).
FIELD_MIN_COVER = 95.0
COLLAPSE_WKTS, COLLAPSE_RUNS = 3, 20
DISMISSAL_ORDER = ["Caught", "Caught and bowled", "Bowled", "LBW", "Run out", "Stumped", "Other"]
ENTRY_BANDS = [(0, 0, "0 down (opener)"), (1, 2, "1 or 2 down"), (3, 4, "3 or 4 down"), (5, 10, "5 or more down")]
LIGHT = {"day": "Day", "daynight": "Day-night", "night": "Night"}


def wicket_label(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(int(n), f"{int(n)}th")


def count_label(n, unit="innings"):
    """Sample column for counts: 'not enough' under MIN_INNS, Small under SMALL_INNS."""
    return [f"{NOT_ENOUGH}" if x < MIN_INNS else (SMALL if x < SMALL_INNS else "") for x in n]


def rate(num, den, mult=1.0, n=None, minimum=MIN_INNS):
    """num / den * mult, blank (NaN) when den is 0 or the sample n is under the minimum."""
    num, den = np.asarray(num, dtype=float), np.asarray(den, dtype=float)
    n = den if n is None else np.asarray(n, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where((den > 0) & (n >= minimum), num / np.where(den > 0, den, 1) * mult, np.nan)
    return out


@st.cache_data(show_spinner=False)
def innings_table():
    i = query("SELECT * FROM innings")
    i["team"] = i.team_id.map(team_names())
    i["opp"] = i.opp_id.map(team_names())
    return i


@st.cache_data(show_spinner=False)
def stands():
    return query("SELECT * FROM stands")


@st.cache_data(show_spinner=False)
def bat_entry():
    return query("SELECT * FROM bat_entry")


@st.cache_data(show_spinner=False)
def dismissals():
    return query("SELECT * FROM dismissals")


@st.cache_data(show_spinner=False)
def fielding():
    f = query("SELECT * FROM fielding").merge(editions()[["edition_id", "edition_name", "order"]], on="edition_id")
    f["team"] = f.team_id.map(team_names())
    return f


@st.cache_data(show_spinner=False)
def field_coverage():
    return query("SELECT * FROM field_coverage")


def pct(known, total):
    return 100.0 * known / total if total else float("nan")


def coverage(eids, team_id=None):
    """Share of catches, run outs and stumpings in the editions (one fielding side if given) whose fielder is known:
    {'ct': (known, total, %), 'ro': ..., 'st': ...}."""
    f = in_scope(field_coverage(), eids)
    if team_id is not None:
        f = f[f.team_id == team_id]
    out = {}
    for k, a, b in (("ct", "catches_known", "catches"), ("ro", "run_outs_known", "run_outs"),
                    ("st", "stumpings_known", "stumpings")):
        kn, tot = int(f[a].sum()), int(f[b].sum())
        out[k] = (kn, tot, pct(kn, tot))
    return out


def cover_ok(cov, kinds=("ct",)):
    """True when every kind has at least FIELD_MIN_COVER % of its fielders known (a kind with none counts as known)."""
    return all(cov[k][1] == 0 or cov[k][2] >= FIELD_MIN_COVER for k in kinds)


def cover_text(cov, where="in this scope"):
    """'Fielder known for 98% of catches (480 of 484), 2% of run outs (1 of 63) and 100% of stumpings in this scope.'"""
    bits = []
    for k, word in (("ct", "catches"), ("ro", "run outs"), ("st", "stumpings")):
        kn, tot, p = cov[k]
        if tot:
            bits.append(f"{p:.0f}% of {word} ({kn:,} of {tot:,})")
    if not bits:
        return f"No catches, run outs or stumpings {where}."
    body = ", ".join(bits[:-1]) + (" and " if len(bits) > 1 else "") + bits[-1]
    return f"Fielder known for {body} {where}."


def pair_bar_chart(df, label, a, b, names=("A", "B"), fmt=",.0f", title=None):
    """Two bars per row (player A blue, player B amber), from the same wide DataFrame as the table under it."""
    if df.empty:
        return
    d = df[[label, a, b]].copy()
    order = list(d[label])
    base = alt.Chart(d).transform_fold([a, b], as_=["who", "value"])
    ch = base.mark_bar(cornerRadiusEnd=2).encode(
        y=alt.Y(f"{label}:N", sort=order, title=None, axis=alt.Axis(labelLimit=0)),
        yOffset=alt.YOffset("who:N", sort=[a, b]),
        x=alt.X("value:Q", title=title, axis=alt.Axis(format=fmt, tickCount=4)),
        color=alt.Color("who:N", scale=alt.Scale(domain=[a, b], range=[BLUE, AMBER]),
                        legend=alt.Legend(title=None, orient="top", labelExpr=f"datum.label == '{a}' ? "
                                          f"{names[0]!r} : {names[1]!r}", labelLimit=0)),
        tooltip=[alt.Tooltip(f"{label}:N"), alt.Tooltip("who:N", title="Player"), alt.Tooltip("value:Q", format=fmt)])
    st.altair_chart(_chart_config(ch.properties(height=max(110, 34 * len(d) + 50))), width="stretch", theme=None)


def stage_reached(r, team):
    """'Champion', 'Runner-up', 'Semi-final', 'Quarter-final', 'Super Eight' or 'Group' from a team's results in one
    edition."""
    st_ = set(r.stage)
    fin = r[r.stage == "final"]
    if len(fin):
        return "Champion" if (fin.winner == team).any() else "Runner-up"
    for k, v in (("semi", "Semi-final"), ("quarter", "Quarter-final"), ("super eight", "Super Eight")):
        if k in st_:
            return v
    return "Group"


# ------------------------------------------------------------------ leader cards (owner, 2026-11-09)
# Label on top, the player's name in bold (a link to his Player page in the same scope), the number large, "+N tied"
# when others share it, then one short caption ("runs · 9 innings"). Every card in a row has the same height.
NOT_ENOUGH_DATA = "not enough data"


def card_name(pid):
    """(name for a card, its small second line). The card shows the name alone; for a shared name the second line
    is the birth year ("b. 1982") or, when unknown, the first season ("from 2013"); never the long season-span label
    (owner, 2026-11-09). The picker and the Player page keep the full label."""
    me = players().loc[pid]
    if not me.label_kind:
        return me.base_name, ""
    return me.base_name, (f"b. {int(me.birth_year)}" if pd.notna(me.birth_year) else f"from {me.first_season}")


def leader_cards(items, comp, season):
    """items: dicts with label, pid (None when nobody qualifies), value, caption and tied (others level with him)."""
    cells = []
    for it in items:
        lab = html.escape(it["label"])
        if it.get("pid") is None:
            who = f'<div class="tc-card-name none">{NOT_ENOUGH_DATA}</div><div class="tc-card-who2"></div>'
            val = '<div class="tc-card-value">-</div>'
        else:
            pid = int(it["pid"])
            href = f"players?player={pid}&comp={slug(comp)}&season={slug(season)}"
            full = html.escape(name(pid))
            short, extra = card_name(pid)
            who = (f'<a class="tc-card-name" href="{href}" target="_self" title="{full}">{html.escape(short)}</a>'
                   f'<div class="tc-card-who2">{html.escape(extra)}</div>')
            val = f'<div class="tc-card-value" title="{html.escape(str(it["value"]))}">{html.escape(str(it["value"]))}</div>'
        tie = f'<div class="tc-card-tie">+{int(it["tied"])} tied</div>' if it.get("tied") else ""
        cap = f'<div class="tc-card-detail">{html.escape(it["caption"])}</div>'
        cells.append(f'<div class="tc-card tc-lcard"><div class="tc-card-label">{lab}</div>{who}{val}{tie}{cap}</div>')
    st.markdown(f'<div class="tc-cards tc-leaders">{"".join(cells)}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ Insights (owner, 2026-11-09): ball-by-ball aggregates
# Only innings whose ball-by-ball agrees with the scorecard (player views: only player innings that agree too), and only
# editions with at least BBB_MIN_MATCHES such matches. No line, length, shot or wagon-zone field is used.
BBB_MIN_MATCHES = 10
PHASE_ORDER = ["Powerplay", "Middle", "Death"]
PHASE_OVERS = {"Powerplay": "overs 1 to 6", "Middle": "overs 7 to 15", "Death": "overs 16 to 20"}
MIN_BALLS, SMALL_BALLS = 30, 60       # player phase rates: blank under 30 balls, Small under 60


@st.cache_data(show_spinner=False)
def bbb_coverage():
    return query("SELECT * FROM bbb_coverage").merge(editions()[["edition_id", "edition_name", "order"]], on="edition_id")


@st.cache_data(show_spinner=False)
def bbb_table(name_):
    return query(f"SELECT * FROM {name_}")


def bbb_scope(eids):
    """(edition IDs shown in Insights, coverage rows of the scope's hidden editions, coverage rows shown)."""
    cv = bbb_coverage()
    cv = cv[cv.edition_id.isin(eids)]
    shown = cv[cv.shown == 1].sort_values("order")
    hidden = cv[cv.shown == 0].sort_values("order")
    return tuple(int(x) for x in shown.edition_id), hidden, shown


def bbb_cover_line():
    """One line naming exactly the editions the ball-by-ball views cover and their matches (built from the data)."""
    cv = bbb_coverage()
    cv = cv[cv.shown == 1].sort_values("order")
    parts = [f"{n} ({int(m)} matches)" for n, m in zip(cv.edition_name, cv.matches)]
    return (f"Ball-by-ball views cover {', '.join(parts[:-1])} and {parts[-1]}: {int(cv.matches.sum())} matches, "
            f"{int(cv.innings.sum())} innings, where the ball-by-ball record agrees with the scorecard.")


def ball_sample(n):
    return [NOT_ENOUGH if x < MIN_BALLS else (SMALL if x < SMALL_BALLS else "") for x in n]


# ------------------------------------------------------------------ Records (owner, 2026-11-09)
# The top of each record list for the chosen scope (dom_app.sqlite rec_bat, rec_bowl, stand_batters, innings, results).
# Lists are never filtered to one player: no player's innings are listed one by one.
REC_N, REC_CAP = 10, 25        # the top 10, plus any row level with the 10th, at most 25 rows


@st.cache_data(show_spinner=False)
def rec_table(name_):
    return query(f"SELECT * FROM {name_}")


def top_ranked(df, sort, asc, rank_on, n=REC_N, cap=REC_CAP):
    """The first n rows after sorting, plus rows level with the nth on `rank_on` (at most cap rows), with '#' as a
    shared rank (1, 2, 2, 4)."""
    if df.empty:
        return df.assign(**{"#": []})
    d = df.sort_values(sort, ascending=asc, kind="mergesort").reset_index(drop=True)
    key = list(zip(*[d[k] for k in rank_on]))
    rank = [1]
    for i in range(1, len(key)):
        rank.append(rank[-1] if key[i] == key[i - 1] else i + 1)
    d.insert(0, "#", rank)
    if len(d) > n:
        d = d[d["#"] <= d["#"].iloc[n - 1]].head(cap)
    return d


# ------------------------------------------------------------------ data confidence meter (owner, 2026-11-09)
# At the top of the Insights page only (owner, 2026-11-10): how much of the chosen scope is complete and checked, in
# four parts.
# Each part is a plain share (known / all) with its counts in the hover text; Method defines each part.
CONF_PARTS = ("Fall of wickets", "Fielders", "Entry over", "Ball-by-ball")


@st.cache_data(show_spinner=False)
def confidence(eids):
    """{part: (known, total, hover text)} for the editions."""
    inn = in_scope(innings_table(), eids)
    fc = in_scope(field_coverage(), eids)
    be = in_scope(bat_entry(), eids)
    be = be[be.position >= 3]
    bc = bbb_coverage()
    bc = bc[bc.edition_id.isin(eids)]
    n_m = len(in_scope(results(), eids))
    f_k = int(fc.catches_known.sum() + fc.run_outs_known.sum() + fc.stumpings_known.sum())
    f_t = int(fc.catches.sum() + fc.run_outs.sum() + fc.stumpings.sum())
    out = {}
    k, t = int(inn.fow_complete.sum()), len(inn)
    out["Fall of wickets"] = (k, t, f"Fall of wickets complete (the score at every wicket) for {k:,} of {t:,} innings. "
                                    "Partnerships and collapses use only complete innings.")
    out["Fielders"] = (f_k, f_t, f"Fielder known for {f_k:,} of {f_t:,} catches, run outs and stumpings. Fielding "
                                 f"numbers are shown only where it is {FIELD_MIN_COVER:.0f}% or more.")
    k, t = int(be.overs_known.sum()), int(be.innings.sum())
    out["Entry over"] = (k, t, f"The over at which the batter came in is known for {k:,} of {t:,} innings by batters "
                               "at number 3 or lower (older scorecards often leave it out).")
    k = int(bc.matches.sum())
    out["Ball-by-ball"] = (k, n_m, f"{k:,} of {n_m:,} matches have a ball-by-ball record that agrees with the scorecard. "
                                   f"Insights shows only editions with {BBB_MIN_MATCHES} or more such matches.")
    return out


def confidence_meter(eids):
    """The small meter: four labelled bars with their share; the counts and meaning on hover."""
    parts = confidence(eids)
    if not parts["Fall of wickets"][1]:
        return
    cells = []
    for name_ in CONF_PARTS:
        k, t, tip = parts[name_]
        p = 100.0 * k / t if t else 0.0
        val = f"{p:.0f}%" if t else "-"
        cells.append(f'<div class="tc-conf-i" title="{html.escape(tip)}"><span class="tc-conf-l">{name_}</span>'
                     f'<span class="tc-conf-bar"><i style="width:{p:.1f}%"></i></span><b>{val}</b></div>')
    st.markdown(f'<div class="tc-conf" title="How much of the chosen competition and season is complete and checked">'
                f'<span class="tc-conf-h">Data confidence</span>{"".join(cells)}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ player journey (owner, 2026-11-09)
def timeline_chart(df, x, y, size, order_x, order_y, tip):
    """A season-by-team grid: one dot per season and team he played for, sized by matches (from the same rows as the
    table under it)."""
    if df.empty:
        return
    d = df[[x, y, size] + [t for t in tip if t not in (x, y, size)]].copy()
    ch = alt.Chart(d).mark_circle(color=BLUE, opacity=0.9).encode(
        x=alt.X(f"{x}:N", sort=order_x, title=None, scale=alt.Scale(domain=order_x),
                axis=alt.Axis(labelAngle=-45, labelLimit=0, labelOverlap="greedy")),
        y=alt.Y(f"{y}:N", sort=order_y, title=None, axis=alt.Axis(labelLimit=0)),
        size=alt.Size(f"{size}:Q", scale=alt.Scale(range=[40, 420], zero=True), legend=None),
        tooltip=[alt.Tooltip(f"{t}:N" if t != size else f"{t}:Q") for t in tip])
    st.altair_chart(_chart_config(ch.properties(height=max(120, 34 * len(order_y) + 70))), width="stretch", theme=None)


def career_chart(df, x, a, b, order_x):
    """Two small column charts sharing the seasons: `a` (runs, blue) above `b` (wickets, amber); seasons he did not play
    are left empty."""
    if df.empty:
        return
    d = df[[x, a, b]].copy()
    enc_x = alt.X(f"{x}:N", sort=order_x, title=None, scale=alt.Scale(domain=order_x),
                  axis=alt.Axis(labelAngle=-45, labelLimit=0, labelOverlap="greedy"))
    top = alt.Chart(d).mark_bar(color=BLUE, cornerRadiusEnd=2).encode(
        x=enc_x, y=alt.Y(f"{a}:Q", title=a, axis=alt.Axis(format=",.0f", tickCount=4)),
        tooltip=[alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{a}:Q", format=",.0f")]).properties(height=150)
    bot = alt.Chart(d).mark_bar(color=AMBER, cornerRadiusEnd=2).encode(
        x=enc_x, y=alt.Y(f"{b}:Q", title=b, axis=alt.Axis(format=",.0f", tickCount=3)),
        tooltip=[alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{b}:Q", format=",.0f")]).properties(height=110)
    st.altair_chart(_chart_config(alt.vconcat(top, bot, spacing=8)), width="stretch", theme=None)


# ------------------------------------------------------------------ player names in charts and lists (owner, 2026-11-10)
# Charts, cards and running text show the plain name ("Azam Khan"). Only when two different players with the same name
# appear in the same view does each get a short suffix: "(b. 1998)", else "(from 2013)" when the birth year is unknown,
# else "(ID 12345)". The long label (birth year and season span) is never on a chart axis; the full detail (birth year,
# seasons, teams) is in the hover and in the tables. Identity is always the player ID: two players are never merged.
def short_names(pids):
    """Display names for player IDs shown together, in the same order."""
    p = players()
    pids = [int(x) for x in pids]
    uniq = list(dict.fromkeys(pids))
    out, groups = {}, {}
    for x in uniq:
        groups.setdefault(p.at[x, "base_name"], []).append(x)
    for base, xs in groups.items():
        if len(xs) == 1:
            out[xs[0]] = base
            continue
        tag = {x: (f"b. {int(p.at[x, 'birth_year'])}" if pd.notna(p.at[x, "birth_year"]) else f"from {p.at[x, 'first_season']}")
               for x in xs}
        for x in xs:
            clash = sum(1 for y in xs if tag[y] == tag[x]) > 1
            out[x] = f"{base} ({'ID ' + str(x) if clash else tag[x]})"
    return [out[x] for x in pids]


def short_name(pid):
    """One player on his own: the plain name."""
    return players().at[int(pid), "base_name"]


@st.cache_data(show_spinner=False)
def career_teams():
    """player_id -> every team he played for (latest first), whole career."""
    return teams_by_player(tuple(int(x) for x in editions().edition_id))


def player_detail(pid, teams=None):
    """The hover text for a player: birth year, seasons and teams ('b. 1998 · 2020/21 to 2025/26 · Lahore Region')."""
    me = players().loc[int(pid)]
    bits = [f"b. {int(me.birth_year)}" if pd.notna(me.birth_year) else "birth year not known",
            me.first_season if me.first_season == me.last_season else f"{me.first_season} to {me.last_season}",
            teams if isinstance(teams, str) and teams else career_teams().get(int(pid), "")]
    return " · ".join(b for b in bits if b)


def name_cols(df, pid_col="player_id", teams=None):
    """Adds 'Name' (the short display name for this view) and 'Detail' (hover text) for a chart."""
    d = df.copy()
    d["Name"] = short_names(d[pid_col])
    tm = d[teams] if teams and teams in d else [None] * len(d)
    d["Detail"] = [player_detail(x, t) for x, t in zip(d[pid_col], tm)]
    return d


# ------------------------------------------------------------------ pages inside pages (owner, 2026-11-10: 8 tabs)
# Players (Player, Compare), Records & Trends, Teams & Venues each show their former pages as sub-tabs. A sub-page is the
# old view script run inside the open sub-tab: its title becomes the sub-tab's line, its footer is the host page's.
import threading  # noqa: E402

_EMBED = threading.local()


class ViewStop(Exception):
    """A sub-page has nothing more to show (thin scope): the host page goes on to its footer."""


def embedded():
    return getattr(_EMBED, "on", False)


@st.cache_resource(show_spinner=False)
def _view_code(name_):
    path = Path(__file__).parent / "views" / name_
    return compile(path.read_text(encoding="utf-8"), str(path), "exec")


def run_view(name_):
    """Run app/views/<name_> inside the current container."""
    _EMBED.on = True
    try:
        exec(_view_code(name_), {"__name__": "__main__", "__file__": str(Path(__file__).parent / "views" / name_)})
    except ViewStop:
        pass
    finally:
        _EMBED.on = False


def stop():
    """End the page early: inside a host page, hand back to it; on its own, footer and stop."""
    if embedded():
        raise ViewStop
    footer()
    st.stop()


def sub_tabs(names, key, param="view"):
    """The host page's sub-tabs (lazy). The open one is in the URL as ?view=compare; a link to an old page sets it."""
    if st.session_state.get(key) not in names:
        want = st.query_params.get(param, "")
        st.session_state[key] = next((n for n in names if slug(n) == want), names[0])
    with st.container(key=f"tc_sub_{key}"):
        out = tabs(names, key=key)
    pick = st.session_state[key]
    link_set(**{param: None if pick == names[0] else slug(pick)})
    return out


# ------------------------------------------------------------------ head to head (owner, 2026-11-10, feature 6)
# Every ordered pair of teams in the scope: the row team's matches, wins, losses, ties and no results against the column
# team, from the results table by team ID. Win %: of matches won or lost, blank under MIN_INNS, Small under SMALL_INNS.
@st.cache_data(show_spinner=False)
def h2h_pairs(eids):
    r = in_scope(results(), eids)
    if r.empty:
        return pd.DataFrame()
    a = r.assign(t=r.team_1_id, o=r.team_2_id)
    b = r.assign(t=r.team_2_id, o=r.team_1_id)
    x = pd.concat([a, b], ignore_index=True)
    x["won"] = (x.winner_id == x.t) & (x.tied == 0) & (x.no_result == 0)
    x["lost"] = x.winner_id.notna() & (x.winner_id != x.t) & (x.tied == 0) & (x.no_result == 0)
    g = x.groupby(["t", "o"]).agg(Played=("p_match", "size"), Won=("won", "sum"), Lost=("lost", "sum"),
                                  Tied=("tied", "sum"), NR=("no_result", "sum")).reset_index()
    tn = team_names()
    g["Team"], g["Opponent"] = g.t.map(tn), g.o.map(tn)
    dec = g.Won + g.Lost
    g["Win %"] = np.where(dec >= MIN_INNS, (100 * g.Won / dec.where(dec > 0)).round(1), np.nan)
    g["Sample"] = [NOT_ENOUGH if k < MIN_INNS else (SMALL if k < SMALL_INNS else "") for k in dec]
    g["Cell"] = g.Won.astype(int).astype(str) + "-" + g.Lost.astype(int).astype(str)
    for k in ("Played", "Won", "Lost", "Tied", "NR"):
        g[k] = g[k].astype(int)
    return g.drop(columns=["t", "o"])


@st.cache_data(show_spinner=False)
def h2h_order(eids):
    """Team names, most matches in the scope first (then by name)."""
    r = in_scope(results(), eids)
    n = pd.concat([r.team_1, r.team_2]).value_counts()
    return sorted(n.index, key=lambda t: (-n[t], t))


def _mix(a, b, f):
    """The colour f of the way from a to b (rgb), as Vega's rgb interpolation draws it."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * f):02X}" for x, y in zip(ca, cb))


def _contrast(fg, bg):
    def lum(hx):
        v = [int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


H2H_LOW, H2H_EMPTY = "#F4F8FA", "#E9EEF1"     # win % 0 (pale) to 100 (BLUE); grey: too few matches


def h2h_heatmap(d, teams):
    """The grid: one cell per pair that met, coloured by win % (rgb from pale to BLUE), the wins-losses in the cell in
    whichever of ink or white reads better on it, an amber dashed border on Small cells."""
    d = d[["Team", "Opponent", "Played", "Won", "Lost", "Tied", "NR", "Win %", "Sample", "Cell"]].copy()
    fill = [_mix(H2H_LOW, BLUE, w / 100) if pd.notna(w) else H2H_EMPTY for w in d["Win %"]]
    d["ink"] = ["#FFFFFF" if _contrast("#FFFFFF", f) > _contrast(INK, f) else INK for f in fill]
    d["fill"] = fill
    d["edge"] = [AMBER if s_ == SMALL else "#FFFFFF" for s_ in d.Sample]
    x = alt.X("Opponent:N", sort=teams, title="Opponent", scale=alt.Scale(domain=teams),
              axis=alt.Axis(labelAngle=-45, labelLimit=0, orient="top"))
    y = alt.Y("Team:N", sort=teams, title=None, scale=alt.Scale(domain=teams), axis=alt.Axis(labelLimit=0))
    tip = [alt.Tooltip("Team:N"), alt.Tooltip("Opponent:N"), alt.Tooltip("Played:Q"), alt.Tooltip("Won:Q"),
           alt.Tooltip("Lost:Q"), alt.Tooltip("Tied:Q"), alt.Tooltip("NR:Q", title="No result"),
           alt.Tooltip("Win %:Q", format=".1f"), alt.Tooltip("Sample:N")]
    base = alt.Chart(d)
    cells = base.mark_rect(strokeWidth=1.5).encode(
        x=x, y=y, fill=alt.Fill("fill:N", scale=None), stroke=alt.Stroke("edge:N", scale=None),
        strokeDash=alt.condition(alt.datum.Sample == SMALL, alt.value([3, 2]), alt.value([1, 0])), tooltip=tip)
    txt = base.mark_text(fontSize=11, fontWeight=600).encode(x=x, y=y, text="Cell:N", color=alt.Color("ink:N", scale=None),
                                                             tooltip=tip)
    side = max(26, min(44, 640 // max(len(teams), 1)))
    ch = (cells + txt).properties(height=side * len(teams), description="tc-heatmap")
    st.altair_chart(_chart_config(ch), width="stretch", theme=None)


def h2h_grid(d, teams):
    """The same grid as a table: one row per team, one column per opponent, 'wins-losses' or '-'."""
    cell = d.set_index(["Team", "Opponent"]).Cell
    rows = [{"Team": t, **{f"v {o}": (cell.get((t, o), "-") if o != t else "") for o in teams}} for t in teams]
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ young talent (owner, 2026-11-10, feature 7)
# Birth year only: a player's age in a season is the season's first year minus his birth year (2012/13 -> 2012). It is
# approximate (a birthday late in the year, a season played in the next calendar year) and can be one year out.
YOUNG_MAX = 22          # under 23


def season_year(s_):
    return int(str(s_)[:4])


@st.cache_data(show_spinner=False)
def young_rows(eids):
    """(bat_edition rows, bowl_edition rows) in the editions for players aged YOUNG_MAX or less that season, and how many
    players in the editions have no known birth year (left out)."""
    by = players().birth_year
    yr = editions().set_index("edition_id").season.map(season_year)
    out = []
    for df in (in_scope(bat_edition(), eids), in_scope(bowl_edition(), eids)):
        d = df.copy()
        d["age"] = d.edition_id.map(yr) - d.player_id.map(by)
        out.append(d[d.age.notna() & (d.age <= YOUNG_MAX)])
    seen_ = set(in_scope(bat_edition(), eids).player_id) | set(in_scope(bowl_edition(), eids).player_id)
    return out[0], out[1], int(sum(1 for x in seen_ if pd.isna(by.get(x))))


def young_ages(rows):
    """player_id -> '19' or '19 to 22' (his ages in the seasons counted)."""
    g = rows.groupby("player_id").age.agg(["min", "max"])
    return {k: (f"{int(a)}" if a == b else f"{int(a)} to {int(b)}") for k, a, b in zip(g.index, g["min"], g["max"])}


def young_teams(rows):
    """player_id -> his teams in the seasons counted, latest first."""
    g = rows.groupby(["player_id", "team"]).order.agg(["max", "min"]).reset_index()
    g = g.sort_values(["player_id", "max", "min"], ascending=[True, False, False], kind="mergesort")
    return g.groupby("player_id", sort=False).team.agg(", ".join).to_dict()


# ------------------------------------------------------------------ season recap (owner, 2026-11-10, feature 8)
def _eids_of(comp, season):
    e = editions()
    e = e if comp == COMP_ALL else e[e.competition == comp]
    return tuple(int(x) for x in e[e.season == season].edition_id)


def _season_numbers(eids):
    inn = in_scope(innings_table(), eids)
    bat = in_scope(bat_edition(), eids)
    runs, balls, six = int(inn.runs.sum()), int(inn.balls.sum()), int(bat.sixes.sum())
    return {"runs": runs, "rr": 6 * runs / balls if balls else np.nan, "sixes": six,
            "six20": 120 * six / balls if balls else np.nan}


@st.cache_data(show_spinner=False)
def season_recap(comp, season):
    """Everything the Season recap shows for one season of the competition (or of all competitions)."""
    eids = _eids_of(comp, season)
    seas = seasons_for(comp)
    i = seas.index(season)
    prev_s = seas[i + 1] if i + 1 < len(seas) else None
    r = in_scope(results(), eids)
    inn = in_scope(innings_table(), eids)
    bat = in_scope(bat_edition(), eids)
    bowl = in_scope(bowl_edition(), eids)
    out = {"matches": len(r), "n_ed": len(set(r.edition_id)), "no_result": int(r.no_result.sum()), "ties": int(r.tied.sum()),
           **_season_numbers(eids), "hundreds": int(bat.hundreds.sum()), "fifties": int(bat.fifties.sum()),
           "prev_season": prev_s, "prev": _season_numbers(_eids_of(comp, prev_s)) if prev_s else {}}
    ename = dict(zip(editions().edition_id, editions().edition_name))
    if len(inn):
        t = inn.sort_values(["runs", "wkts", "balls"], ascending=[False, True, True]).iloc[0]
        out["top_total"] = f"{int(t.runs)}" + ("" if t.wkts == 10 else f"/{int(t.wkts)}")
        out["top_total_note"] = f"{t.team} v {t.opp}"
    else:
        out["top_total"], out["top_total_note"] = "-", ""
    ed = editions()
    ed = ed[ed.edition_id.isin(eids)].sort_values("order")
    champs = []
    for e_ in ed.itertuples():
        fin = r[(r.edition_id == e_.edition_id) & (r.stage == "final")]
        ru = "-"
        if len(fin) and pd.notna(fin.iloc[0].winner):
            f_ = fin.iloc[0]
            ru = f_.team_2 if f_.winner == f_.team_1 else f_.team_1
        champs.append({"Edition": e_.edition_name, "Champion": e_.champion if isinstance(e_.champion, str) else "No final",
                       "Runner-up": ru, "Matches": int(e_.matches), "Teams": int(e_.teams)})
    out["champions"] = pd.DataFrame(champs)
    rows = []

    def add(cat, d, sort, asc, key, who, fig, team, edn=""):
        if d is None or d.empty:
            rows.append({"Category": cat, "Who": "not enough data", "Figure": "-", "Team": "", "Edition": "",
                         "Others level": 0})
            return
        d = d.sort_values(sort, ascending=asc, kind="mergesort")
        t_ = d.iloc[0]
        rows.append({"Category": cat, "Who": who(t_), "Figure": fig(t_), "Team": team(t_), "Edition": edn(t_) if edn else "",
                     "Others level": int((d[key] == t_[key]).sum()) - 1})
    bs = bat_summary(bat, ["player_id"]) if len(bat) else pd.DataFrame()
    ws = bowl_summary(bowl, ["player_id"]) if len(bowl) else pd.DataFrame()
    tm = teams_by_player(eids)
    rules = LB_RULES["one"]
    add("Most runs", bs[bs.runs > 0] if len(bs) else bs, ["runs", "balls"], [False, True], "runs",
        lambda t: name(int(t.player_id)), lambda t: f"{int(t.runs):,} runs", lambda t: tm.get(int(t.player_id), ""))
    add("Most wickets", ws[ws.wickets > 0] if len(ws) else ws, ["wickets", "runs"], [False, True], "wickets",
        lambda t: name(int(t.player_id)), lambda t: f"{int(t.wickets)} wickets", lambda t: tm.get(int(t.player_id), ""))
    hs = best_innings(eids).assign(k=lambda d: d.high * 2 + d.high_not_out.fillna(0))
    add("Highest score", hs, ["k"], [False], "k", lambda t: name(int(t.player_id)),
        lambda t: f"{int(t.high)}{'*' if t.high_not_out else ''}", lambda t: t.team, lambda t: t.edition_name)
    bf = best_figures(eids)
    bf = bf[bf.best_wickets > 0].assign(k=lambda d: d.best_wickets * 1000 - d.best_runs)
    add("Best bowling", bf, ["k"], [False], "k", lambda t: name(int(t.player_id)),
        lambda t: f"{int(t.best_wickets)}/{int(t.best_runs)}", lambda t: t.team, lambda t: t.edition_name)
    q = bs[(bs.balls >= rules["bf"]) & bs.sr.notna()].assign(k=lambda d: d.sr.round(1)) if len(bs) else bs
    add("Best strike rate", q, ["sr", "runs"], [False, False], "k", lambda t: name(int(t.player_id)),
        lambda t: f"{t.sr:.1f}", lambda t: tm.get(int(t.player_id), ""))
    q = ws[(ws.balls >= rules["bb"]) & ws.econ.notna()].assign(k=lambda d: d.econ.round(2)) if len(ws) else ws
    add("Best economy", q, ["econ", "wickets"], [True, False], "k", lambda t: name(int(t.player_id)),
        lambda t: f"{t.econ:.2f}", lambda t: tm.get(int(t.player_id), ""))
    add("Most sixes", bs[bs.sixes > 0] if len(bs) else bs, ["sixes", "balls"], [False, True], "sixes",
        lambda t: name(int(t.player_id)), lambda t: f"{int(t.sixes)} sixes", lambda t: tm.get(int(t.player_id), ""))
    add("Highest total", inn, ["runs", "wkts", "balls"], [False, True, True], "runs", lambda t: t.team,
        lambda t: f"{int(t.runs)}" + ("" if t.wkts == 10 else f"/{int(t.wkts)}"), lambda t: f"v {t.opp}",
        lambda t: ename[int(t.edition_id)])
    wr = r[r.margin_kind == "run"]
    add("Biggest win by runs", wr, ["margin"], [False], "margin", lambda t: t.winner, lambda t: f"{int(t.margin)} runs",
        lambda t: f"v {t.team_2 if t.winner == t.team_1 else t.team_1}", lambda t: t.edition_name)
    ww = r[r.margin_kind == "wicket"].assign(k=lambda d: d.margin * 1000 - d.balls_2)
    add("Biggest win by wickets", ww, ["k"], [False], "k", lambda t: t.winner,
        lambda t: f"{int(t.margin)} wickets, {int(t.balls_2)} balls", lambda t: f"v {t.team_2 if t.winner == t.team_1 else t.team_1}",
        lambda t: t.edition_name)
    out["leaders"] = pd.DataFrame(rows)
    return out


# ------------------------------------------------------------------ global search (owner, 2026-11-10, feature 9)
# One box in the header on every page: players (by the full label, so every player of a shared name is found), teams and
# grounds. A pick opens the player's Player tab, the team's Teams tab or the ground's Venues tab. If the pick has no
# match in the chosen competition and season, the scope widens to all competitions and seasons (said under the box).
@st.cache_resource(show_spinner=False)
def search_index():
    """(option keys in order, key -> label): players by name, then teams, then grounds with matches."""
    lab = {}
    for pid in player_order():
        lab[f"p:{pid}"] = f"{name(pid)} · player"
    used = set(results().team_1_id) | set(results().team_2_id)
    for tid, tn in sorted(team_names().items(), key=lambda x: x[1]):
        if tid in used:
            lab[f"t:{tid}"] = f"{tn} · team"
    used_g = set(results().ground_id)
    for gid, gn in sorted(ground_names().items(), key=lambda x: x[1]):
        if gid in used_g:
            lab[f"g:{gid}"] = f"{gn} · ground"
    return tuple(lab), lab


def _search_pick():
    """Callback (runs before the script, so it may set the pickers): the target page, its sub-tab and pick."""
    key = st.session_state.get("tc_gsearch")
    st.session_state.tc_gsearch = None
    if not key:
        return
    kind, ident = key.split(":")
    ident = int(ident)
    comp, season = st.session_state.get("scope_comp", COMP_ALL), st.session_state.get("scope_season", SEASON_ALL)
    e = editions()
    e = e if comp == COMP_ALL else e[e.competition == comp]
    e = e if season == SEASON_ALL else e[e.season == season]
    eids = set(int(x) for x in e.edition_id)
    r = results()
    r = r[r.edition_id.isin(eids)]
    if kind == "p":
        ok = ident in set(bat_edition()[bat_edition().edition_id.isin(eids)].player_id) |             set(bowl_edition()[bowl_edition().edition_id.isin(eids)].player_id)
        st.session_state.update(player_pick=ident, players_view="Player")
        page_ = "views/players.py"
    elif kind == "t":
        ok = ident in set(r.team_1_id) | set(r.team_2_id)
        st.session_state.update(team_pick=ident, tv_view="Teams")
        page_ = "views/teams_venues.py"
    else:
        ok = ident in set(r.ground_id)
        st.session_state.update(venue_pick=ground_names()[ident], tv_view="Venues")
        page_ = "views/teams_venues.py"
    if not ok:
        st.session_state.update(scope_comp=COMP_ALL, scope_season=SEASON_ALL, _tc_scope=(COMP_ALL, SEASON_ALL))
        st.session_state["_tc_widened"] = True
    st.session_state["_tc_goto"] = page_


def global_search():
    keys, lab = search_index()
    st.selectbox("Search", keys, index=None, key="tc_gsearch", format_func=lab.get, on_change=_search_pick,
                 placeholder="Search players, teams, grounds", label_visibility="collapsed", width=230,
                 help="Type a name: players, teams and grounds. Players of the same name each have their own entry.")


def widened_note():
    """Under the header after a search that widened the scope."""
    if st.session_state.pop("_tc_widened", False):
        note("Not in the competition and season you had picked: showing all competitions and all seasons.")


# ------------------------------------------------------------------ owner image export (owner, 2026-11-10, feature 10)
# Locked behind DOMESTIC_OWNER_KEY, read from Streamlit secrets only (.streamlit/secrets.toml, git-ignored, or the host's
# secrets). No secret: nothing of this shows. With a secret: an "Owner" box under the footer; the key typed there is
# compared in constant time and cleared at once; the session keeps only "unlocked". Unlocked: every bar chart gets a
# "Download image" button: a PNG drawn from the same rows as the chart, with its section, scope, brand and data credit.
import hmac  # noqa: E402
import io  # noqa: E402

OWNER_SECRET = "DOMESTIC_OWNER_KEY"


def _owner_secret():
    try:
        v = st.secrets.get(OWNER_SECRET)
    except Exception:           # no secrets file at all
        return None
    return str(v) if v else None


def owner_on():
    return bool(st.session_state.get("_tc_owner")) and _owner_secret() is not None


def _owner_check():
    typed = str(st.session_state.get("tc_owner_key") or "")
    secret = _owner_secret()
    st.session_state["_tc_owner"] = bool(secret) and hmac.compare_digest(typed.encode("utf-8"), secret.encode("utf-8"))
    st.session_state["_tc_owner_tried"] = not st.session_state["_tc_owner"]
    st.session_state.tc_owner_key = ""          # the typed key is never kept


def _owner_lock():
    st.session_state["_tc_owner"] = False


def owner_box():
    if _owner_secret() is None:
        return
    with st.container(key="tc_owner"):
        if owner_on():
            st.button("Owner mode on: lock", key="tc_owner_lock", on_click=_owner_lock, type="tertiary",
                      help="Every bar chart has a Download image button while this is on.")
        else:
            with st.expander("Owner"):
                st.text_input("Owner key", type="password", key="tc_owner_key", on_change=_owner_check)
                if st.session_state.pop("_tc_owner_tried", False):
                    note("That key is not right.")


def _png_key():
    n = st.session_state.get("_tc_png_n", 0) + 1
    st.session_state["_tc_png_n"] = n
    return f"tc_png_{n}"


def chart_png(d, label, value, fmt=",.0f", text=None, title=None, head=BRAND, sub=""):
    """The bar chart as a PNG (matplotlib), from the same rows, in the same order, with the same end labels."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker  # noqa: F401
    labels = [str(x) for x in d[label]]
    vals = pd.to_numeric(d[value], errors="coerce").fillna(0).tolist()
    ends = [str(t) for t in d[text]] if text else [format(v, fmt.replace(",", ",") if fmt else "") for v in vals]
    h = max(4.2, 0.42 * len(d) + 2.6)
    fig, ax = plt.subplots(figsize=(10, h), dpi=150)
    fig.patch.set_facecolor(PAGE_BG)
    ax.set_facecolor(PAGE_BG)
    y = list(range(len(d)))[::-1]
    ax.barh(y, vals, color=BLUE, height=0.7)
    ax.set_yticks(y, labels, fontsize=10, color=INK)
    top = max(vals) if vals else 1
    ax.set_xlim(0, top * 1.18 if top > 0 else 1)
    for yy, v, e in zip(y, vals, ends):
        ax.text(v + top * 0.01, yy, e, va="center", fontsize=9, color=INK)
    for k in ("top", "right", "left"):
        ax.spines[k].set_visible(False)
    ax.spines["bottom"].set_color(CHART_GREY)
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: format(v, ",.0f") if top >= 10 else f"{v:g}"))
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel(title or value, color=MUTED, fontsize=10)
    fig.text(0.02, 0.975, head, fontsize=15, fontweight="bold", color=BLUE, family="serif", va="top")
    if sub:
        fig.text(0.02, 0.975 - 0.33 / h, sub, fontsize=9.5, color=MUTED, va="top", wrap=True)
    fig.text(0.02, 0.012, f"{FOOTER}. Data: ESPNcricinfo scorecards.", fontsize=8.5, color=MUTED, va="bottom")
    fig.tight_layout(rect=(0, 0.04, 1, 1 - 0.75 / h))
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=PAGE_BG)
    plt.close(fig)
    return buf.getvalue()


def export_button(d, label, value, fmt, text, title):
    """Owner only: a Download image button under a bar chart; the PNG is drawn when clicked."""
    head = getattr(_EMBED, "head", BRAND) or BRAND
    what = title or value
    head = head if str(what).lower() in head.lower() else f"{head}: {what}"
    sub = getattr(_EMBED, "sub", "") or f"In {scope_label(*scope()[:2])}."
    rows = d.copy()
    st.download_button("Download image", data=lambda: chart_png(rows, label, value, fmt, text, title, head, sub),
                       file_name=f"t20-crease-{slug(head)}-{slug(value)}.png", mime="image/png", key=_png_key(),
                       on_click="ignore", icon=":material/download:", type="tertiary")


def export_context(sub, head=None):
    """A view whose scope differs from the header's (Leaderboards' Career) names it for the owner's images."""
    _EMBED.sub = sub
    if head:
        _EMBED.head = head
