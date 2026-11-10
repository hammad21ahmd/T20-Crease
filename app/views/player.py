"""
player.py - one player's domestic T20 record from the scorecards: overview, batting and bowling by edition, batting
position and entry, dismissals against all players, fielding (with its coverage), teams.
READ-ONLY (dom_app.sqlite). Players are chosen by Cricinfo player ID; shown names follow the shared-name rule.
Birth year only, style categories only.
"""

import html
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Player", "One player's domestic T20 record by competition and season, from the scorecards.")
comp, season, eids = c.scope()
label = c.scope_label(comp, season)
p = c.players()
allbat = c.bat_edition()
options = c.player_order()
if "player_pick" not in st.session_state:
    want = st.query_params.get("player", "")
    if want.isdigit() and int(want) in p.index:
        st.session_state.player_pick = int(want)
    else:
        top = c.in_scope(allbat, eids).groupby("player_id").runs.sum()
        top = top if len(top) else allbat.groupby("player_id").runs.sum()
        st.session_state.player_pick = int(top.idxmax())
pid = st.selectbox("Player", options, key="player_pick", format_func=c.name, placeholder="Type a name")
c.link_set(player=pid)
me = p.loc[pid]

bat_all = allbat[allbat.player_id == pid]
bowl_all = c.bowl_edition()[c.bowl_edition().player_id == pid]
bat = c.in_scope(bat_all, eids)
bowl = c.in_scope(bowl_all, eids)

# ------------------------------------------------------------------ header: birth year only, style categories only
bits = [f"Born {int(me.birth_year)}" if pd.notna(me.birth_year) else None,
        f"{me.bat_hand}-hand bat" if isinstance(me.bat_hand, str) else None,
        (f"{me.style_type} ({me.style_family})" if me.style_family != "Pace" else me.style_type)
        if isinstance(me.style_type, str) else "Bowling style: Unknown"]
seasons = bat_all.sort_values("order")
span = ""
if len(seasons):
    first, last = seasons.edition_name.iloc[0], seasons.edition_name.iloc[-1]
    span = f"{int(bat_all.matches.sum())} matches, {me.first_season} to {me.last_season}. " if first != last else \
        f"{int(bat_all.matches.sum())} matches, {me.first_season}. "
teams = c.teams_latest(pd.concat([bat_all[["team", "order"]], bowl_all[["team", "order"]]]))
# the plain name (owner, 2026-11-10); the picker above and the hover keep the full label
st.markdown(f'<p class="tc-lede" title="{html.escape(me["name"])}"><b>{html.escape(me.base_name)}</b></p>'
            f'<p class="tc-meta">{html.escape(span)}{html.escape(" | ".join(b for b in bits if b))}.</p>'
            + c.team_chips(teams), unsafe_allow_html=True)

if bat.empty and bowl.empty:
    c.empty(f"{me.base_name} played no matches in {label}.",
            " Try All competitions and All seasons at the top of the page to see his whole record.")
    c.stop()

def _bar_labels(t):
    """One bar per table row: the edition, and the team too when he played for two sides in one edition."""
    dup = t.edition_name.duplicated(keep=False)
    return [f"{e} ({tm})" if d else e for e, tm, d in zip(t.edition_name, t.team, dup)]


bs = c.bat_summary(bat, ["player_id"])
ws = c.bowl_summary(bowl, ["player_id"]) if len(bowl) else pd.DataFrame()

with st.container(key="tc_player_tabs"):
    tabs = c.tabs(["Overview", "Batting", "Bowling", "Position", "Dismissals", "Fielding", "Teams", "Journey"],
                  key="player_tab")
t_over, t_bat, t_bowl, t_pos, t_dis, t_fld, t_team, t_jour = tabs

with t_over:
    if t_over.open:
        b = bs.iloc[0]
        small = f"{int(b.innings)} innings" + (f", {c.SMALL} sample" if b.innings < c.SMALL_INNS else "")
        c.section("Batting", f"In {label}.")
        c.cards([("Matches", f"{int(b.matches)}", ""),
                 ("Runs", f"{int(b.runs):,}", small),
                 ("Average", c.fmt(b.avg, 1) if pd.notna(b.avg) else "-",
                  f"{int(b.outs)} dismissals" if pd.notna(b.avg) else ("not enough innings" if b.innings < c.MIN_INNS
                                                                        else "never dismissed")),
                 ("Strike rate", c.fmt(b.sr, 1) if pd.notna(b.sr) else "-",
                  f"{int(b.balls):,} balls" if pd.notna(b.sr) else "not enough innings"),
                 ("High score", b.hs, f"{int(b.fifties)} fifties, {int(b.hundreds)} hundreds")], lead=True, detail=True)
        if len(ws):
            w = ws.iloc[0]
            c.section("Bowling", f"In {label}.")
            c.cards([("Wickets", f"{int(w.wickets)}", f"{int(w.innings)} innings" + (f", {c.SMALL} sample" if w.innings < c.SMALL_INNS else "")),
                     ("Economy", c.fmt(w.econ, 2), f"{w.overs} overs" if pd.notna(w.econ) else "not enough innings"),
                     ("Average", c.fmt(w.avg, 1), "runs per wicket" if pd.notna(w.avg) else
                      ("not enough innings" if w.innings < c.MIN_INNS else "no wicket")),
                     ("Best", w.best, f"{int(w.four_w)} four-wicket hauls")], detail=True)
        else:
            c.note(f"He did not bowl in {label}.")
        c.note("Rates are blank under 5 innings and marked Small under 10.")

with t_bat:
    if t_bat.open:
        t = c.bat_summary(bat.sort_values("order", ascending=False), ["edition_name", "team"])
        if t.empty or int(t.innings.sum()) == 0:
            c.empty(f"He did not bat in {label}.")
        else:
            t["Bar"] = _bar_labels(t)
            c.bar_chart(t.rename(columns={"runs": "Runs"}), "Bar", "Runs", title="Runs by edition")
            c.table(pd.DataFrame({"Edition": t.edition_name, "Team": t.team, "Matches": t.matches, "Inns": t.innings,
                                  "NO": t.not_outs, "Runs": t.runs, "HS": t.hs, "Avg": t.avg, "SR": t.sr,
                                  "50s": t.fifties, "100s": t.hundreds, "4s": t.fours, "6s": t.sixes,
                                  "Sample": t["sample"]}),
                    {"Matches": c.col_int(), "Inns": c.col_int(), "NO": c.col_int(help="Not outs"), "Runs": c.col_int(),
                     "HS": c.col_text(help=c.HELP["HS"], width="small"), "Avg": c.col_1(help=c.HELP["Avg"]),
                     "SR": c.col_1(help=c.HELP["SR"]), "50s": c.col_int(), "100s": c.col_int(), "4s": c.col_int(),
                     "6s": c.col_int(), "Sample": c.col_text(help=c.HELP["Sample"], width="small")})
            c.note("Newest first. Rates are blank under 5 innings in the edition; Small: under 10 innings.")

with t_bowl:
    if t_bowl.open:
        if bowl.empty:
            c.empty(f"He did not bowl in {label}.")
        else:
            t = c.bowl_summary(bowl.sort_values("order", ascending=False), ["edition_name", "team"])
            t["Bar"] = _bar_labels(t)
            c.bar_chart(t.rename(columns={"wickets": "Wkts"}), "Bar", "Wkts", title="Wickets by edition")
            c.table(pd.DataFrame({"Edition": t.edition_name, "Team": t.team, "Inns": t.innings, "Overs": t.overs,
                                  "Runs": t.runs, "Wkts": t.wickets, "Best": t.best, "Avg": t.avg, "Econ": t.econ,
                                  "SR": t.sr, "4w": t.four_w, "Sample": t["sample"]}),
                    {"Inns": c.col_int(), "Overs": c.col_text(width="small"), "Runs": c.col_int(), "Wkts": c.col_int(),
                     "Best": c.col_text(help=c.HELP["Best"], width="small"), "Avg": c.col_1(help=c.HELP["Bowl avg"]),
                     "Econ": c.col_2(help=c.HELP["Econ"]), "SR": c.col_1(help=c.HELP["Bowl SR"]),
                     "4w": c.col_int(help="Innings with 4 or more wickets"),
                     "Sample": c.col_text(help=c.HELP["Sample"], width="small")})
            c.note("Newest first. Rates are blank under 5 innings in the edition; Small: under 10 innings.")


INT = c.col_int()
with t_pos:
    if t_pos.open:
        en = c.in_scope(c.bat_entry(), eids)
        en = en[en.player_id == pid]
        if en.empty:
            c.empty(f"He did not bat in {label}.")
        else:
            n = int(en.innings.sum())
            pos = en.groupby("position").agg(Inns=("innings", "sum"), Runs=("runs", "sum"), balls=("balls", "sum"),
                                             outs=("outs", "sum")).reset_index()
            usual = pos.sort_values(["Inns", "position"], ascending=[False, True]).iloc[0]
            k = en[en.entry_wkts >= 0]
            nk, nb = int(k.entry_known.sum()), int(en.overs_known.sum())
            avg_score = k.entry_runs.sum() / nk if nk else np.nan
            avg_wk = (k.entry_wkts * k.innings).sum() / nk if nk else np.nan
            avg_ball = en.entry_balls.sum() / nb if nb else np.nan
            c.cards([("Usual position", f"{int(usual.position)}", f"in {int(usual.Inns)} of {n} innings"),
                     ("Score when he came in", f"{avg_score:.0f}/{avg_wk:.1f}" if nk >= c.MIN_INNS else "-",
                      f"average runs/wickets, {nk} innings" if nk >= c.MIN_INNS else "not enough innings"),
                     ("Over when he came in", c.overs(round(avg_ball)) if nb >= c.MIN_INNS else "-",
                      f"average, known for {nb} of {n} innings" if nb >= c.MIN_INNS else
                      f"known for only {nb} of {n} innings")], lead=True, detail=True)
            c.section("By batting position", f"In {label}.")
            t = pd.DataFrame({"Position": pos.position.astype(str), "Inns": pos.Inns, "Runs": pos.Runs,
                              "Avg": c.rate(pos.Runs, pos.outs, n=pos.Inns).round(1),
                              "SR": c.rate(pos.Runs, pos.balls, 100, n=pos.Inns).round(1),
                              "Share %": (100 * pos.Inns / n).round(1), "Sample": [c.sample(x) for x in pos.Inns]})
            c.bar_chart(t, "Position", "Inns", title="Innings at each position")
            c.table(t, {"Inns": INT, "Runs": INT, "Avg": c.col_1(help=c.HELP["Avg"]), "SR": c.col_1(help=c.HELP["SR"]),
                        "Share %": c.col_1(help="Share of his innings at this position."),
                        "Sample": c.col_text(help=c.HELP["Sample"], width="small")})
            c.section("By wickets down when he came in", "The score and wickets at his arrival (the batter at position k "
                                                         "comes in at the fall of wicket k - 2; openers at 0 for 0).")
            rows = []
            for lo, hi, lab_ in c.ENTRY_BANDS + [(-1, -1, "Not known")]:
                g = en[(en.entry_wkts >= lo) & (en.entry_wkts <= hi)]
                if g.empty:
                    continue
                ni = int(g.innings.sum())
                rows.append({"Came in": lab_, "Inns": ni, "Runs": int(g.runs.sum()),
                             "Avg": c.rate([g.runs.sum()], [g.outs.sum()], n=[ni])[0],
                             "SR": c.rate([g.runs.sum()], [g.balls.sum()], 100, n=[ni])[0],
                             "Score at entry": (g.entry_runs.sum() / g.entry_known.sum())
                             if lo >= 0 and g.entry_known.sum() else np.nan,
                             "Sample": c.sample(ni)})
            t = pd.DataFrame(rows)
            for col in ("Avg", "SR", "Score at entry"):
                t[col] = t[col].astype(float).round(1)
            c.table(t, {"Inns": INT, "Runs": INT, "Avg": c.col_1(help=c.HELP["Avg"]), "SR": c.col_1(help=c.HELP["SR"]),
                        "Score at entry": c.col_1(help="Average team score when he came in."),
                        "Sample": c.col_text(help=c.HELP["Sample"], width="small")})
            c.note(f"Not known: the scorecard has no score for that wicket, or he came in after a batter retired hurt. "
                   f"The over is known for {nb} of his {n} innings (older scorecards often give the score but not the "
                   "over). Rates are blank under 5 innings; Small: under 10.")

with t_dis:
    if t_dis.open:
        d_all = c.in_scope(c.dismissals(), eids)
        mine_d = d_all[d_all.player_id == pid]
        if mine_d.empty:
            c.empty(f"He was not dismissed in {label}.")
        else:
            my_e = set(bat.edition_id)
            league = d_all[d_all.edition_id.isin(my_e)].groupby("how").n.sum().reindex(c.DISMISSAL_ORDER, fill_value=0)
            me_n = mine_d.groupby("how").n.sum().reindex(c.DISMISSAL_ORDER, fill_value=0)
            tot, ltot = int(me_n.sum()), int(league.sum())
            ok = tot >= c.MIN_INNS
            t = pd.DataFrame({"How out": c.DISMISSAL_ORDER, "Times": me_n.values.astype(int),
                              "His %": (100 * me_n.values / tot).round(1) if ok else np.nan,
                              "All players %": (100 * league.values / ltot).round(1)})
            t["Difference"] = (t["His %"] - t["All players %"]).round(1)
            t = t[(t.Times > 0) | (t["All players %"] > 0)]
            c.cards([("Dismissals", f"{tot}", f"{c.SMALL} sample" if tot < c.SMALL_INNS else "in " + label),
                     ("Most often", t.sort_values("Times", ascending=False).iloc[0]["How out"],
                      f"{int(t.Times.max())} of {tot}")], detail=True)
            if ok:
                c.bar_chart(t, "How out", "His %", fmt=",.1f", title="Share of his dismissals (%)")
            c.table(t, {"Times": INT, "His %": c.col_1(), "All players %": c.col_1(help="Every dismissal of every player "
                                                                                       "in the editions he batted in."),
                        "Difference": st.column_config.NumberColumn(format="%+.1f", width="small",
                                                                    help="His share minus the all-player share, in points.")})
            c.note(f"All players: the {ltot:,} dismissals in the editions he batted in ({label}). Retired hurt is not "
                   "a dismissal. Shares are blank under 5 dismissals" + (f"; {c.SMALL}: under 10." if tot < c.SMALL_INNS else "."))

with t_fld:
    if t_fld.open:
        f = c.in_scope(c.fielding(), eids)
        f = f[f.player_id == pid].sort_values("order", ascending=False)
        if f.empty:
            c.empty(f"He did not field in {label}.")
        else:
            tc_, tk_ = int(f.team_catches.sum()), int(f.team_catches_known.sum())
            tr_, trk_ = int(f.team_run_outs.sum()), int(f.team_run_outs_known.sum())
            cov_c, cov_r = c.pct(tk_, tc_), c.pct(trk_, tr_)
            ok_c = tc_ == 0 or cov_c >= c.FIELD_MIN_COVER
            ok_r = tr_ == 0 or cov_r >= c.FIELD_MIN_COVER
            no = "not shown: fielder known for"
            c.cards([("Catches", f"{int(f.catches.sum() + f.cb_catches.sum())}" if ok_c else "-",
                      f"{int(f.cb_catches.sum())} caught and bowled" if ok_c else f"{no} {cov_c:.0f}%"),
                     ("Keeper catches", f"{int(f.keeper_catches.sum())}" if ok_c else "-",
                      "as wicketkeeper" if ok_c else f"{no} {cov_c:.0f}%"),
                     ("Stumpings", f"{int(f.stumpings.sum())}", "as wicketkeeper"),
                     ("Run outs", f"{int(f.run_outs.sum())}" if ok_r else "-",
                      "every fielder named is credited" if ok_r else f"{no} {cov_r:.0f}%"),
                     ("Substitute catches", f"{int(f.sub_catches.sum())}" if ok_c else "-",
                      "while on as a substitute" if ok_c else f"{no} {cov_c:.0f}%"),
                     ("Matches", f"{int(f.matches.sum())}", "in the XI")], lead=True, detail=True)
            parts = []
            if tc_:
                parts.append(f"{cov_c:.0f}% of the catches ({tk_:,} of {tc_:,})")
            if tr_:
                parts.append(f"{cov_r:.0f}% of the run outs ({trk_:,} of {tr_:,})")
            c.note(("Fielder known for " + " and ".join(parts) + f" his sides took in his matches in {label}. "
                    f"A number is shown only where the fielder is known for at least {c.FIELD_MIN_COVER:.0f}%; a catch "
                    "whose fielder is unknown counts for nobody.") if parts else
                   f"No catches or run outs in his matches in {label}.")
            rc = [c.pct(k_, n_) for k_, n_ in zip(f.team_catches_known, f.team_catches)]
            rr = [c.pct(k_, n_) for k_, n_ in zip(f.team_run_outs_known, f.team_run_outs)]
            good_c = [n_ == 0 or p_ >= c.FIELD_MIN_COVER for p_, n_ in zip(rc, f.team_catches)]
            good_r = [n_ == 0 or p_ >= c.FIELD_MIN_COVER for p_, n_ in zip(rr, f.team_run_outs)]
            t = pd.DataFrame({"Edition": f.edition_name + " (" + f.team + ")", "Matches": f.matches,
                              "Ct": np.where(good_c, f.catches + f.cb_catches, np.nan),
                              "Keeper ct": np.where(good_c, f.keeper_catches, np.nan),
                              "St": f.stumpings, "Run outs": np.where(good_r, f.run_outs, np.nan),
                              "Sub ct": np.where(good_c, f.sub_catches, np.nan),
                              "Ct known %": np.round(rc, 0), "RO known %": np.round(rr, 0)})
            c.table(t, {"Matches": INT, "Ct": c.col_int(help="Catches in the field, caught and bowled included."),
                        "Keeper ct": INT, "St": INT, "Run outs": INT, "Sub ct": c.col_int(help="Catches as a substitute."),
                        "Ct known %": c.col_int(help="Share of his side's catches in his matches whose fielder is known."),
                        "RO known %": c.col_int(help="Share of his side's run outs in his matches whose fielders are known.")})
            c.note("Newest first. A cell is blank where the fielder is known for under "
                   f"{c.FIELD_MIN_COVER:.0f}% of those dismissals in his matches that edition. The source often names no "
                   "fielder for a run out (2005/06, 2006/07 and most editions from 2018/19), so run outs are often blank.")

with t_team:
    if t_team.open:
        bt = bat.groupby("team").agg(first=("first_date", "min"), last=("first_date", "max"), matches=("matches", "sum"),
                                     runs=("runs", "sum"), order=("order", "max"))
        wk = bowl.groupby("team").wickets.sum()
        bt["wickets"] = wk.reindex(bt.index).fillna(0).astype(int)
        bt = bt.sort_values("order", ascending=False).reset_index()
        c.table(pd.DataFrame({"Team": bt.team, "From": bt["first"].map(c.date_fmt), "To": bt["last"].map(c.date_fmt),
                              "Matches": bt.matches, "Runs": bt.runs, "Wickets": bt.wickets}),
                {"Matches": c.col_int(), "Runs": c.col_int(), "Wickets": c.col_int()})
        c.note("From and To: the start of his first and last edition for the team. Latest team first.")

with t_jour:
    if t_jour.open:
        # his whole career by season, whatever competition and season are picked at the top (owner, 2026-11-09)
        ed_ = c.editions()[["edition_id", "season", "competition", "order"]]
        app_ = pd.concat([bat_all[["edition_id", "team", "matches", "runs"]].assign(wickets=0),
                          bowl_all[["edition_id", "team"]].assign(matches=0, runs=0, wickets=bowl_all.wickets)])
        app_ = app_.merge(ed_, on="edition_id")
        st_ = app_.groupby(["season", "competition", "team"]).agg(Matches=("matches", "sum"), first=("order", "min"))             .reset_index().rename(columns={"season": "Season", "competition": "Competition", "team": "Team"})
        s_order = list(ed_.sort_values("order").drop_duplicates("season").season)
        played = [s_ for s_ in s_order if s_ in set(st_.Season)]
        span_ = s_order[s_order.index(played[0]):s_order.index(played[-1]) + 1]
        t_order = list(st_.sort_values("first").drop_duplicates("Team").Team)
        c.section("Journey", "His teams and competitions season by season, over his whole domestic T20 career (the "
                             "competition and season picked at the top do not narrow it). A bigger dot: more matches.")
        st_["so"] = st_.Season.map({s_: i for i, s_ in enumerate(s_order)})
        st_ = st_.sort_values(["so", "first", "Team"]).reset_index(drop=True)
        c.timeline_chart(st_, "Season", "Team", "Matches", span_, t_order, ["Season", "Team", "Competition", "Matches"])
        c.table(st_[["Season", "Competition", "Team", "Matches"]], {"Matches": INT, "Competition": c.col_text(width="large")},
                search="journey" if len(st_) > 15 else None)
        c.note("Oldest first: one row per season, competition and team. Matches count every match in the XI, batting or "
               "not.")
        by_s = app_.groupby("season").agg(Matches=("matches", "sum"), Runs=("runs", "sum"), Wickets=("wickets", "sum"))
        by_s = by_s.reindex(span_)
        gap = by_s.Matches.isna()
        by_s = by_s.fillna(0).astype(int).rename_axis("Season").reset_index()
        c.section("Career by season", "Runs (blue) and wickets (amber) in each season, oldest first.")
        c.career_chart(by_s, "Season", "Runs", "Wickets", span_)
        c.table(by_s[["Season", "Matches", "Runs", "Wickets"]], {"Matches": INT, "Runs": INT, "Wickets": INT})
        c.note(f"{len(played)} seasons played from {played[0]} to {played[-1]}"
               + (f"; no match in {int(gap.sum())} season{'s' if gap.sum() != 1 else ''} in between (rows with 0)."
                  if gap.any() else "."))

c.footer()
