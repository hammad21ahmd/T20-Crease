"""
data_files.py - where T20 Crease finds its one data file, dom_app.sqlite.

READ-ONLY for data. In this order:
  1. DOM_APP_DB (environment variable): a path to the file, for local runs and tests.
  2. The local build: private/domestic/dom_app.sqlite in the folder above the project (where the export writes it).
  3. Hosted (Streamlit Community Cloud): the file is not on the server, so it is downloaded once per server from the
     private GitHub repo named in Streamlit secrets, with a fine-grained read-only token (never in any file):
       [data]
       github_token = "..."        Contents: read-only, on that one repo only
       repo = "<owner>/t20-crease-files"
     The download goes to a temporary folder named after app/DATA_VERSION (written by tools/publish.py), so a new
     publish downloads a fresh file and an unchanged one reuses it. A failed download shows a plain message on the page
     and no details (no token, no URL).
T20C_GITHUB_API overrides the GitHub API address (the release checks use a local stand-in).
"""

import os
import shutil
import sqlite3
import tempfile
import urllib.request
from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent
ROOT = APP.parent
NAME = "dom_app.sqlite"
LOCAL = ROOT.parent / "private" / "domestic" / NAME
CHECK_TABLE = "export_info"
AGENT = "t20-crease-app"


def api():
    return os.environ.get("T20C_GITHUB_API", "https://api.github.com").rstrip("/")


def data_version():
    f = APP / "DATA_VERSION"
    return f.read_text(encoding="utf-8").strip() if f.exists() else "local"


def valid(path):
    """True if path is a readable SQLite file holding the app's tables."""
    try:
        if not Path(path).is_file():
            return False
        con = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
        try:
            ok = con.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            return ok and con.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (CHECK_TABLE,)).fetchone() is not None
        finally:
            con.close()
    except sqlite3.Error:
        return False


def local_path():
    """The local file if there is one (DOM_APP_DB first), else None."""
    env = os.environ.get("DOM_APP_DB")
    if env:
        return Path(env)
    return LOCAL if LOCAL.exists() else None


def _secrets():
    try:
        cfg = st.secrets["data"]
        return str(cfg["github_token"]), str(cfg["repo"])
    except Exception:            # no secrets file, no [data] section or a missing key
        return None, None


def _download(dest, token, repo):
    req = urllib.request.Request(f"{api()}/repos/{repo}/contents/{NAME}",
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw",
                                          "User-Agent": AGENT, "X-GitHub-Api-Version": "2022-11-28"})
    tmp = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)
    os.replace(tmp, dest)


@st.cache_resource(show_spinner="Loading the data")
def locate():
    """(path or None, problem or ''). Cached once per server process."""
    p = local_path()
    if p is not None:
        return (p, "") if valid(p) else (None, "The local data file could not be opened.")
    token, repo = _secrets()
    if not token or not repo:
        return None, ("The data file is not set up here. Locally, build it with export/domestic_export.py; on the hosted "
                      "app, add the [data] secrets.")
    folder = Path(tempfile.gettempdir()) / "t20_crease_data" / data_version()
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / NAME
    try:
        if not valid(dest):
            _download(dest, token, repo)
    except Exception:            # network, token or a missing file: no details on screen
        return None, "The data could not be loaded. Please try again in a few minutes."
    return (dest, "") if valid(dest) else (None, "The data could not be loaded. Please try again in a few minutes.")
