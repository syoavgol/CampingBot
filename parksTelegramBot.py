import cloudscraper

from datetime import datetime

import os

import requests

import sys

import traceback





def _log(msg):

    print(f"[CampingBot] {msg}", flush=True)





def load_config():

    """Read env vars with clear logging; exits if required vars are missing."""

    required = ("TG_BOT_TOKEN", "TG_CHAT_ID", "TARGET_DATES")

    missing = [k for k in required if not os.environ.get(k)]

    if missing:

        _log(f"ERROR: Missing environment variables: {', '.join(missing)}")

        sys.exit(1)



    raw_dates = os.environ["TARGET_DATES"]

    _log(f"TARGET_DATES raw length={len(raw_dates)} character(s)")

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

        d = part.strip()

        if d and d not in seen:

            seen.add(d)

            dates.append(d)

    if not dates:

        raise ValueError(

            "TARGET_DATES must list at least one date as comma-separated YYYY-MM-DD values"

        )

    return dates





def _fetch_yarkon_availability_days():

    """Fetch availability rows from the Yarkon camping API, or None on failure."""

    url = "https://secure-hotels.net/INPA/BE_Engine.aspx/getAvalibility"

    payload = {

        "hotelID": "22",

        "dsn": "",

        "lang": "heb",

        "days": 365,

        "fromdate": None,

        "enddate": None

    }

    try:

        _log("Requesting availability from API…")

        scraper = cloudscraper.create_scraper(

            browser={"browser": "chrome", "platform": "windows", "mobile": False}

        )

        response = scraper.post(url, json=payload)

        _log(f"API HTTP status={response.status_code}, response bytes={len(response.content)}")

        if response.status_code != 200:

            preview = response.text[:800].replace("\r", " ").replace("\n", " ")

            _log(f"Non-200 response preview: {preview!r}")



        data = response.json()

        avail = data["d"]["Availibility"]

        _log(f"Parsed JSON OK; Availibility rows={len(avail)}")

        return avail

    except Exception as e:

        _log(f"ERROR fetching availability: {type(e).__name__}: {e}")

        traceback.print_exc()

        return None





def availability_for_target_dates(target_dates):

    """

    From one API response, return (available_entries, missing_dates).

    Each entry is (date_str, rooms). missing_dates are targets with no row or not IsAvail.

    """

    results = _fetch_yarkon_availability_days()

    if results is None:

        _log("No availability data (fetch failed); treating all target dates as unavailable")

        return [], list(target_dates)



    by_date = {}

    for day in results:

        date_ms = int(day["DayDate"].strip("/Date()\\/"))

        date = datetime.utcfromtimestamp(date_ms / 1000)

        date_str = date.strftime("%Y-%m-%d")

        by_date[date_str] = day



    available = []

    missing = []

    for td in target_dates:

        day = by_date.get(td)

        if day and day["IsAvail"]:

            rooms = day.get("SumRoomsForSale", "N/A")

            available.append((td, rooms))

            _log(f"{td}: available (SumRoomsForSale={rooms})")

        else:

            missing.append(td)

            if day is None:

                _log(f"{td}: no matching day in API calendar")

            else:

                _log(f"{td}: day exists but IsAvail=false")

    return available, missing





def send_telegram_message(bot_token, chat_id, message):

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {

        "chat_id": chat_id,

        "text": message

    }

    _log("Sending Telegram notification…")

    r = requests.post(url, data=payload, timeout=30)

    ok = r.status_code == 200

    if ok:

        _log("Telegram send OK (HTTP 200)")

    else:

        _log(f"Telegram send failed: HTTP {r.status_code}")

        preview = (r.text or "")[:500].replace("\r", " ").replace("\n", " ")

        _log(f"Telegram response preview: {preview!r}")

    return ok





def main():

    _log("Starting Yarkon availability check")

    try:

        bot_token, chat_id, target_dates = load_config()

    except ValueError as e:

        _log(f"ERROR: Invalid configuration: {e}")

        sys.exit(1)



    available, missing = availability_for_target_dates(target_dates)

    if available:

        lines = [

            f"Yarkon camping is available for {d}! (reservations: {r})"

            for d, r in available

        ]

        body = "\n".join(lines)

        message = (

            f"{body}\n"

            f"Book now: https://www.parks.org.il/camping/חניון-לילה-גן-לאומי-ירקון/"

        )

        send_telegram_message(bot_token, chat_id, message)

    else:

        dates_joined = ", ".join(missing)

        message = f"Yarkon camping has no availability for {dates_joined} :("

    _log(f"Result message: {message}")





if __name__ == "__main__":

    main()


