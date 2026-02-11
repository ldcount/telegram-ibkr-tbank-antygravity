# PRD — Telegram Portfolio Balance Bot (T‑Bank + IBKR + Bybit + OKX)

## 1) Project overview and the goal
Build a Telegram bot in Python that polls four platforms on a schedule and sends a concise balance summary:
- **T‑Bank (T‑Invest API)**: total portfolio value in **RUB** (cash + positions)
- **IBKR (Interactive Brokers)**: **Net Liquidation Value (NLV)** in **USD**
- **Bybit + OKX**: total account equity in **USD** (assume **USDT = USD** for valuation)

The bot sends **one Telegram message** per run with:
1) 3 platform lines (original currency/valuation)
2) 2 total lines: grand total in **USD** and **RUB** using a current FX rate.

**Schedule**: every **2 hours**, only during daytime window **08:00–20:00 Europe/Paris** (inclusive).
Typical run times: 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00.

**Key security constraints**
- Use **read-only** API keys everywhere.
- Secrets stored in `.env` and excluded via `.gitignore`.
- No static IP → **do not rely on IP allowlisting** (where optional). Compensate with strict read-only scopes, minimal permissions, and careful secret handling.

**IBKR constraint**
- Do **not** run IBKR Client Portal Gateway on the VPS.
- Preferred approach: use **IBKR Flex Web Service** to programmatically generate and retrieve a pre-configured **Flex Query** that includes the account NLV (report data is generated via HTTPS without running a gateway process).  
  Sources: IBKR Flex Web Service overview and enabling steps. citeturn0search0turn1search2turn1search5turn1search12

---

## 1b) User story
As an investor with accounts across multiple platforms, I want an automated Telegram summary of my balances every 2 hours during the day, so I can track my net worth quickly without logging into each service.

---

## 1c) In-scope / Out-of-scope

### In-scope (v1)
- Telegram message delivery to one chat.
- Scheduled polling (08:00–20:00 Europe/Paris, every 2 hours).
- Read-only balance retrieval:
  - T‑Bank: total portfolio value (RUB) via `GetPortfolio`.
  - IBKR: Net Liquidation Value (USD) via Flex Web Service + Flex Query template.
  - Bybit: total equity/wallet balance (USD) via v5 account endpoints.
  - OKX: total account equity (USD) via v5 account balance endpoints.
- FX conversion RUB↔USD for totals (external FX provider).
- Strong error handling:
  - Partial failure: still send message with missing parts flagged.
  - Total failure (all platforms fail): still send message (error summary).

### Out-of-scope (v1)
- Trading, transfers, withdrawals.
- Per-asset portfolio breakdown (positions list, PnL by symbol).
- Historical storage / charts / database.
- Multi-user support.
- Web dashboard.

---

# 2) Core functionality

## 2a) User interface
Telegram-only.

**Optional v1.1**: `/now` command to force an immediate run.

---

## 2b) Input
All inputs are environment variables (loaded from `.env`).

Categories:
- Telegram BOT API key 
- Platform credentials (T‑Bank token, IBKR flex token & query id, Bybit key/secret, OKX key/secret/passphrase)
- Schedule window configuration
- FX provider configuration (choose by yourself)

---

## 2c) Processing (per run)
Use all releval libraries or APIs that are native or reccomended for each platform. Like pybit for Bybit.
1. Load config from environment variables.
2. Fetch balances:
   - T‑Bank total portfolio value in RUB via OperationsService `GetPortfolio`.
   - IBKR NLV via Flex Web Service:
     - Use an existing Flex Query template configured in Client Portal, requested via HTTPS using a Flex token.
   - Bybit total equity/wallet balance via v5 endpoint.
   - OKX account balance via `/api/v5/account/balance` (read permission).
3. Fetch FX rate USD↔RUB:
   - Use ECB SDMX web service (or another configured provider) and cache for TTL. citeturn0search7turn0search3turn0search15
4. Compute:
   - `crypto_usd = bybit_usd + okx_usd`
   - `total_usd = ibkr_usd + crypto_usd + (tbank_rub / fx_rub_per_usd)`
   - `total_rub = tbank_rub + (ibkr_usd + crypto_usd) * fx_rub_per_usd`
5. Render message in fixed template (see Output).
6. Send Telegram message.
7. Log sanitized summary.

---

## 2d) Output
One Telegram message per run.

### Output message template
```
T‑Bank (RUB): <amount_rub> ₽
IBKR NLV (USD): $<amount_usd>
Crypto (USD): $<crypto_total_usd>  [Bybit $<bybit_usd> | OKX $<okx_usd>]

TOTAL (USD): $<total_usd>
TOTAL (RUB): <total_rub> ₽  (rate: <fx> RUB/USD, <timestamp>)
```

### Failure formatting rules
- If one platform fails, replace its line with:
  - `IBKR NLV (USD): ERROR (<short_reason>)`
- If FX fails, still send platform lines and include:
  - `TOTAL (USD): ERROR (FX unavailable)`
  - `TOTAL (RUB): ERROR (FX unavailable)`
- If all platforms fail, send:
  - 3 lines all with `ERROR`, totals with `ERROR`, and include a single-line footer: `All sources failed in this run`.

---

# 3) Technical requirements

## 3a) Libraries (Python)
Recommended:
- HTTP client: `httpx` (async) or `requests` (sync)
- Telegram: `python-telegram-bot` or raw Telegram Bot API calls via HTTP
- Scheduling:
  - `APScheduler` (CronTrigger for 08:00–20:00 every 2 hours, Europe/Paris), OR
  - `systemd timer` or `cron` running the script at those times
- Config: `python-dotenv`
- Logging: stdlib `logging` + custom redaction filter

---

## 3b) Functional modules and what they do
### `config`
- Load and validate env vars into a typed config object.

### `telegram_client`
- Send message to `TELEGRAM_CHAT_ID`.
- Handle Telegram errors (retry on transient errors / rate limits).

### `fx_rates`
- Fetch USD/RUB rate from configured provider.
- Cache rate for `FX_TTL_MINUTES`.
- Mark “STALE” if using cached rate older than TTL.

### `platforms/tbank_client`
- Call T‑Invest API OperationsService `GetPortfolio` and compute total portfolio value in RUB. citeturn1search1

### `platforms/ibkr_flex_client`
- Trigger & retrieve Flex Query reports via Flex Web Service (HTTPS).
- Parse NLV in USD from the returned report.
- Requires user to pre-create Flex Query template and enable Flex Web Service. citeturn1search2turn1search5turn1search12turn1search9
- NLV definition: cash + positions + options + bonds + funds (segment-specific). citeturn0search1

### `platforms/bybit_client`
- Query Bybit v5 wallet/equity (USD) using read-only API key. citeturn1search3turn1search13

### `platforms/okx_client`
- Query OKX v5 account balance (USD equity) with read permission. citeturn2search2turn2search8

### `aggregator`
- Normalize balances into a single internal model.
- Compute totals in USD and RUB.

### `scheduler`
- Enforce time window (08:00–20:00 Europe/Paris).
- Ensure “exactly once per slot” behavior even across restarts (optional v1, recommended v1.1).

---

## 3c) Rules of behavior
- **Read-only**: never place trades, never move funds.
- **No secrets leakage**:
  - Never log tokens, API keys, secrets, passphrases.
  - Never send secrets to Telegram.
- **Resilience**:
  - Partial success allowed and reported.
  - All-fail run still sends message with error summary.
- **Time window**:
  - Runs only between 08:00 and 20:00 Europe/Paris at 2-hour intervals.

---

## 3d) Breakdown of modules across files
Suggested repository structure:
```
/app
  main.py
  config.py
  scheduler.py
  telegram_client.py
  fx_rates.py
  aggregator.py
  /platforms
    __init__.py
    tbank_client.py
    ibkr_flex_client.py
    bybit_client.py
    okx_client.py
  /utils
    logging_redaction.py
    retry.py

.env              # not committed
.env.example      # committed
.gitignore
README.md
requirements.txt  # or pyproject.toml
```
Addtionally, create a file named 'functions.md' that would list all functions developped by you for this project. Each function should have a description of what it does, its parameters, and what it returns.
---

## 3e) Error handling
### Retries
- Use exponential backoff for transient failures:
  - HTTP timeouts
  - 5xx
  - 429 (respect retry hints where available)

### Platform-specific failures
- T‑Bank: auth/token errors, account not found.
- IBKR Flex: token expired / query not found / report generation failed. Flex tokens have an expiration (default 6 hours, configurable). citeturn1search9
- Bybit: signature errors / permission errors.
- OKX: signature errors / permission errors.
  - Note: OKX mentions behavior around API key expiration and conditions; ensure keys remain active by calling balance endpoints regularly and keep read-only permissions. citeturn2search3

### Message sending failures
- Telegram errors:
  - Retry on transient.
  - If Telegram fails, log the failure; optional v1.1: write the message to a local “dead letter” file.

---

## 3f) Acceptance criteria
1. **Scheduling**: Bot sends a message at **08:00, 10:00, …, 20:00** Europe/Paris every day.
2. **T‑Bank**: Message includes total portfolio value in RUB.
3. **IBKR**: Message includes account Net Liquidation Value in USD (from Flex report).
4. **Crypto**: Message includes Bybit USD and OKX USD and summed Crypto USD.
5. **Totals**: Message includes TOTAL USD and TOTAL RUB based on current FX rate (or explicit FX error).
6. **Partial failure**: If any platform fails, message still sends with clear `ERROR` for that line.
7. **All fail**: If all platforms fail, message still sends with errors for all lines.
8. **Security**: `.env` is ignored by git; secrets never appear in logs or repository.

---

## 3g) Edge cases
- FX provider unavailable → totals become `ERROR` or use cached FX marked `STALE`.
- One exchange returns equity in USDT and/or USD → treat as USD (USDT=USD assumption).
- Account has multiple subaccounts:
  - v1: sum across the default account scope for each platform client.
  - v1.1: configurable list of subaccounts.
- Restart during day:
  - v1: next scheduled run proceeds normally.
  - v1.1: prevent duplicate sending for the same time slot via lightweight state file.

---

## 3h) Non-functional requirements

### Token handling
- Store all secrets in `.env` only.
- Support “rotate by restart” (changing `.env` takes effect after restart).
- Never print tokens.

### Secrets via env vars
- `.env` local only, excluded by `.gitignore`.
- `.env.example` included in repo with empty placeholders.

### Logging (what must / must not be logged)
**Must log**
- Run time, which platforms succeeded/failed, elapsed time, FX age
- Sanitized error summary

**Must not log**
- API keys, secrets, passphrases, bearer tokens
- Full responses from private endpoints
- Full account numbers

### Env vars (to change the behavior)
See `.env.example` below.

### No Docker required
- Use Python venv + `systemd` service (recommended) or Windows Task Scheduler (if running on PC).

### Configuration and deployment
**Recommended deployment**: Linux VPS
- `systemd` service for the process OR `cron`/`systemd timer` for runs.
- Keep process minimal; one run can exit if scheduled externally.

---

# 4) Input & Output specifications

## 4a) Input

### Source
Environment variables loaded from `.env`.

### Format
Strings parsed into typed config (int, bool, etc.).

### Data validation
- Fail fast if required vars missing.
- Validate schedule window:
  - start hour = 8, end hour = 20
  - interval minutes = 120
- Validate Telegram config:
  - Bot token is non-empty
  - Chat ID is numeric

---

## 4b) Output

### Source / means
Telegram Bot API message send.

### Format (template)
See Output template above.

### Example I/O
**Example scheduled run**
- Trigger: 2026-02-11 10:00 Europe/Paris

**Example report**
```
T‑Bank (RUB): 1,234,567 ₽
IBKR NLV (USD): $12,345.67
Crypto (USD): $8,901.23  [Bybit $5,000.00 | OKX $3,901.23]

TOTAL (USD): $34,602.01
TOTAL (RUB): 3,194,300 ₽  (rate: 92.32 RUB/USD, 2026-02-11 09:55)
```

---

# Appendix A — Credential acquisition (high level)

## Telegram
- Create a bot via BotFather → obtain `TELEGRAM_BOT_TOKEN`.
- Obtain your `TELEGRAM_CHAT_ID` (via a helper bot or logging first inbound message).

## T‑Bank (T‑Invest API)
- Create an Invest API token in T‑Bank developer settings and use it as a Bearer token.
- Use OperationsService `GetPortfolio` to retrieve portfolio totals. citeturn1search1

## Bybit
- Create an API key with **read-only** permissions.
- Use v5 wallet/equity endpoints. citeturn1search3turn1search13

## OKX
- Create a V5 API key with **Permission: Read**. citeturn2search2
- Keep it active (the OKX FAQ describes expiration behavior; calling balance endpoints regularly helps). citeturn2search3

## IBKR (Flex Web Service)
- Enable Flex Web Service in IBKR Portal and generate a Flex token. citeturn1search5turn1search9
- Create a Flex Query template that includes Net Liquidation Value fields.
- The bot uses Flex Web Service HTTPS calls to generate/retrieve reports. citeturn0search0turn1search2turn1search12

---

# Appendix B — `.env.example`

```dotenv
# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Schedule
TIMEZONE=Europe/Paris
POLL_INTERVAL_MINUTES=120
WINDOW_START_HOUR=8
WINDOW_END_HOUR=20

# FX
FX_PROVIDER=ECB
FX_TTL_MINUTES=60

# T‑Bank (T‑Invest API)
TBANK_TOKEN=
TBANK_ACCOUNT_ID=

# IBKR (Flex Web Service)
IBKR_FLEX_TOKEN=
IBKR_FLEX_QUERY_ID=
IBKR_FLEX_REPORT_FORMAT=XML  # or TEXT, depending on your template

# Bybit
BYBIT_API_KEY=
BYBIT_API_SECRET=

# OKX
OKX_API_KEY=
OKX_API_SECRET=
OKX_API_PASSPHRASE=

# Behavior / logging
INCLUDE_CRYPTO_BREAKDOWN=true
LOG_LEVEL=INFO
```
