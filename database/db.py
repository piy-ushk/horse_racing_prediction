import sqlite3
from pathlib import Path
from datetime import date
import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def get_connection():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS races (
            race_id     TEXT PRIMARY KEY,
            race_name   TEXT NOT NULL,
            race_date   TEXT NOT NULL,
            venue       TEXT NOT NULL,
            race_number INTEGER NOT NULL,
            created_at  TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS horses (
            horse_id    TEXT PRIMARY KEY,
            race_id     TEXT NOT NULL,
            horse_name  TEXT NOT NULL,
            horse_number INTEGER NOT NULL,
            odds        REAL NOT NULL,
            FOREIGN KEY (race_id) REFERENCES races(race_id)
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id         TEXT NOT NULL,
            horse_id        TEXT NOT NULL,
            mark            TEXT NOT NULL,
            odds            REAL NOT NULL,
            rank            INTEGER NOT NULL,
            created_at      TEXT DEFAULT (datetime('now', 'localtime')),
            wp_page_id      INTEGER DEFAULT NULL,
            wp_page_url     TEXT DEFAULT NULL,
            FOREIGN KEY (race_id) REFERENCES races(race_id),
            FOREIGN KEY (horse_id) REFERENCES horses(horse_id),
            UNIQUE (race_id, horse_id)
        );
    """)
    conn.commit()
    conn.close()


def save_race(race: dict):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO races (race_id, race_name, race_date, venue, race_number)
           VALUES (:race_id, :race_name, :race_date, :venue, :race_number)""",
        race,
    )
    conn.commit()
    conn.close()


def save_horse(horse: dict):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO horses (horse_id, race_id, horse_name, horse_number, odds)
           VALUES (:horse_id, :race_id, :horse_name, :horse_number, :odds)""",
        horse,
    )
    conn.commit()
    conn.close()


def save_prediction(pred: dict):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO predictions (race_id, horse_id, mark, odds, rank)
           VALUES (:race_id, :horse_id, :mark, :odds, :rank)""",
        pred,
    )
    conn.commit()
    conn.close()


def update_wp_info(race_id: str, wp_page_id: int, wp_page_url: str):
    conn = get_connection()
    conn.execute(
        "UPDATE predictions SET wp_page_id=?, wp_page_url=? WHERE race_id=?",
        (wp_page_id, wp_page_url, race_id),
    )
    conn.commit()
    conn.close()


def get_races_for_date(race_date: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM races WHERE race_date=? ORDER BY venue, race_number", (race_date,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_predictions_for_race(race_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.*, h.horse_name, h.horse_number
           FROM predictions p
           JOIN horses h ON p.horse_id = h.horse_id
           WHERE p.race_id = ?
           ORDER BY p.rank""",
        (race_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def predictions_exist_for_date(race_date: str) -> bool:
    conn = get_connection()
    count = conn.execute(
        """SELECT COUNT(*) FROM predictions p
           JOIN races r ON p.race_id = r.race_id
           WHERE r.race_date = ?""",
        (race_date,),
    ).fetchone()[0]
    conn.close()
    return count > 0
