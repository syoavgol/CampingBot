# CampingBot

Python scripts and GitHub Actions workflows for checking Israel Nature and Parks Authority availability and sending Telegram alerts when target dates become available.

The repository currently includes two alert jobs:

- `parksTelegramBot.py` checks camping availability through the camping API.
- `parksVisitTelegramBot.py` checks park visit availability through the Checkfront inventory API.

Both scripts are designed to run on a schedule in GitHub Actions, but they can also be run locally.

## How It Works

Each script reads configuration from environment variables, checks availability for the configured dates and site IDs, and builds a status message.

A Telegram message is sent only when at least one requested date is available. When no requested dates are available, the result is logged but no Telegram notification is sent.

## Requirements

- Python 3.11 or newer
- A Telegram bot token
- A Telegram chat ID

Install dependencies locally:

```powershell
python -m pip install --upgrade pip
pip install requests cloudscraper
```

`parksVisitTelegramBot.py` only needs `requests`; `parksTelegramBot.py` needs both `requests` and `cloudscraper`.

## Telegram Setup

1. Create a Telegram bot with [BotFather](https://t.me/BotFather).
2. Save the bot token as `TG_BOT_TOKEN`.
3. Send a message to the bot from the target chat.
4. Get the chat ID and save it as `TG_CHAT_ID`.

## Camping Availability Alert

Script:

```powershell
python parksTelegramBot.py
```

Environment variables:

- `TG_BOT_TOKEN`: Telegram bot token.
- `TG_CHAT_ID`: Telegram chat ID.
- `CAMPING_TARGET_DATES`: comma-separated dates in `YYYY-MM-DD` format.
- `HOTEL_ID`: comma-separated configured hotel IDs.

Example:

```powershell
$env:TG_BOT_TOKEN = "123456:telegram-token"
$env:TG_CHAT_ID = "123456789"
$env:CAMPING_TARGET_DATES = "2026-06-01,2026-06-02"
$env:HOTEL_ID = "22"
python parksTelegramBot.py
```

Configured camping IDs are defined in `HOTEL_CONFIGS` inside `parksTelegramBot.py`.

## Park Visit Availability Alert

Script:

```powershell
python parksVisitTelegramBot.py
```

Environment variables:

- `TG_BOT_TOKEN`: Telegram bot token.
- `TG_CHAT_ID`: Telegram chat ID.
- `PARK_VISIT_TARGET_DATES`: comma-separated dates in `YYYY-MM-DD` format.
- `PARK_ITEM_ID`: comma-separated Checkfront item IDs.
- `PARK_CATEGORY_ID`: Checkfront category ID.

Example:

```powershell
$env:TG_BOT_TOKEN = "123456:telegram-token"
$env:TG_CHAT_ID = "123456789"
$env:PARK_VISIT_TARGET_DATES = "2026-06-01,2026-06-02"
$env:PARK_ITEM_ID = "12345,67890"
$env:PARK_CATEGORY_ID = "123"
python parksVisitTelegramBot.py
```

## GitHub Actions

The repository includes scheduled workflows under `.github/workflows`.

`alert.yml` runs `parksTelegramBot.py` at `05:00` and `17:00` UTC, which is `08:00` and `20:00` in Israel during UTC+3.

`park-visit-alert.yml` runs `parksVisitTelegramBot.py` every hour.

Both workflows can also be triggered manually from the GitHub Actions tab with `workflow_dispatch`.

## GitHub Secrets and Variables

Add these repository secrets:

- `TG_BOT_TOKEN`
- `TG_CHAT_ID`

For the camping workflow, add these as either repository secrets or repository variables:

- `CAMPING_TARGET_DATES`
- `HOTEL_ID`

For the park visit workflow, add these as either repository secrets or repository variables:

- `PARK_VISIT_TARGET_DATES`
- `PARK_ITEM_ID`
- `PARK_CATEGORY_ID`

Secrets are preferable for sensitive values. Repository variables are useful for non-sensitive values such as target dates and public site IDs.

## Notes

- Dates must use `YYYY-MM-DD` format.
- Multiple dates and IDs should be comma-separated.
- The scripts log unavailable dates to the workflow output.
- Telegram notifications are sent only when availability is found.
