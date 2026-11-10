"""
insights.py - ball-by-ball views: phases, over by over, a player by phase, and each team's phase profile.
READ-ONLY (dom_app.sqlite tables bbb_*, built by export/domestic_export.py).
Owner's rules 2026-11-09: only innings whose ball-by-ball agrees with the scorecard (player views: only player
innings that agree too); an edition is shown only with at least 10 such matches, and the page says which are left
out and why; every view says how many matches and innings it rests on; no line, length, shot or wagon-zone data;
no source credit on the page (Method's Data sources names it); one closing line lists exactly what is covered.
Phases: powerplay overs 1 to 6, middle 7 to 15, death 16 to 20.
The data confidence meter (fall of wickets, fielders, entry over, ball-by-ball) sits at the top of this page only.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as c  # noqa: E402

c.page("Insights", "Ball by ball: scoring and wickets by phase and by over, for players and for teams.")
comp, season, eids = c.scope()
label = c.scope_label(comp, season)
c.confidence_meter(eids)          # owner, 2026-11-10: the data confidence meter is shown here only, at the top
shown_e, hidden, shown_cov = c.bbb_scope(eids)
INT = c.col_int()

if len(hidden):
    c.note("Not shown: " + ", ".join(f"{n} ({int(m)} match{'es' if m != 1 else ''})" for n, m in
                                     zip(hidden.edition_name, hidden.matches))
           + f": fewer than {c.BBB_MIN_MATCHES} matches with a ball-by-ball record that agrees with the scorecard.")
if not shown_e:
    c.empty(f"No ball-by-ball view for {label}.",
            f" Ball-by-ball records cover only some editions, and an edition is shown from {c.BBB_MIN_MATCHES} matches"
            " whose record agrees with the scorecard. The latest edition covered is "
            f"{c.bbb_coverage().query('shown == 1').sort_values('order').edition_name.iloc[-1]}: choose it, or All "
            "seasons, at the top of the page.")
else:
    n_m, n_i = int(shown_cov.matches.sum()), int(shown_cov.innings.sum())
    based = f"From {n_m} matches and {n_i} innings in {label}" + \
        (f" ({len(shown_cov)} editions)" if len(shown_cov) > 1 else "") + "."
    tp = c.in_scope(c.bbb_table("bbb_team_phase"), shown_e)

    def phase_rows(d):
        g = d.groupby("phase").agg(inns=("inns", "sum"), legal=("legal", "sum"), faced=("faced", "sum"), runs=("runs", "sum"),
                                   wkts=("wkts", "sum"), b4=("fours", "sum"), b6=("sixes", "sum"), dots=("dots", "sum"))
        return g.reindex(c.PHASE_ORDER).dropna(how="all").fillna(0)

    t_ph, t_ov, t_pl, t_tm = c.tabs(["Phases", "Over by over", "Players", "Teams"], key="ins_tab")
    with t_ph:
        if t_ph.open:
            c.section("By phase", based + " Powerplay: overs 1 to 6; middle: 7 to 15; death: 16 to 20.")
            g = phase_rows(tp)
            t = pd.DataFrame({"Phase": g.index, "Innings": g.inns.astype(int), "Runs": g.runs.astype(int),
                              "Run rate": (6 * g.runs / g.legal).round(2), "Wickets": g.wkts.astype(int),
                              "Wickets per innings": (g.wkts / g.inns).round(2),
                              "Boundary %": (100 * (g.b4 + g.b6) / g.faced).round(1),
                              "Dot ball %": (100 * g.dots / g.legal).round(1)})
            c.bar_chart(t, "Phase", "Run rate", fmt=",.2f", title="Runs per over")
            c.table(t, {"Innings": INT, "Runs": INT, "Run rate": c.col_2(help="Runs per 6 legal balls, extras included."),
                        "Wickets": INT, "Wickets per innings": c.col_2(),
                        "Boundary %": c.col_1(help="Balls faced hit for 4 or 6."),
                        "Dot ball %": c.col_1(help="Legal balls with no run of any kind.")})
            c.section("Batting first and chasing", "The same phases for the side batting first and the side chasing.")
            a, b = phase_rows(tp[tp.innings == 1]), phase_rows(tp[tp.innings == 2])
            idx = [p for p in c.PHASE_ORDER if p in a.index or p in b.index]
            a, b = a.reindex(idx), b.reindex(idx)
            t2 = pd.DataFrame({"Phase": idx, "Run rate batting first": (6 * a.runs / a.legal).round(2).values,
                               "Run rate chasing": (6 * b.runs / b.legal).round(2).values,
                               "Wickets per innings batting first": (a.wkts / a.inns).round(2).values,
                               "Wickets per innings chasing": (b.wkts / b.inns).round(2).values,
                               "Dot ball % batting first": (100 * a.dots / a.legal).round(1).values,
                               "Dot ball % chasing": (100 * b.dots / b.legal).round(1).values,
                               "Innings batting first": a.inns.fillna(0).astype(int).values,
                               "Innings chasing": b.inns.fillna(0).astype(int).values})
            c.pair_bar_chart(t2, "Phase", "Run rate batting first", "Run rate chasing",
                             names=("Batting first", "Chasing"), fmt=",.2f", title="Runs per over")
            c.table(t2, {k: c.col_2() for k in t2.columns if k.startswith(("Run rate", "Wickets"))}
                    | {k: c.col_1() for k in t2.columns if k.startswith("Dot")}
                    | {k: INT for k in t2.columns if k.startswith("Innings")})
            c.note("Chasing innings end when the target is reached, so their death overs are fewer and often shorter.")

    with t_ov:
        if t_ov.open:
            side = st.segmented_control("Innings", ["Both", "Batting first", "Chasing"], key="ins_ov_side",
                                        default="Both", required=True)
            ov = c.in_scope(c.bbb_table("bbb_over"), shown_e)
            ov = ov if side == "Both" else ov[ov.innings == (1 if side == "Batting first" else 2)]
            g = ov.groupby("over").agg(inns=("inns", "sum"), legal=("legal", "sum"), runs=("runs", "sum"),
                                       wkts=("wkts", "sum")).reset_index()
            c.section("Over by over", based + " Each over's average over every innings that reached it.")
            t = pd.DataFrame({"Over": g.over.astype(str), "Innings": g.inns.astype(int),
                              "Runs per over": (g.runs / g.inns).round(2), "Wickets per over": (g.wkts / g.inns).round(3)})
            c.line_chart(t, "Over", "Runs per over", fmt=",.2f", title="Runs in the over")
            c.bar_chart(t, "Over", "Wickets per over", fmt=",.2f", title="Wickets in the over")
            c.table(t, {"Innings": INT, "Runs per over": c.col_2(help="Runs in the over (extras included) per innings "
                                                                    "that reached it."),
                        "Wickets per over": st.column_config.NumberColumn(format="%.3f", width="small")})
            c.note("Later overs rest on fewer innings: a chase that is won early never reaches them, and an innings "
                   "that is all out stops.")

    with t_pl:
        if t_pl.open:
            bp = c.in_scope(c.bbb_table("bbb_bat_phase"), shown_e)
            wp = c.in_scope(c.bbb_table("bbb_bowl_phase"), shown_e)
            opts = list(pd.concat([bp.groupby("player_id").runs.sum(), wp.groupby("player_id").legal.sum() * 0])
                        .groupby(level=0).sum().sort_values(ascending=False).index)
            if st.session_state.get("ins_player") not in opts:
                st.session_state.ins_player = int(opts[0])
            pid = st.selectbox("Player", [int(x) for x in opts], key="ins_player", format_func=c.name,
                               help="Players with ball-by-ball innings in the covered editions, most runs first.")
            mb, mw = bp[bp.player_id == pid], wp[wp.player_id == pid]
            c.section("Batting by phase", f"{c.short_name(pid)} in {label}: from his {int(mb.inns.sum())} phase innings "
                                          "whose ball-by-ball agrees with the scorecard.")
            if mb.empty or mb.faced.sum() == 0:
                c.empty(f"No batting with a ball-by-ball record for {c.short_name(pid)} here.")
            else:
                g = mb.groupby("phase").sum(numeric_only=True).reindex(c.PHASE_ORDER).dropna(how="all")
                ok = g.faced >= c.MIN_BALLS
                t = pd.DataFrame({"Phase": g.index, "Balls": g.faced.astype(int), "Runs": g.runs.astype(int),
                                  "Strike rate": np.where(ok, (100 * g.runs / g.faced).round(1), np.nan),
                                  "Outs": g.outs.astype(int),
                                  "Boundary %": np.where(ok, (100 * (g.fours + g.sixes) / g.faced).round(1), np.nan),
                                  "Dot ball %": np.where(ok, (100 * g.dots / g.faced).round(1), np.nan),
                                  "Sample": c.ball_sample(g.faced)})
                c.bar_chart(t, "Phase", "Strike rate", fmt=",.1f", title="Strike rate")
                c.table(t, {"Balls": INT, "Runs": INT, "Strike rate": c.col_1(help=c.HELP["SR"]), "Outs": INT,
                            "Boundary %": c.col_1(), "Dot ball %": c.col_1(help="Balls faced with no run off the bat."),
                            "Sample": c.col_text(width="small")})
            c.section("Bowling by phase", f"{c.short_name(pid)} in {label}.")
            if mw.empty or mw.legal.sum() == 0:
                c.empty(f"No bowling with a ball-by-ball record for {c.short_name(pid)} here.")
            else:
                g = mw.groupby("phase").sum(numeric_only=True).reindex(c.PHASE_ORDER).dropna(how="all")
                ok = g.legal >= c.MIN_BALLS
                t = pd.DataFrame({"Phase": g.index, "Overs": [c.overs(x) for x in g.legal], "Runs": g.runs.astype(int),
                                  "Wickets": g.wkts.astype(int),
                                  "Economy": np.where(ok, (6 * g.runs / g.legal).round(2), np.nan),
                                  "Dot ball %": np.where(ok, (100 * g.dots / g.legal).round(1), np.nan),
                                  "Boundary %": np.where(ok, (100 * (g.fours + g.sixes) / g.legal).round(1), np.nan),
                                  "Sample": c.ball_sample(g.legal)})
                c.bar_chart(t, "Phase", "Economy", fmt=",.2f", title="Runs per over")
                c.table(t, {"Overs": c.col_text(width="small"), "Runs": INT, "Wickets": INT,
                            "Economy": c.col_2(help=c.HELP["Econ"]),
                            "Dot ball %": c.col_1(help="Legal balls with no run to the bowler."),
                            "Boundary %": c.col_1(help="4s and 6s hit off him per 100 legal balls."), "Sample": c.col_text(width="small")})
            c.note(f"Rates are blank under {c.MIN_BALLS} balls in a phase (not enough); Small: under {c.SMALL_BALLS}. "
                   "Only his innings whose ball-by-ball figures equal his scorecard figures count.")

    with t_tm:
        if t_tm.open:
            role = st.segmented_control("View", ["Batting", "Bowling"], key="ins_tm_role", default="Batting", required=True)
            col = "team_id" if role == "Batting" else "opp_id"
            g = tp.groupby([col, "phase"]).agg(inns=("inns", "sum"), legal=("legal", "sum"), runs=("runs", "sum"),
                                               wkts=("wkts", "sum")).reset_index()
            w = g.pivot(index=col, columns="phase")
            n = tp[tp.phase == "Powerplay"].groupby(col).inns.sum()     # innings batted (or bowled): every innings has a powerplay
            rows = pd.DataFrame({"Team": [c.team_names().get(int(x), str(x)) for x in w.index], "Innings": n.reindex(w.index).fillna(0).astype(int).values})
            for ph, short in (("Powerplay", "PP"), ("Middle", "Middle"), ("Death", "Death")):
                legal = w["legal"][ph] if ph in w["legal"] else pd.Series(np.nan, index=w.index)
                rr = 6 * w["runs"][ph] / legal
                wk = w["wkts"][ph] / w["inns"][ph]
                enough = rows.Innings.values >= c.MIN_INNS
                rows[f"{short} run rate"] = np.where(enough, rr.round(2).values, np.nan)
                rows[f"{short} wickets per innings"] = np.where(enough, wk.round(2).values, np.nan)
            rows["Sample"] = c.count_label(rows.Innings)
            rows = rows.sort_values(["Innings", "Team"], ascending=[False, True])
            what = "scored" if role == "Batting" else "conceded"
            c.section(f"Phase profile: runs {what} and wickets {'lost' if role == 'Batting' else 'taken'}",
                      based + " Rates blank under 5 innings; Small under 10.")
            q = rows[rows["Death run rate"].notna()].sort_values("Death run rate", ascending=role != "Batting")
            if len(q):
                c.bar_chart(q, "Team", "Death run rate", fmt=",.2f", title=f"Death-over runs per over {what}")
                c.table(q, {k: (INT if k == "Innings" else c.col_2()) for k in q.columns if k not in ("Team", "Sample")}
                        | {"Sample": c.col_text(width="small")})
            thin = rows[rows["Death run rate"].isna()]
            if len(thin):
                c.note("Fewer than 5 innings here: " + ", ".join(thin.Team) + ".")
            if not len(q):
                c.thin(label, "innings per team")

c.note(c.bbb_cover_line())
c.footer()
