import cloudscraper
from datetime import datetime
import requests
import os

BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
CHAT_ID = os.environ["TG_CHAT_ID"]

def check_yarkon_availability(target_date="2025-11-14"):
    """Check if a specific date is available at Yarkon camping"""
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
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        response = scraper.post(url, json=payload)
        data = response.json()
        results = data["d"]["Availibility"]
        for day in results:
            date_ms = int(day["DayDate"].strip("/Date()\\/"))
            date = datetime.utcfromtimestamp(date_ms / 1000)
            date_str = date.strftime("%Y-%m-%d")
            if date_str == target_date and day["IsAvail"]:
                print(day)
                return True, date_str
        return False, None
    except Exception as e:
        print(f"Error checking availability: {e}")
        return False, None

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    r = requests.post(url, data=payload)
    return r.status_code == 200

def main():
    target_date = "2025-11-14"
    is_available, date = check_yarkon_availability(target_date)
    if is_available:
        message = (
            f"Yarkon camping is available for {date}!\n"
            f"Book now: https://www.parks.org.il/camping/חניון-לילה-גן-לאומי-ירקון/"
        )
        send_telegram_message(BOT_TOKEN, CHAT_ID, message)
    else:
        message = (
            f"Yarkon camping has no availablity for {target_date} :("
        )
        send_telegram_message(BOT_TOKEN, CHAT_ID, message)
    print(message)


if __name__ == "__main__":
    main()





