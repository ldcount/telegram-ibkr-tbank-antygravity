import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Path to the JSON file storing daily portfolio snapshots
_HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "portfolio_history.json",
)


def _load() -> dict:
    """Load the history JSON from disk. Returns empty dict on failure."""
    if not os.path.exists(_HISTORY_FILE):
        return {}
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load portfolio history: {e}")
        return {}


def _save(data: dict) -> None:
    """Persist the history dict to disk."""
    os.makedirs(os.path.dirname(_HISTORY_FILE), exist_ok=True)
    try:
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save portfolio history: {e}")


def save_snapshot(usd: float, rub: float) -> None:
    """
    Save (or overwrite) today's portfolio snapshot.

    Key format: "DD-MM-YYYY"
    Value: {"USD": <amount>, "RUB": <amount>}
    """
    today_key = datetime.now().strftime("%d-%m-%Y")
    data = _load()
    data[today_key] = {"USD": round(usd, 2), "RUB": round(rub, 2)}
    _save(data)
    logger.info(
        f"Portfolio snapshot saved for {today_key}: USD={usd:.2f}, RUB={rub:.2f}"
    )


def get_history(days: int = 30) -> list[dict]:
    """
    Return up to `days` most-recent daily snapshots, sorted newest-first.

    Each element: {"date": "DD-MM-YYYY", "USD": <float>, "RUB": <float>}
    """
    data = _load()

    # Build a list of (date_obj, key, values) for sorting
    entries = []
    for key, values in data.items():
        try:
            date_obj = datetime.strptime(key, "%d-%m-%Y")
            entries.append((date_obj, key, values))
        except ValueError:
            logger.warning(f"Skipping malformed date key in history: {key}")

    # Sort descending (newest first), take up to `days`
    entries.sort(key=lambda x: x[0], reverse=True)
    entries = entries[:days]

    return [
        {"date": key, "USD": vals.get("USD", 0.0), "RUB": vals.get("RUB", 0.0)}
        for _, key, vals in entries
    ]
