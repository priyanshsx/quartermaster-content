"""The check registry: what counts as notable, one function per check.

Every check takes an asset's analysed frame (from the app's quant_analyzer),
its spec and the run context, and returns None or a note:

    {"key": cooldown scope, "score": 0-100 rarity, "headline": short label,
     "fields": display strings for the template}

Checks only read columns the app already computed. They never recompute a
metric, so the figures match the app.
"""
import pandas as pd

import config
import fmt


def _base_fields(df, spec):
    return {"asset": spec["display"], "asof": fmt.date(df.index[-1])}


# --- Drawdown checks -------------------------------------------------------

def check_dd_cross(df, spec, ctx):
    """Drawdown crossed −10/−20/−30/−50% on the way down."""
    dd = df["drawdown"]
    if len(dd) < 2:
        return None
    prev, curr = dd.iloc[-2], dd.iloc[-1]
    crossed = [t for t in config.DD_THRESHOLDS if prev > t >= curr]
    if not crossed:
        return None
    t = min(crossed)
    level = round(-t * 100)
    return {
        "key": str(level),
        "score": {10: 30, 20: 50, 30: 65, 50: 85}.get(level, 50),
        "headline": f"crossed −{level}% from its high",
        "fields": {
            **_base_fields(df, spec),
            "dd": fmt.pct(curr),
            "ath": fmt.price(df["close"].max(), spec["currency"]),
            "ath_date": fmt.date(df["close"].idxmax()),
        },
    }


def check_dd_new_max(df, spec, ctx):
    """The current drawdown just went deeper than any earlier one in the history."""
    dd = df["drawdown"]
    if len(dd) < 2 or dd.iloc[-1] >= 0:
        return None
    peak_date = df["close"].idxmax()            # start of the current drawdown
    before = dd.loc[:peak_date]
    if len(before) < 2 or before.min() >= 0:
        return None
    record = before.min()
    prev, curr = dd.iloc[-2], dd.iloc[-1]
    if not (prev >= record > curr):             # fires on the day it crosses the old record
        return None
    return {
        "key": "",
        "score": 95,
        "headline": "deepest drawdown in its history",
        "fields": {
            **_base_fields(df, spec),
            "dd": fmt.pct(curr),
            "ath": fmt.price(df["close"].max(), spec["currency"]),
            "ath_date": fmt.date(peak_date),
            "prev_dd": fmt.pct(record),
            "prev_date": fmt.date(before.idxmin()),
            "start": fmt.date(df.index[0]),
        },
    }


def check_new_ath(df, spec, ctx):
    """A new all-time closing high after a meaningful time below the previous one."""
    dd = df["drawdown"]
    if len(dd) < 2 or dd.iloc[-1] < 0 or dd.iloc[-2] >= 0:
        return None
    asof = df.index[-1]
    prev_peak = df["close"].iloc[:-1].idxmax()
    days = (asof - prev_peak).days
    if days < config.NEW_ATH_MIN_UNDERWATER_DAYS:
        return None
    between = dd.loc[prev_peak:]
    return {
        "key": "",
        "score": min(60 + days / 20, 95),
        "headline": "new all-time high",
        "fields": {
            **_base_fields(df, spec),
            "price": fmt.price(df["close"].iloc[-1], spec["currency"]),
            "days": f"{days:,}",
            "prev_peak_date": fmt.date(prev_peak),
            "max_dd": fmt.pct(between.min()),
        },
    }


def check_underwater_milestone(df, spec, ctx):
    """Calendar days since the all-time high just passed 100, 200, 365, 500..."""
    dd = df["drawdown"]
    if len(dd) < 2 or dd.iloc[-1] >= 0:
        return None
    peak = df["close"].idxmax()
    d_now = (df.index[-1] - peak).days
    d_prev = (df.index[-2] - peak).days
    hit = [m for m in config.UNDERWATER_MILESTONES if d_prev < m <= d_now]
    if not hit:
        return None
    m = max(hit)
    since = dd.loc[peak:]
    if since.idxmin() == df.index[-1]:
        depth = f"It is {fmt.pct(dd.iloc[-1])} below that high, its deepest point so far."
    else:
        depth = (f"Its deepest point was {fmt.pct(since.min())} below, on {fmt.date(since.idxmin())}; "
                 f"it is {fmt.pct(dd.iloc[-1])} below today.")
    return {
        "key": str(m),
        "score": min(35 + m / 20, 85),
        "headline": f"{m} days below its high",
        "fields": {
            **_base_fields(df, spec),
            "days": f"{d_now:,}",
            "ath_date": fmt.date(peak),
            "depth": depth,
        },
    }


# --- Volatility ------------------------------------------------------------

def check_vol30_extreme(df, spec, ctx):
    """30-day volatility is its highest or lowest in at least a year."""
    v = df["rolling_vol_annualized"].dropna()
    if len(v) < 2:
        return None
    asof, curr = v.index[-1], v.iloc[-1]
    if (asof - v.index[0]).days < 2 * config.VOL_MIN_SPAN_DAYS:
        return None                              # not enough history to call it unusual
    hist = v.iloc[:-1]
    for kind, comparable in (("highest", hist[hist >= curr]), ("lowest", hist[hist <= curr])):
        if len(comparable):
            last = comparable.index[-1]
            span = (asof - last).days
            since = f"since {fmt.date(last)}"
        else:
            span = (asof - v.index[0]).days
            since = f"in the available history (since {fmt.date(v.index[0])})"
        if span >= config.VOL_MIN_SPAN_DAYS:
            return {
                "key": kind,
                "score": min(40 + span / 365 * 10, 85),
                "headline": f"30-day volatility at its {kind} in {span / 365:.1f} years",
                "fields": {
                    **_base_fields(df, spec),
                    "vol": fmt.pct(curr),
                    "high_low": kind,
                    "since": since,
                },
            }
    return None


# --- Daily moves -----------------------------------------------------------

def _move_fields(df, spec, ret, when):
    return {
        **_base_fields(df, spec),
        "verb": "rose" if ret >= 0 else "fell",
        "abs_ret": fmt.pct(ret),
        "date": fmt.date(when),
    }


def check_ytd_day(df, spec, ctx):
    """Yesterday was the largest one-day move of the calendar year, up or down."""
    r = df["daily_returns"].dropna()
    if r.empty:
        return None
    asof = r.index[-1]
    ytd = r[r.index.year == asof.year]
    if len(ytd) < config.YTD_MIN_OBS or abs(r.iloc[-1]) < ytd.abs().max():
        return None
    return {
        "key": "",
        "score": 50,
        "headline": f"largest one-day move of {asof.year}",
        "fields": {**_move_fields(df, spec, r.iloc[-1], asof), "year": str(asof.year)},
    }


def check_ytd_week(df, spec, ctx):
    """Monday runs only: last week was the largest weekly move of the year."""
    if ctx["run_date"].weekday() != 0:
        return None
    w = df["close"].resample("W").last().pct_change().dropna()
    if w.empty:
        return None
    last = w.index[-1]
    ytd = w[w.index.year == last.year]
    if len(ytd) < 8 or abs(w.iloc[-1]) < ytd.abs().max():
        return None
    return {
        "key": "",
        "score": 55,
        "headline": f"largest weekly move of {last.year}",
        "fields": {
            **_base_fields(df, spec),
            "verb": "rose" if w.iloc[-1] >= 0 else "fell",
            "abs_ret": fmt.pct(w.iloc[-1]),
            "week_end": fmt.date(last),
            "year": str(last.year),
        },
    }


def check_tail_day(df, spec, ctx):
    """Yesterday's move was beyond 3 standard deviations of the trailing year."""
    r = df["daily_returns"].dropna()
    n = spec["trading_days"]
    if len(r) < n + 1:
        return None
    window = r.iloc[-(n + 1):-1]
    mu, sd = window.mean(), window.std()
    if not sd or pd.isna(sd):
        return None
    z = (r.iloc[-1] - mu) / sd
    if abs(z) < config.TAIL_SIGMA:
        return None
    count = int(((r.iloc[-n:] - mu).abs() > config.TAIL_SIGMA * sd).sum())
    count_phrase = (
        "That is the only such day in the last 12 months."
        if count <= 1
        else f"That has happened {count} times in the last 12 months, including this one."
    )
    return {
        "key": "",
        "score": min(60 + (abs(z) - config.TAIL_SIGMA) * 7, 95),
        "headline": f"a {abs(z):.1f}-standard-deviation day",
        "fields": {**_move_fields(df, spec, r.iloc[-1], r.index[-1]), "count_phrase": count_phrase},
    }


# --- Registry ----------------------------------------------------------------
# cooldown_days applies per (check, asset, key). "screenshot" tells you which
# app view to capture until screenshots are automated.

CHECKS = {
    "dd_new_max": {"fn": check_dd_new_max, "cooldown_days": 30,
                   "screenshot": "Quantitative Metrics → full history → drawdown chart"},
    "dd_cross": {"fn": check_dd_cross, "cooldown_days": 30,
                 "screenshot": "Quantitative Metrics → full history → drawdown chart"},
    "new_ath": {"fn": check_new_ath, "cooldown_days": 7,
                "screenshot": "Quantitative Metrics → full history → price chart"},
    "underwater_milestone": {"fn": check_underwater_milestone, "cooldown_days": 365,
                             "screenshot": "Quantitative Metrics → full history → drawdown chart"},
    "vol30_extreme": {"fn": check_vol30_extreme, "cooldown_days": 14,
                      "screenshot": "Quantitative Metrics → 2Y → risk vs return chart"},
    "tail_day": {"fn": check_tail_day, "cooldown_days": 1,
                 "screenshot": "Quantitative Metrics → 1Y → return distribution"},
    "ytd_day": {"fn": check_ytd_day, "cooldown_days": 1,
                "screenshot": "Quantitative Metrics → YTD → price chart"},
    "ytd_week": {"fn": check_ytd_week, "cooldown_days": 7,
                 "screenshot": "Quantitative Metrics → YTD → price chart"},
}


def run_checks(ticker, df, spec, ctx):
    """Runs every check on one asset. Returns a list of notes."""
    notes = []
    for name, check in CHECKS.items():
        result = check["fn"](df, spec, ctx)
        if result:
            notes.append({"check": name, "ticker": ticker, **result})
    return notes
