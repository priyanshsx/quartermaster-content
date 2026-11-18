"""Display formatting. Matches the app's own formats so a tweet reads the same as the screen."""

SYMBOLS = {"USD": "$", "INR": "₹", "GBP": "£"}


def date(ts):
    """12 Mar 2020 — the format the app uses."""
    return f"{ts:%d %b %Y}"


def pct(x):
    """Unsigned percentage to one decimal, as the app shows it: 30.4%."""
    return f"{abs(x):.1%}"


def signed_pct(x):
    """+12.3% or −8.1% (true minus sign)."""
    return f"+{x:.1%}" if x >= 0 else f"−{abs(x):.1%}"


def price(x, currency):
    """$126,080 · $2.31 · $0.0412 — enough decimals to be meaningful."""
    sym = SYMBOLS.get(currency, currency + " ")
    if x >= 100:
        return f"{sym}{x:,.0f}"
    if x >= 1:
        return f"{sym}{x:,.2f}"
    return f"{sym}{x:,.4f}"
