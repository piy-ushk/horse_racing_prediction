"""
Mock race and odds data that simulates what JV-Link and UmaConn would return.
Used in DEMO_MODE=true so the system runs without real API subscriptions.
"""
from datetime import date
import random


VENUES = ["東京", "中山", "阪神", "京都", "小倉", "札幌", "函館", "福島", "新潟", "中京"]

HORSE_NAMES = [
    "ディープインパクト", "オルフェーヴル", "キタサンブラック", "アーモンドアイ",
    "ジェンティルドンナ", "ゴールドシップ", "ウオッカ", "ダイワスカーレット",
    "テイエムオペラオー", "ナリタブライアン", "シンボリルドルフ", "メジロマックイーン",
    "トウカイテイオー", "ミスターシービー", "タマモクロス", "スペシャルウィーク",
    "エルコンドルパサー", "グラスワンダー", "セイウンスカイ", "ステイゴールド",
    "マンハッタンカフェ", "タニノギムレット", "シンボリクリスエス", "ネオユニヴァース",
    "キングカメハメハ", "ハーツクライ", "ディープスカイ", "ロードカナロア",
    "フィエールマン", "コントレイル", "クロノジェネシス", "グランアレグリア",
]


def generate_race_id(race_date: str, venue: str, race_number: int) -> str:
    safe = venue.encode("utf-8").hex()[:4]
    return f"{race_date.replace('-', '')}_{safe}_{race_number:02d}"


def generate_horse_id(race_id: str, horse_number: int) -> str:
    return f"{race_id}_H{horse_number:02d}"


def generate_mock_races(race_date: str = None, num_races: int = 3) -> list:
    if race_date is None:
        race_date = date.today().strftime("%Y-%m-%d")

    rng = random.Random(race_date)
    chosen_venues = rng.sample(VENUES, min(num_races, len(VENUES)))
    races = []
    for i, venue in enumerate(chosen_venues, start=1):
        race_id = generate_race_id(race_date, venue, i)
        races.append({
            "race_id": race_id,
            "race_name": f"{venue}{i}R",
            "race_date": race_date,
            "venue": venue,
            "race_number": i,
        })
    return races


def generate_mock_horses(race: dict, num_horses: int = 8) -> list:
    rng = random.Random(race["race_id"])
    names = rng.sample(HORSE_NAMES, min(num_horses, len(HORSE_NAMES)))
    horses = []
    for i, name in enumerate(names, start=1):
        horse_id = generate_horse_id(race["race_id"], i)
        # Odds distributed roughly log-normal so some are clear favourites
        raw = rng.expovariate(0.5) + 1.1
        odds = round(raw, 1)
        horses.append({
            "horse_id": horse_id,
            "race_id": race["race_id"],
            "horse_name": name,
            "horse_number": i,
            "odds": odds,
        })
    return horses
