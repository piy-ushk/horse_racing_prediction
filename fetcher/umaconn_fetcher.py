"""
UmaConn 地方競馬DATA HTTP API fetcher.

Production: calls the UmaConn REST API to get local/regional race odds.
  Credentials required:
    UMACONN_API_KEY  — issued by UmaConn (set in .env)
    UMACONN_BASE_URL — API base URL (default: https://api.umaconn.com/v1)

Demo mode (DEMO_MODE=true): no-op; the JV-Link mock data is sufficient
for demo purposes.

UmaConn API reference: https://www.umaconn.com/api/docs
  Key endpoints used here:
    GET /races?date=YYYYMMDD           — list all local races for a date
    GET /odds/{race_id}                — win odds for each horse in a race
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from logger.operation_logger import get_logger

log = get_logger()


def enrich_odds(races: list, horses_by_race: dict) -> dict:
    """
    Fetch local/regional race data from UmaConn and merge into horses_by_race.
    For central JRA races already present, only adds UmaConn races/odds that
    were not already captured by JV-Link.
    Returns the (possibly enriched) horses_by_race dict.
    """
    if config.DEMO_MODE:
        log.info("UmaConn: DEMO MODE — skipping enrichment")
        return horses_by_race
    return _umaconn_enrich(races, horses_by_race)


def _umaconn_enrich(races: list, horses_by_race: dict) -> dict:
    import requests

    api_key = config.UMACONN_API_KEY
    base_url = config.UMACONN_BASE_URL.rstrip("/")

    if not api_key:
        log.warning("UmaConn: UMACONN_API_KEY not set — skipping")
        return horses_by_race

    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
    }

    # Determine the race date from the first race in the list
    race_date = races[0]["race_date"].replace("-", "") if races else ""
    if not race_date:
        return horses_by_race

    # Step 1: fetch all local races for the day
    try:
        resp = requests.get(
            f"{base_url}/races",
            params={"date": race_date},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        local_races = resp.json()  # list of race objects from UmaConn
    except Exception as exc:
        log.warning("UmaConn: failed to fetch race list — %s", exc)
        return horses_by_race

    # Step 2: for each local race, fetch odds and merge
    for lr in local_races:
        race_id = str(lr.get("race_id", ""))
        if not race_id:
            continue

        # Build a race dict compatible with our schema if not already present
        if race_id not in horses_by_race:
            races.append({
                "race_id": race_id,
                "race_name": lr.get("race_name", race_id),
                "race_date": races[0]["race_date"] if races else "",
                "venue": lr.get("venue", ""),
                "race_number": int(lr.get("race_number", 0)),
            })
            horses_by_race[race_id] = []

        try:
            resp = requests.get(
                f"{base_url}/odds/{race_id}",
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            odds_data = resp.json()  # {horse_id: {horse_name, horse_number, odds}, ...}
        except Exception as exc:
            log.warning("UmaConn: failed to fetch odds for race %s — %s", race_id, exc)
            continue

        existing_ids = {h["horse_id"] for h in horses_by_race[race_id]}
        for horse_id, info in odds_data.items():
            if horse_id in existing_ids:
                # Update existing odds if UmaConn value is more recent
                for h in horses_by_race[race_id]:
                    if h["horse_id"] == horse_id:
                        h["odds"] = float(info.get("odds", h["odds"]))
                        break
            else:
                horses_by_race[race_id].append({
                    "horse_id": horse_id,
                    "race_id": race_id,
                    "horse_name": info.get("horse_name", ""),
                    "horse_number": int(info.get("horse_number", 0)),
                    "odds": float(info.get("odds", 0)),
                })
        log.info("UmaConn: enriched race %s — %d horses", race_id, len(horses_by_race[race_id]))

    return horses_by_race
