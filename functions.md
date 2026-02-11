# Functions Documentation

## App

### `main.py`
- `main()`: Entry point. Validates config and starts the `TelegramBot` polling loop.

### `config.py`
- `Config.validate()`: Checks if essential environment variables are set. Raises `ValueError` if missing.
- `Config.get_timezone_obj()`: Returns a `pytz.timezone` object based on the `TIMEZONE` env var.

### `aggregator.py`
- `Aggregator.get_portfolio_summary()`: Fetches balances from all configured platforms. Returns a dictionary with individual and total values in USD, plus an error dictionary.
- `Aggregator.format_message(summary)`: Takes the summary dictionary and formats it into the string template specified in the PRD.

### `telegram_client.py`
- `TelegramBot.__init__()`: Initializes the `Application`, registers the `/status` command handler, and schedules the daily jobs.
- `TelegramBot.status_command(update, context)`: Async handler for `/status`. Fetches data and replies to the user.
- `TelegramBot.scheduled_job(context)`: Async callback for the scheduled job. Fetches data and sends a message to the configured chat.
- `TelegramBot.run()`: Starts the bot polling loop using `run_polling()`.

## Platforms

### `bybit_client.py`
- `BybitClient.get_balance_usd()`: Connects to ByBit via `pybit`. Fetches the Unified Trading Account wallet balance and returns the total equity in USD.

### `okx_client.py`
- `OkxClient.get_balance_usd()`: Connects to OKX via `okx-sdk`. Fetches the account balance (`get_balance`) and extracts the total equity (`totalEq`) in USD.
