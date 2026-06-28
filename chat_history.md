# Norra AI - Chat History & Knowledge Log

## Session: June 28, 2026

### User Request
* The cron job runs but fails with "output too large" errors (probably fetching all data).
* How to see predictions posted (reducing confidence threshold or fixing pipeline).
* Telegram commands do nothing.
* Save every chat for knowledge.

### Our Analysis
1. **Cron Failure ("output too large")**: Caused by `print(response.text)` in `football_api.py` dumping massive JSON payloads (often 100KB+) to standard output. This can exceed cron-job.org's log response limit or Render log capacities, marking it failed.
2. **API Limits**: The app tries to fetch a full season of historical data (380+ fixtures) from the API on every cron run when training the model if the DB is empty. This instantly exhausts the daily 100-request free tier API quota.
3. **Low Confidence Skips**: When training fails or falls back to heuristics, prediction confidence drops to `65.0%`. Since the post threshold is hardcoded to `90.0%`, no predictions are ever posted.
4. **Telegram Commands Inactive**: The FastAPI app doesn't start the Telegram bot's polling process. The bot commands are defined in `telegram_bot.py` but never registered/run on startup.

### Proposed Solution
1. Remove/comment verbose `print(response.text)` from API functions in `football_api.py`.
2. Implement synthetic training data pre-population when the DB is empty, bypassing API calls for historical data.
3. Start the Telegram bot polling in a background thread in `app.py` on startup.
4. Set a configurable confidence post threshold in `.env` (default: `70.0%`).
5. Add an API rate-limit cutoff safeguard to prevent making network requests when the token limit is reached.
