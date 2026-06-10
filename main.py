"""
Main pipeline entry point.

Execution order (mirrors the MVP workflow spec):
  1. Init database
  2. Fetch odds (JV-Link + UmaConn)
  3. Generate prediction marks
  4. Save predictions to SQLite  (fixed — won't change if re-run same day)
  5. Publish to WordPress (or static HTML in demo mode)
  6. Log completion

Intended to be run by Windows Task Scheduler at 09:30 AM daily.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from logger.operation_logger import get_logger
from database import db
from fetcher.jvlink_fetcher import fetch_races_and_odds
from fetcher.umaconn_fetcher import enrich_odds
from predictor.engine import generate_predictions
from publisher.wordpress import publish_race

log = get_logger()


def run(race_date: str | None = None):
    if race_date is None:
        race_date = date.today().strftime("%Y-%m-%d")

    log.info("=" * 50)
    log.info("Horse Racing Prediction Pipeline started  date=%s  demo=%s",
             race_date, config.DEMO_MODE)

    # Phase 1: Init database
    db.init_db()
    log.info("Database initialised")

    # Guard: don't overwrite predictions already generated today
    if db.predictions_exist_for_date(race_date):
        log.info("Predictions already exist for %s — skipping (fixed result)", race_date)
        return

    # Phase 2: Fetch odds (JRA from JV-Link + Local from UmaConn)
    races, horses_by_race = fetch_races_and_odds(race_date)
    horses_by_race = enrich_odds(races, horses_by_race, race_date)

    if not races:
        log.warning("No JRA or local races fetched for %s — pipeline aborted", race_date)
        return
    log.info("Odds fetched successfully — %d races total", len(races))

    # Phase 3 + 4: Generate predictions and save
    all_predictions = []
    for race in races:
        db.save_race(race)
        horses = horses_by_race.get(race["race_id"], [])
        for h in horses:
            db.save_horse(h)

        preds = generate_predictions(race, horses)
        for p in preds:
            db.save_prediction(p)
        all_predictions.append((race, preds, horses))

    log.info("Prediction generation completed — %d races saved", len(races))

    # Phase 5: Publish to WordPress
    horses_flat = {
        h["horse_id"]: h
        for horses in horses_by_race.values()
        for h in horses
    }
    published_urls = []
    for race, preds, _ in all_predictions:
        result = publish_race(race, preds, horses_flat)
        if result.get("wp_page_id"):
            db.update_wp_info(race["race_id"], result["wp_page_id"], result["wp_page_url"])
        published_urls.append(result["wp_page_url"])

    log.info("WordPress updated successfully — %d pages", len(published_urls))
    for url in published_urls:
        log.info("  → %s", url)

    log.info("Pipeline completed successfully")
    log.info("=" * 50)
    return published_urls


if __name__ == "__main__":
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    run(target_date)
