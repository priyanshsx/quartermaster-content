"""Loads every asset through the app's own pipeline: fetch → audit → analyse.

Nothing here computes a figure itself. Prices come from the app's fetch_asset,
the audit is the app's tick_inspector, and every metric comes from the app's
quant_analyzer, so a note can never disagree with what the app shows.
"""
import pandas as pd
import streamlit.logger as streamlit_logger

import config  # noqa: F401  (must come first: puts the app on sys.path)

# The engine's st.cache_data decorators warn ("No runtime found") when the
# engine is imported outside a running app. The functions work normally, so
# raise Streamlit's log level BEFORE importing the engine.
streamlit_logger.set_log_level("error")

from assets import ASSET_SPECS, get_spec  # noqa: E402
from engine import MAX_MISSING_DATES, fetch_asset, quant_analyzer, tick_inspector  # noqa: E402


def eligible_tickers(only=None):
    """Every ticker in the app's registry, minus stablecoins, config.EXCLUDE and config.EXCLUDE_MARKETS."""
    tickers = [
        t for t, a in ASSET_SPECS.items()
        if a.get("comparable", True)
        and t not in config.EXCLUDE
        and a["market"] not in config.EXCLUDE_MARKETS
    ]
    if only:
        tickers = [t for t in tickers if t in only]
    return tickers


def _days(rows):
    """'3 days, 12 Mar 2003 – 04 Jun 2007' for a frame of failing rows."""
    first, last = rows.index.min(), rows.index.max()
    span = f"{first:%d %b %Y}" if first == last else f"{first:%d %b %Y} – {last:%d %b %Y}"
    return f"{len(rows)} day{'s' if len(rows) != 1 else ''}, {span}"


def audit_reason(report):
    """One short line saying why an asset failed the Tick Inspector, with the days affected."""
    reasons = []
    if report["duplicates"]:
        reasons.append(f"duplicate dates ({report['duplicates']})")
    if report["excess_days"] > MAX_MISSING_DATES:
        reasons.append(f"missing dates ({report['excess_days']} excess days)")
    if len(report["corrupted_high_low"]):
        reasons.append(f"low above high ({_days(report['corrupted_high_low'])})")
    if len(report["negative_volume"]):
        reasons.append(f"negative volume ({_days(report['negative_volume'])})")
    if len(report["high_open_close"]):
        rows = report["high_open_close"]
        # how far above the high, as a share of the high: rounding errors are tiny
        excess = (rows[["open", "close"]].max(axis=1) / rows["high"] - 1).max()
        reasons.append(f"open or close above high ({_days(rows)}; largest excess {excess:.4%})")
    return ", ".join(reasons) or "failed audit"


def load_all(only=None):
    """Returns ({ticker: {"spec", "df"}}, [(ticker, reason), ...] for skipped assets)."""
    data, skipped = {}, []
    # fetch_asset itself drops today's unfinished session, so asking for
    # tomorrow as the end date returns every finished bar.
    end = pd.Timestamp.utcnow().date() + pd.Timedelta(days=1)

    for ticker in eligible_tickers(only):
        spec = get_spec(ticker)
        try:
            raw = fetch_asset(ticker, config.HISTORY_START, end)
        except Exception as e:  # network, Yahoo or empty-data errors
            skipped.append((ticker, f"download failed ({type(e).__name__})"))
            continue

        report = tick_inspector(raw, spec)
        if not report["is_healthy"]:
            skipped.append((ticker, audit_reason(report)))
            continue

        df = quant_analyzer(raw.copy(), ticker, spec)
        data[ticker] = {"spec": spec, "df": df}

    return data, skipped
