"""Settings for Quartermaster Daily Notes, and the link to the app's engine.

Import this module before anything from the app: it puts the app folder on
sys.path so that `from engine import ...` resolves to the same code the app runs.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_DIR = Path(__file__).resolve().parent
load_dotenv(REPO_DIR / ".env")

# --- Link to the app -------------------------------------------------------
# QM_APP_PATH is relative to this repo unless it is absolute.
APP_PATH = (REPO_DIR / os.environ.get("QM_APP_PATH", "../../quartermaster/app")).resolve()
if not (APP_PATH / "engine.py").exists():
    raise SystemExit(f"Can't find the app's engine.py at {APP_PATH}. Set QM_APP_PATH in .env.")
if str(APP_PATH) not in sys.path:
    sys.path.insert(0, str(APP_PATH))

# --- Secrets (from .env, never committed) ----------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Files (gitignored) ----------------------------------------------------
DB_PATH = REPO_DIR / "notes.sqlite"
LOG_DIR = REPO_DIR / "logs"

# --- Which assets ------------------------------------------------------------
# Every asset in the app's ASSET_SPECS is checked, except stablecoins
# ("comparable": False) and the ones listed here.
EXCLUDE = {
    "WETH-USD": "tracks ETH one-for-one, so its notes would duplicate Ethereum's",
}

# Whole markets left out for now. Indian equities are held back until the
# Indian equity announcement; remove "in_equity" from this set to include them.
EXCLUDE_MARKETS = {"in_equity"}

# Full history, as far back as Yahoo Finance has it.
HISTORY_START = "2000-01-01"

# --- Digest ------------------------------------------------------------------
TOP_N = 5

# --- Check thresholds ----------------------------------------------------------
DD_THRESHOLDS = [-0.10, -0.20, -0.30, -0.50]          # drawdown crossings that fire
UNDERWATER_MILESTONES = [100, 200, 365, 500, 730, 1000]  # calendar days below the high
VOL_MIN_SPAN_DAYS = 365        # volatility must be the most extreme in at least this many days
TAIL_SIGMA = 3.0               # a "tail day" is beyond this many standard deviations
NEW_ATH_MIN_UNDERWATER_DAYS = 30  # ignore new highs after only a brief dip
YTD_MIN_OBS = 30               # need this many trading days in the year before a "largest of the year" note

DISCLAIMER = "Historical measurements only. Not investment advice."

# --- Scheduling ----------------------------------------------------------------
# At login the network may not be up yet: if every download fails, wait and retry.
NETWORK_RETRIES = 3
NETWORK_RETRY_WAIT_SECONDS = 120
