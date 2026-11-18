"""Quartermaster Daily Notes — run once a day at 01:00 UTC.

    python run.py --dry-run              # print the digest, send nothing, save nothing
    python run.py --dry-run --only BTC-USD,ETH-USD
    python run.py                        # send to Telegram and start cooldowns

Pipeline: load (fetch → audit → analyse) → checks → cooldowns → rank →
render + text check → digest → Telegram → archive.
"""
import argparse
import logging
from datetime import datetime, timezone

import config
import fmt
import rank
import state
import templates
from checks import CHECKS, run_checks


def build_digest(data, skipped, run_date, con, top_n):
    """Returns (digest text, notes that made the digest)."""
    ctx = {"run_date": run_date}

    # 1. every check on every loaded asset
    fired = []
    for ticker, item in data.items():
        fired.extend(run_checks(ticker, item["df"], item["spec"], ctx))

    # 2. drop anything still on cooldown
    fresh = [n for n in fired
             if not state.on_cooldown(con, n, CHECKS[n["check"]]["cooldown_days"], run_date)]

    # 3. render and text-check before ranking, so a rejected draft can't take a slot
    rejected = []
    usable = []
    for n in fresh:
        n["text"], n["tweet"] = templates.render(n)
        problems = templates.lint(n["tweet"])
        if problems:
            rejected.append(f"{n['ticker']} {n['check']}: {'; '.join(problems)}")
        else:
            usable.append(n)

    top, n_assets = rank.rank(usable, top_n)

    # 4. the digest
    lines = [f"Daily Notes — {fmt.date(run_date)}"]
    if top:
        lines[0] += f" (top {len(top)} of {n_assets} assets)"
    else:
        lines.append("Nothing notable today.")

    for i, n in enumerate(top, 1):
        name = data[n["ticker"]]["spec"]["display"]
        block = [
            f"{i}. {name} — {n['headline']}",
            "",
            n["tweet"],
            "",
            f"Screenshot: {CHECKS[n['check']]['screenshot']} ({n['ticker']})",
        ]
        if n["also"]:
            block.append("Also today: " + "; ".join(o["headline"] for o in n["also"]))
        lines.append("\n".join(block))

    if skipped:
        lines.append("Skipped:\n" +"\n".join(f"{t} — {why}" for t, why in skipped))
    if rejected:
        lines.append("Rejected by the text check:\n" + "\n".join(rejected))

    return "\n\n".join(lines), top


def status_table(data):
    """Each asset's latest figures, for checking against Quantitative Metrics (full history)."""
    rows = [f"{'Asset':<10} {'Last bar':<12} {'Close':>12} {'All-time high':>14} {'ATH date':<12} "
            f"{'Drawdown':>9} {'30d vol':>8}"]
    for ticker, item in data.items():
        df, ccy = item["df"], item["spec"]["currency"]
        rows.append(
            f"{ticker:<10} {fmt.date(df.index[-1]):<12} {fmt.price(df['close'].iloc[-1], ccy):>12} "
            f"{fmt.price(df['close'].max(), ccy):>14} {fmt.date(df['close'].idxmax()):<12} "
            f"{fmt.signed_pct(df['drawdown'].iloc[-1]):>9} {fmt.pct(df['rolling_vol_annualized'].iloc[-1]):>8}"
        )
    return "\n".join(rows) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Quartermaster Daily Notes")
    parser.add_argument("--dry-run", action="store_true", help="print only; no Telegram, no cooldowns saved")
    parser.add_argument("--only", help="comma-separated tickers, e.g. BTC-USD,ETH-USD")
    parser.add_argument("--top", type=int, default=config.TOP_N)
    parser.add_argument("--status", action="store_true",
                        help="also print each asset's latest figures, to compare against the app")
    args = parser.parse_args()

    config.LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=config.LOG_DIR / "run.log", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    from data import load_all  # imported here: pulls in the app's engine
    run_date = datetime.now(timezone.utc).date()
    only = set(args.only.split(",")) if args.only else None

    data, skipped = load_all(only)
    logging.info("loaded %d assets, skipped %d", len(data), len(skipped))

    if args.status:
        print(status_table(data))

    con = state.connect(config.DB_PATH)
    digest, top = build_digest(data, skipped, run_date, con, args.top)
    print(digest)

    if args.dry_run:
        logging.info("dry run: %d notes, nothing sent", len(top))
        return

    from telegram_send import send_message
    send_message(digest)
    state.record(con, top, run_date)
    logging.info("sent %d notes", len(top))


if __name__ == "__main__":
    main()
