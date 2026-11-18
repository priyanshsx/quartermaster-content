# Quartermaster Content

Daily Notes and research for [Quartermaster](https://quartermasterlabs.com), a historical market research tool for crypto, equities and commodities.

> Historical measurements only. Not investment advice.

## Daily Notes

A script that runs once a day, measures every asset Quartermaster covers, and finds what is **historically notable**: a drawdown crossing a round level, volatility at a multi-year extreme, a new all-time high, an unusually large day. The most notable items arrive as a Telegram digest with a ready-to-post draft for each. A person checks and schedules every post; nothing is published automatically.

Every figure comes from Quartermaster's own engine (`engine.py`), so a note always matches what the app shows.

### Requirements

- The Quartermaster app repository, checked out locally (this repo imports its engine).
- Python matching the app's version, and the pinned libraries in `requirements.txt`.
- A Telegram bot token and chat ID, for the digest.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in the values
```

`QM_APP_PATH` in `.env` points to the app's `app/` folder, relative to this repo.

### Running

```bash
python run.py --dry-run                  # print the digest; send nothing, save nothing
python run.py --dry-run --only BTC-USD   # one asset
python run.py                            # send to Telegram and start cooldowns
```

Run it daily at **01:00 UTC**, after the Bitcoin day, the US close and the Indian close have all finished.

### How it works

| Step | File |
|---|---|
| Fetch every asset, audit it with the Tick Inspector, analyse it | `data.py` |
| Run the checks (what counts as notable) | `checks.py` |
| Skip anything sent recently | `state.py` |
| Fill the templates and check the text | `templates.py` |
| One note per asset, most notable first | `rank.py` |
| Send the digest | `telegram_send.py` |
| Settings and thresholds | `config.py` |

An asset whose price data fails the audit is skipped and listed in one line.

### Checks

| Check | Fires when |
|---|---|
| `dd_cross` | The drawdown from the all-time high crosses −10%, −20%, −30% or −50% |
| `dd_new_max` | The current drawdown becomes the deepest in the asset's history |
| `new_ath` | A new all-time closing high after at least 30 days below the previous one |
| `underwater_milestone` | Days below the all-time high reach 100, 200, 365, 500, 730 or 1,000 |
| `vol30_extreme` | 30-day volatility is its highest or lowest in at least a year |
| `tail_day` | A daily move beyond three standard deviations of the past year |
| `ytd_day` | The largest one-day move of the calendar year so far |
| `ytd_week` | The largest weekly move of the calendar year so far (Monday runs) |

Every draft is checked before it reaches the digest: it must contain a date, stay within 280 characters, and use none of a list of words that would turn a measurement into a prediction or recommendation.

## Licence

To be decided.
