"""Tweet templates and the text checker.

Templates are fixed sentences filled with display strings from the checks,
so every draft is deterministic and checkable against the app. Each one
contains a date, and none states a direction or recommends anything.
"""
import re

import config

TEMPLATES = {
    "dd_cross": "{asset} closed {dd} below its all-time high of {ath}, set on {ath_date}. As of {asof}.",
    "dd_new_max": (
        "{asset} is {dd} below its {ath_date} high of {ath}, its deepest drawdown in data going back to {start}. "
        "The previous deepest was {prev_dd}, on {prev_date}. As of {asof}."
    ),
    "new_ath": (
        "{asset} closed at a new all-time high of {price} on {asof}, {days} days after its "
        "previous high on {prev_peak_date}. In between, it fell as far as {max_dd} below that high."
    ),
    "underwater_milestone": (
        "{asset} has now spent {days} days below its {ath_date} high. {depth} As of {asof}."
    ),
    "vol30_extreme": "{asset}'s 30-day volatility is {vol}, its {high_low} {since}. As of {asof}.",
    "tail_day": (
        "{asset} {verb} {abs_ret} on {date}, more than three standard deviations from its "
        "average day over the past year. {count_phrase}"
    ),
    "ytd_day": "{asset} {verb} {abs_ret} on {date}, its largest one-day move in either direction in {year} so far.",
    "ytd_week": (
        "{asset} {verb} {abs_ret} in the week ending {week_end}, its largest weekly move "
        "in either direction in {year} so far."
    ),
}

# Words that would turn a measurement into a prediction or a recommendation.
BANNED = re.compile(
    r"\b(buy|sell|should|will|could|expect\w*|bottom\w*|signal\w*|alert\w*|opportunit\w*|"
    r"decoupl\w*|diversif\w*|hedge\w*|outperform\w*|best)\b|top is in",
    re.IGNORECASE,
)
DATE = re.compile(r"\b\d{1,2} [A-Z][a-z]{2} \d{4}\b")
MAX_LEN = 280


def render(note):
    """Returns (note text, tweet draft)."""
    text = TEMPLATES[note["check"]].format(**note["fields"])
    with_disclaimer = f"{text}\n\n{config.DISCLAIMER}"
    tweet = with_disclaimer if len(with_disclaimer) <= MAX_LEN else text
    return text, tweet


def lint(tweet):
    """Returns a list of problems. Empty means the draft can go in the digest."""
    problems = []
    if len(tweet) > MAX_LEN:
        problems.append(f"{len(tweet)} characters (limit {MAX_LEN})")
    body = tweet.replace(config.DISCLAIMER, "")
    banned = sorted({m.group(0).lower() for m in BANNED.finditer(body)})
    if banned:
        problems.append("banned words: " + ", ".join(banned))
    if not DATE.search(body):
        problems.append("no date")
    return problems
