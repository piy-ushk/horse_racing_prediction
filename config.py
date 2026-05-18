import os
import json
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "predictions.db"
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = BASE_DIR / "data" / "settings.json"

# WordPress REST API (ConoHa WING)
WP_BASE_URL = os.getenv("WP_BASE_URL", "https://www.keiba-tips.top")
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

# Access restriction parameter
AUTH_PARAM = "auth"
AUTH_VALUE = "line_only"

# JRA-VAN Data Lab — JV-Link Windows COM
JRAVAN_LICENSE_KEY = os.getenv("JRAVAN_LICENSE_KEY", "")
JRAVAN_SOFTWARE_ID = os.getenv("JRAVAN_SOFTWARE_ID", "")

# UmaConn 地方競馬DATA HTTP API
UMACONN_API_KEY = os.getenv("UMACONN_API_KEY", "")
UMACONN_BASE_URL = os.getenv("UMACONN_BASE_URL", "https://api.umaconn.com/v1")

# Demo mode: uses mock data instead of real JV-Link / UmaConn
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# Flask demo server
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = False


def get_schedule() -> tuple[int, int]:
    """Read schedule time from settings.json; fall back to env vars."""
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return int(data["scheduled_hour"]), int(data["scheduled_minute"])
        except (KeyError, ValueError, OSError):
            pass
    return int(os.getenv("SCHEDULED_HOUR", 9)), int(os.getenv("SCHEDULED_MINUTE", 30))


def save_schedule(hour: int, minute: int) -> None:
    """Persist schedule time to settings.json so the admin change survives restarts."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if SETTINGS_FILE.exists():
        try:
            existing = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    existing["scheduled_hour"] = hour
    existing["scheduled_minute"] = minute
    SETTINGS_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Convenience attributes read at import time (use get_schedule() for live values)
SCHEDULED_HOUR, SCHEDULED_MINUTE = get_schedule()
