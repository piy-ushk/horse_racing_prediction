"""
Prediction engine: sorts horses by odds (ascending) and assigns marks.

Mark mapping (from spec):
  Rank 1 → ◎ (honmei / top pick)
  Rank 2 → ○ (taikou)
  Rank 3 → ▲ (tanana)
  Rank 4 → △ (renka)
  Rank 5+ → (no mark assigned)
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from logger.operation_logger import get_logger

log = get_logger()

MARKS = {1: "◎", 2: "○", 3: "▲", 4: "△"}


def generate_predictions(race: dict, horses: list) -> list:
    """
    Returns a list of prediction dicts sorted by rank (best first).
    Each dict has: race_id, horse_id, mark, odds, rank
    """
    sorted_horses = sorted(horses, key=lambda h: h["odds"])
    predictions = []
    for rank, horse in enumerate(sorted_horses, start=1):
        mark = MARKS.get(rank, "")
        pred = {
            "race_id": race["race_id"],
            "horse_id": horse["horse_id"],
            "mark": mark,
            "odds": horse["odds"],
            "rank": rank,
        }
        predictions.append(pred)
        if mark:
            log.info(
                "Prediction: %s  %s %s  odds=%.1f",
                race["race_name"], mark, horse["horse_name"], horse["odds"],
            )
    log.info("Generated %d predictions for %s", len(predictions), race["race_name"])
    return predictions
