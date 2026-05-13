import requests


def send_telegram_message(bot_token, chat_id, message, log=None):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
    }

    if log is not None:
        log("Sending Telegram notification...")

    r = requests.post(url, data=payload, timeout=30)
    ok = r.status_code == 200

    if log is not None:
        if ok:
            log("Telegram send OK (HTTP 200)")
        else:
            log(f"Telegram send failed: HTTP {r.status_code}")
            preview = (r.text or "")[:500].replace("\r", " ").replace("\n", " ")
            log(f"Telegram response preview: {preview!r}")

    return ok
