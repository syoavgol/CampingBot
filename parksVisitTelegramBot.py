import os
import sys
import traceback
from datetime import datetime

import requests

from telegram_notifier import send_telegram_message


BASE_URL = "https://checkfrontcom.checkfront.com/reserve/inventory/"
BOOKING_URL = (
    "https://checkfrontcom.checkfront.com/reserve/"
    "?inline=1&category_id=96&item_id=367"
    "&options=category_select%2Chidedates"
    "&provider=droplet&ssl=1&src=https%3A%2F%2Fwww.parks.org.il"
)

ITEM_ID = 367
CATEGORY_ID = 96


def _log(msg):
    print(f"[ParksVisitBot] {msg}", flush=True)


def load_config():
    """Read env vars with clear logging; exits if required vars are missing."""
    required = ("TG_BOT_TOKEN", "TG_CHAT_ID", "PARK_VISIT_TARGET_DATES")
    missing = [k for k in required if not os.environ.get(k)]

    if missing:
        _log(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    raw_dates = os.environ["PARK_VISIT_TARGET_DATES"]
    _log(f"PARK_VISIT_TARGET_DATES raw length={len(raw_dates)} character(s)")
    target_dates = _parse_target_dates(raw_dates)
    _log(f"Parsed {len(target_dates)} date(s): {target_dates}")

    token = os.environ["TG_BOT_TOKEN"]
    chat_id = os.environ["TG_CHAT_ID"]

    _log(f"TG_BOT_TOKEN present (length {len(token)})")
    _log(f"TG_CHAT_ID present (length {len(chat_id)})")

    return token, chat_id, target_dates


def _parse_target_dates(raw):
    dates = []
    seen = set()

    for part in raw.split(","):
        date_str = part.strip()
        if not date_str or date_str in seen:
            continue

        datetime.strptime(date_str, "%Y-%m-%d")
        seen.add(date_str)
        dates.append(date_str)

    if not dates:
        raise ValueError(
            "PARK_VISIT_TARGET_DATES must list at least one date as comma-separated YYYY-MM-DD values"
        )

    return dates


def check_availability(target_date: str) -> bool | None:
    """
    target_date format: YYYY-MM-DD
    returns:
        True  -> available
        False -> unavailable
        None  -> date not present in returned window
    """
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    cf_month = dt.strftime("%Y%m%d")
    key = dt.strftime("%Y%m%d")

    params = {
        "inline": "1",
        "header": "hide",
        "options": "category_select,hidedates",
        "src": "https://www.parks.org.il",
        "filter_item_id": str(ITEM_ID),
        "filter_category_id": str(CATEGORY_ID),
        "ssl": "1",
        "provider": "droplet",
        "customer_id": "",
        "original_start_date": "",
        "original_end_date": "",
        "date": "",
        "language": "",
        "cacheable": "1",
        "item_id": str(ITEM_ID),
        "view": "",
        "category_id": str(CATEGORY_ID),
        "start_date": target_date,
        "end_date": target_date,
        "cf-month": cf_month,
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BOOKING_URL,
    }

    with requests.Session() as session:
        response = session.get(BASE_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

    calendar_data = data.get("calendar_data", {})
    value = calendar_data.get(key)

    if value is None:
        return None

    return value == 1


def availability_for_target_dates(target_dates):
    available = []
    unavailable = []
    not_found = []

    for target_date in target_dates:
        result = check_availability(target_date)

        if result is True:
            available.append(target_date)
            _log(f"{target_date}: available")
        elif result is False:
            unavailable.append(target_date)
            _log(f"{target_date}: not available")
        else:
            not_found.append(target_date)
            _log(f"{target_date}: not found in returned calendar window")

    return available, unavailable, not_found


def main():
    _log("Starting parks visit availability check")

    try:
        bot_token, chat_id, target_dates = load_config()
        available, unavailable, not_found = availability_for_target_dates(target_dates)
    except ValueError as e:
        _log(f"ERROR: Invalid configuration: {e}")
        sys.exit(1)
    except Exception as e:
        _log(f"ERROR checking availability: {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)

    message_sections = []

    if available:
        message_sections.append(
            "Parks visit is available for " + ", ".join(available) + "!"
        )
        message_sections.append(f"Book now: {BOOKING_URL}")

    if unavailable:
        message_sections.append(
            "No parks visit availability for " + ", ".join(unavailable) + "."
        )

    if not_found:
        message_sections.append(
            "Dates not found in returned calendar window: " + ", ".join(not_found) + "."
        )

    message = "\n\n".join(message_sections)

    if available:
        send_telegram_message(bot_token, chat_id, message, log=_log)

    _log(f"Result message: {message}")


if __name__ == "__main__":
    main()
