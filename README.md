# T20 Crease

**Pakistan domestic T20 analytics.**

T20 Crease is a free, independent web app on Pakistan's domestic men's T20 cups, 2004/05 to 2025/26: 809 matches in
31 editions. It shows the numbers behind each competition and season (leaders, records, trends, teams, grounds,
players and ball-by-ball phases) and says plainly where a sample is thin or the record is incomplete.

T20 Crease is independent: it is not affiliated with, endorsed by or connected to any cricket board, tournament,
team or sponsor. Competition and team names are used only to say which matches the numbers come from.

## What is in it

Eight tabs: Home, Competitions (editions and a season recap), Leaderboards (with fielding and young talent),
Players (one player, or two compared), Records & Trends, Teams & Venues (with a head-to-head grid), Insights (ball by
ball, with a data confidence meter) and Method (every source and every rule). A search box at the top finds any
player, team or ground. Every page follows the competition and season picked at the top.

## Data credit

Scorecards, ball-by-ball records and player profiles: ESPNcricinfo. For players who also played the Pakistan Super
League, names and bowling styles were checked against Cricsheet.org data (ODC-BY) and Wikipedia (CC BY-SA). T20 Crease
only adds the numbers up; it shows no birth dates (birth year only). The Method tab lists every source and rule.

## Run it yourself

You need Python 3.13 and the data file `dom_app.sqlite` (it is not in this repository).

```
pip install -r requirements.txt
streamlit run app/Home.py
```

Run it from the repository folder so the theme in `.streamlit/config.toml` is used. The app looks for the data file in
this order: the path in the environment variable `DOM_APP_DB`; then `private/domestic/dom_app.sqlite` in the folder
above the repository; then, on a hosted server, a download from a private GitHub repository named in Streamlit secrets
(`[data]` with `github_token` and `repo`). If none works, the page says the data is not available.

## Known limits

- Ball-by-ball records cover 175 of the 809 matches; Insights uses them only where they agree with the scorecard
  (6 editions, 151 matches). Other numbers come from the scorecards.
- Partnerships name both batters for about two in three stands; older scorecards often do not say at which wicket a
  batter fell. The over a batter came in is often missing, especially in recent seasons.
- Run-out fielders are often not named in the source, so run-out boards and numbers are shown only where at least 95%
  of fielders are known.
- Ages on the young talent board are approximate (season year minus birth year); 76 players have no known birth year.
- Some scheduled matches are in no source (most likely abandoned without a ball); Method names them by edition.
- Teams are kept by name and ID: an older and a newer side of one city are not joined.
