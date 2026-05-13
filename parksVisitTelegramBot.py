import os
import sys
import traceback
from datetime import datetime

import requests

from telegram_notifier import send_telegram_message


BASE_URL = "https://checkfrontcom.checkfront.com/reserve/inventory/"


def build_booking_url(park_item_id, park_category_id):
    return (
        "https://checkfrontcom.checkfront.com/reserve/"
        f"?inline=1&category_id={park_category_id}&item_id={park_item_id}"
        "&options=category_select%2Chidedates"
        "&provider=droplet&ssl=1&src=https%3A%2F%2Fwww.parks.org.il"
    )


def _log(msg):
    print(f"[ParksVisitBot] {msg}", flush=True)


def load_config():
    """Read env vars with clear logging; exits if required vars are missing."""
    required = (
        "TG_BOT_TOKEN",
        "TG_CHAT_ID",
        "PARK_VISIT_TARGET_DATES",
        "PARK_ITEM_ID",
        "PARK_CATEGORY_ID",
    )
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
    raw_park_item_ids = os.environ["PARK_ITEM_ID"]
    park_item_ids = _parse_park_item_ids(raw_park_item_ids)
    park_category_id = _parse_numeric_id(os.environ["PARK_CATEGORY_ID"], "PARK_CATEGORY_ID")

    _log(f"TG_BOT_TOKEN present (length {len(token)})")
    _log(f"TG_CHAT_ID present (length {len(chat_id)})")
    _log(f"PARK_ITEM_ID parsed {len(park_item_ids)} value(s): {park_item_ids}")
    _log(f"PARK_CATEGORY_ID parsed value: {park_category_id}")

    return token, chat_id, target_dates, park_item_ids, park_category_id


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


def _parse_park_item_ids(raw):
    park_item_ids = []
    seen = set()

    for part in raw.split(","):
        park_item_id = part.strip()
        if not park_item_id or park_item_id in seen:
            continue

        if not park_item_id.isdigit():
            raise ValueError(
                "PARK_ITEM_ID must list numeric Checkfront item IDs as comma-separated values"
            )

        seen.add(park_item_id)
        park_item_ids.append(park_item_id)

    if not park_item_ids:
        raise ValueError(
            "PARK_ITEM_ID must list at least one Checkfront item ID as comma-separated values"
        )

    return park_item_ids


def _parse_numeric_id(raw, env_name):
    value = raw.strip()
    if not value.isdigit():
        raise ValueError(f"{env_name} must be a numeric Checkfront ID")

    return value


def check_availability(
    target_date: str, park_item_id: str, park_category_id: str
) -> bool | None:
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
        "filter_item_id": park_item_id,
        "filter_category_id": park_category_id,
        "ssl": "1",
        "provider": "droplet",
        "customer_id": "",
        "original_start_date": "",
        "original_end_date": "",
        "date": "",
        "language": "",
        "cacheable": "1",
        "item_id": park_item_id,
        "view": "",
        "category_id": park_category_id,
        "start_date": target_date,
        "end_date": target_date,
        "cf-month": cf_month,
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": build_booking_url(park_item_id, park_category_id),
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


def availability_for_target_dates(target_dates, park_item_id, park_category_id):
    available = []
    unavailable = []
    not_found = []

    for target_date in target_dates:
        result = check_availability(target_date, park_item_id, park_category_id)

        if result is True:
            available.append(target_date)
            _log(f"park_item_id={park_item_id} {target_date}: available")
        elif result is False:
            unavailable.append(target_date)
            _log(f"park_item_id={park_item_id} {target_date}: not available")
        else:
            not_found.append(target_date)
            _log(
                f"park_item_id={park_item_id} {target_date}: not found in returned calendar window"
            )

    return available, unavailable, not_found


def main():
    _log("Starting parks visit availability check")

    try:
        bot_token, chat_id, target_dates, park_item_ids, park_category_id = load_config()
        results = []
        for park_item_id in park_item_ids:
            results.append(
                (
                    park_item_id,
                    *availability_for_target_dates(
                        target_dates, park_item_id, park_category_id
                    ),
                )
            )
    except ValueError as e:
        _log(f"ERROR: Invalid configuration: {e}")
        sys.exit(1)
    except Exception as e:
        _log(f"ERROR checking availability: {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)

    message_sections = []
    has_available_dates = False

    for park_item_id, available, unavailable, not_found in results:
        if available:
            has_available_dates = True
            message_sections.append(
                f"Park item {park_item_id} visit is available for "
                + ", ".join(available)
                + "!"
            )
            message_sections.append(
                f"Book now: {build_booking_url(park_item_id, park_category_id)}"
            )

        if unavailable:
            message_sections.append(
                f"No park item {park_item_id} visit availability for "
                + ", ".join(unavailable)
                + "."
            )

        if not_found:
            message_sections.append(
                f"Park item {park_item_id} dates not found in returned calendar window: "
                + ", ".join(not_found)
                + "."
            )

    message = "\n\n".join(message_sections)

    if has_available_dates:
        send_telegram_message(bot_token, chat_id, message, log=_log)

    _log(f"Result message: {message}")


if __name__ == "__main__":
    main()
