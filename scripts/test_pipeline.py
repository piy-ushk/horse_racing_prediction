"""
End-to-end pipeline smoke test (demo mode only).

Verifies the full pipeline runs without errors and produces expected output.
Safe to run any time — uses mock data, does not touch WordPress or real APIs.

Usage:
    python scripts/test_pipeline.py
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DEMO_MODE"] = "true"

import config
from database import db
from fetcher.jvlink_fetcher import fetch_races_and_odds
from fetcher.umaconn_fetcher import enrich_odds
from predictor.engine import generate_predictions
from publisher.wordpress import publish_race

TEST_DATE = "2099-01-01"  # far-future date won't clash with real data


def run_smoke_test():
    print("\nPipeline Smoke Test (DEMO MODE)")
    print("-" * 40)

    # Init DB
    print("[1] Init database...")
    db.init_db()
    print("    OK")

    # Fetch
    print("[2] Fetch odds (mock)...")
    races, horses_by_race = fetch_races_and_odds(TEST_DATE)
    assert races, "No races returned"
    assert horses_by_race, "No horses returned"
    print(f"    OK — {len(races)} races, {sum(len(v) for v in horses_by_race.values())} horses")

    # Enrich (no-op in demo)
    print("[3] UmaConn enrichment (demo no-op)...")
    horses_by_race = enrich_odds(races, horses_by_race)
    print("    OK")

    # Generate predictions
    print("[4] Generate predictions...")
    all_predictions = []
    horses_flat = {}
    for race in races:
        horses = horses_by_race[race["race_id"]]
        preds = generate_predictions(race, horses)
        assert preds, f"No predictions for {race['race_name']}"
        top = preds[0]
        assert top["mark"] == "◎", f"Top mark should be ◎, got {top['mark']}"
        all_predictions.append((race, preds, horses))
        for h in horses:
            horses_flat[h["horse_id"]] = h
    print(f"    OK — {len(all_predictions)} races predicted")

    # Publish (static HTML in demo)
    print("[5] Publish (static HTML demo)...")
    for race, preds, _ in all_predictions:
        result = publish_race(race, preds, horses_flat)
        assert result.get("wp_page_url"), "Publisher returned no URL"
    print("    OK — static HTML files written to data/html/")

    print("\n[ALL CHECKS PASSED] Pipeline is working correctly.")
    return True


if __name__ == "__main__":
    try:
        ok = run_smoke_test()
        sys.exit(0 if ok else 1)
    except Exception as exc:
        print(f"\n[FAIL] {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
