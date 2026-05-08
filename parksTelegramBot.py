import cloudscraper

from datetime import datetime

import os

import requests

import sys

import traceback





HOTEL_CONFIGS = {
    "9": {
        "name": "חורשת טל",
        "booking_url": "https://www.parks.org.il/camping/חניון-לילה-גן-לאומי-חורשת-טל/",
    },
    "20": {
        "name": "הקסטל",
        "booking_url": "https://www.parks.org.il/camping/חניון-לילה-הקסטל/",
    },
    "22": {
        "name": "מקורות הירקון",
        "booking_url": "https://www.parks.org.il/camping/חניון-לילה-גן-לאומי-ירקון/",
    },
}


def resolve_hotel_config(hotel_id):

    cfg = HOTEL_CONFIGS.get(hotel_id)

    if cfg is None:

        known_ids = ", ".join(sorted(HOTEL_CONFIGS.keys()))

        raise ValueError(
            f"HOTEL_ID '{hotel_id}' is not configured. Known HOTEL_ID values: {known_ids}"
        )

    return cfg


def _log(msg):

    print(f"[CampingBot] {msg}", flush=True)





def load_config():

    """Read env vars with clear logging; exits if required vars are missing."""

    required = ("TG_BOT_TOKEN", "TG_CHAT_ID", "TARGET_DATES", "HOTEL_ID")

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
    raw_hotel_ids = os.environ["HOTEL_ID"]
    hotel_ids = _parse_hotel_ids(raw_hotel_ids)

    _log(f"TG_BOT_TOKEN present (length {len(token)})")

    _log(f"TG_CHAT_ID present (length {len(chat_id)})")
    _log(f"HOTEL_ID parsed {len(hotel_ids)} value(s): {hotel_ids}")

    return token, chat_id, target_dates, hotel_ids





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





def _parse_hotel_ids(raw):

    hotel_ids = []

    seen = set()

    for part in raw.split(","):

        hotel_id = part.strip()

        if hotel_id and hotel_id not in seen:

            seen.add(hotel_id)

            hotel_ids.append(hotel_id)

    if not hotel_ids:

        raise ValueError(

            "HOTEL_ID must list at least one value as comma-separated IDs (for example: 22,23)"

        )

    return hotel_ids




def _fetch_availability_days(hotel_id):

    """Fetch availability rows from the camping API, or None on failure."""

    url = "https://secure-hotels.net/INPA/BE_Engine.aspx/getAvalibility"

    payload = {

        "hotelID": hotel_id,

        "dsn": "",

        "lang": "heb",

        "days": 365,

        "fromdate": None,

        "enddate": None

    }

    try:

        _log(f"Requesting availability from API (hotelID={hotel_id})…")

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





def availability_for_target_dates(target_dates, hotel_id):

    """

    From one API response, return (available_entries, missing_dates).

    Each entry is (date_str, rooms). missing_dates are targets with no row or not IsAvail.

    """

    results = _fetch_availability_days(hotel_id)

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

    _log("Starting camping availability check")

    try:

        bot_token, chat_id, target_dates, hotel_ids = load_config()
        hotel_cfgs = {hotel_id: resolve_hotel_config(hotel_id) for hotel_id in hotel_ids}

    except ValueError as e:

        _log(f"ERROR: Invalid configuration: {e}")

        sys.exit(1)



    message_sections = []
    any_available = False

    for hotel_id in hotel_ids:

        hotel_cfg = hotel_cfgs[hotel_id]
        _log(f"Checking hotelID={hotel_id} ({hotel_cfg['name']})")

        available, missing = availability_for_target_dates(target_dates, hotel_id)

        if available:

            any_available = True
            lines = [

                f"{hotel_cfg['name']} is available for {d}! (reservations: {r})"

                for d, r in available

            ]
            lines.append(f"Book now: {hotel_cfg['booking_url']}")
            message_sections.append("\n".join(lines))

        else:

            dates_joined = ", ".join(missing)
            message_sections.append(
                f"{hotel_cfg['name']} has no availability for {dates_joined} :("
            )

    message = "\n\n".join(message_sections)

    if any_available:

        send_telegram_message(bot_token, chat_id, message)

    _log(f"Result message: {message}")





if __name__ == "__main__":

    main()


