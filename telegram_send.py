"""Sends the digest to Telegram through the Bot API (free)."""
import requests

import config

API = "https://api.telegram.org/bot{token}/{method}"
LIMIT = 4000  # Telegram's hard limit is 4096 characters per message


def _post(method, **kwargs):
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
    url = API.format(token=config.TELEGRAM_BOT_TOKEN, method=method)
    resp = requests.post(url, timeout=30, **kwargs)
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if not resp.ok or not body.get("ok"):
        # Never print the URL: it contains the bot token.
        raise RuntimeError(f"Telegram {method} failed: {resp.status_code} {body.get('description', '')}")
    return body


def _chunks(text):
    """Splits on blank lines so a note is never cut in half."""
    chunk = ""
    for block in text.split("\n\n"):
        if chunk and len(chunk) + len(block) + 2 > LIMIT:
            yield chunk
            chunk = ""
        chunk = f"{chunk}\n\n{block}" if chunk else block
    if chunk:
        yield chunk


def send_message(text):
    for chunk in _chunks(text):
        _post("sendMessage", data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": chunk,
            "disable_web_page_preview": True,
        })


def send_photo(path, caption=""):
    """For automated screenshots (next phase)."""
    with open(path, "rb") as f:
        _post("sendPhoto", data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption[:1024]},
              files={"photo": f})
