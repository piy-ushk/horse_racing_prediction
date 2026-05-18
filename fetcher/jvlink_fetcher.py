"""
JV-Link fetcher (JRA-VAN Data Lab).

Production: connects to the JRA-VAN JV-Link Windows COM API.
  Requirements:
    1. JV-Link software installed on the Windows VPS
    2. Your license key (JRAVAN_LICENSE_KEY) registered in JV-Link settings
    3. JRAVAN_SOFTWARE_ID set to the software ID issued at jra-van.jp
    4. pip install pywin32

Demo mode (DEMO_MODE=true): returns realistic mock data so the full
pipeline can run without the real COM service.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from logger.operation_logger import get_logger
from fetcher.mock_data import generate_mock_races, generate_mock_horses

log = get_logger()

# JRA-VAN real-time dataspec for win/place odds (単勝・複勝オッズ)
_DATASPEC_ODDS = "0B11"
# Buffer size for one JV-Link record (bytes)
_RECORD_BUFFER = 1024


def fetch_races_and_odds(race_date: str) -> tuple[list, dict]:
    """
    Returns (races, horses_by_race_id).
      races            — list of race dicts
      horses_by_race_id — {race_id: [horse_dict, ...]}
    """
    if config.DEMO_MODE:
        return _mock_fetch(race_date)
    return _jvlink_fetch(race_date)


def _mock_fetch(race_date: str):
    log.info("JV-Link: DEMO MODE — generating mock data for %s", race_date)
    races = generate_mock_races(race_date, num_races=3)
    horses_by_race = {}
    for race in races:
        horses = generate_mock_horses(race, num_horses=8)
        horses_by_race[race["race_id"]] = horses
        log.info("JV-Link: %d horses for %s", len(horses), race["race_name"])
    log.info("JV-Link: mock fetch done — %d races", len(races))
    return races, horses_by_race


def _jvlink_fetch(race_date: str):
    """
    Real JV-Link integration via Windows COM (JVDTLab.JVLink).

    Data flow:
      JVInit  → authenticate with software ID
      JVRTOpen → open real-time odds stream (dataspec 0B11)
      JVGetsR → read records until exhausted
      JVClose → release the connection

    Record parsing follows JRA-VAN JVDATA format specification.
    Field offsets are defined in the official JRA-VAN data layout document.
    """
    try:
        import win32com.client
    except ImportError:
        raise RuntimeError(
            "pywin32 is required for JV-Link. "
            "Run: pip install pywin32  "
            "Or set DEMO_MODE=true to use mock data."
        )

    software_id = config.JRAVAN_SOFTWARE_ID
    if not software_id:
        raise RuntimeError(
            "JRAVAN_SOFTWARE_ID not set. "
            "Register your software at jra-van.jp and set the issued ID in .env."
        )

    log.info("JV-Link: connecting to COM server (software_id=%s)...", software_id)
    jvlink = win32com.client.Dispatch("JVDTLab.JVLink")

    rc = jvlink.JVInit(software_id)
    if rc != 0:
        raise RuntimeError(f"JVInit failed — code {rc}. Check software ID and JV-Link settings.")

    log.info("JV-Link: opening real-time odds stream (dataspec=%s)...", _DATASPEC_ODDS)
    rc = jvlink.JVRTOpen(_DATASPEC_ODDS, "")
    if rc < 0:
        raise RuntimeError(f"JVRTOpen failed — code {rc}")

    races: list[dict] = []
    horses_by_race: dict[str, list] = {}

    try:
        while True:
            rc, buff, filename = jvlink.JVGetsR("", _RECORD_BUFFER, "")
            if rc == 0:
                break
            if rc < 0:
                log.error("JV-Link: JVGetsR error — code %d", rc)
                break

            parsed = _parse_odds_record(buff)
            if parsed is None:
                continue

            race_id = parsed["race_id"]
            if race_id not in horses_by_race:
                races.append({
                    "race_id": race_id,
                    "race_name": parsed["race_name"],
                    "race_date": race_date,
                    "venue": parsed["venue"],
                    "race_number": parsed["race_number"],
                })
                horses_by_race[race_id] = []

            horses_by_race[race_id].append({
                "horse_id": parsed["horse_id"],
                "race_id": race_id,
                "horse_name": parsed["horse_name"],
                "horse_number": parsed["horse_number"],
                "odds": parsed["odds"],
            })
    finally:
        jvlink.JVClose()

    log.info("JV-Link: fetch complete — %d races", len(races))
    return races, horses_by_race


def _parse_odds_record(buff: str) -> dict | None:
    """
    Parse one JVDATA 0B11 record (fixed-width text).

    Field layout (JRA-VAN JVDATA format spec, record type 0B11):
      Bytes  1- 2  : record type  ("0B")
      Bytes  3- 4  : data classification
      Bytes  5-12  : race date      (YYYYMMDD)
      Bytes 13-14  : venue code     (keibajyo code, 2 digits)
      Bytes 15-16  : race number    (2 digits, zero-padded)
      Bytes 17-18  : horse number   (umaban, 2 digits)
      Bytes 19-xx  : horse name     (fixed-width, shift-JIS or UTF-8 depending on version)
      Bytes xx-xx  : odds (tansho)  (e.g. "0105" = 10.5x, divide by 10)

    NOTE: Exact offsets depend on the JV-Link version and record subtype.
    Consult the official JRA-VAN JVDATA layout specification PDF for your
    version and adjust the slice indices below accordingly.
    """
    if not buff or len(buff) < 30:
        return None

    try:
        record_type = buff[0:2].strip()
        if record_type not in ("0B", "OB"):
            return None

        date_str_raw = buff[4:12].strip()   # YYYYMMDD
        venue_code = buff[12:14].strip()
        race_num_str = buff[14:16].strip()
        horse_num_str = buff[16:18].strip()

        if not race_num_str.isdigit() or not horse_num_str.isdigit():
            return None

        race_number = int(race_num_str)
        horse_number = int(horse_num_str)

        # Horse name: 36 bytes, shift-JIS encoded in the JVDATA spec
        horse_name_raw = buff[18:54]
        try:
            horse_name = horse_name_raw.encode("latin-1").decode("cp932").strip()
        except Exception:
            horse_name = horse_name_raw.strip()

        # Tansho (win) odds stored as integer tenths, e.g. 0105 → 10.5
        odds_raw = buff[54:58].strip()
        odds = int(odds_raw) / 10.0 if odds_raw.isdigit() else 0.0
        if odds <= 0:
            return None

        venue_name = _VENUE_CODE_MAP.get(venue_code, venue_code)
        race_date = f"{date_str_raw[:4]}-{date_str_raw[4:6]}-{date_str_raw[6:8]}"
        race_id = f"{date_str_raw}_{venue_code}_{race_number:02d}"
        horse_id = f"{race_id}_H{horse_number:02d}"

        return {
            "race_id": race_id,
            "race_name": f"{venue_name}{race_number}R",
            "race_date": race_date,
            "venue": venue_name,
            "race_number": race_number,
            "horse_id": horse_id,
            "horse_name": horse_name,
            "horse_number": horse_number,
            "odds": odds,
        }
    except Exception as exc:
        log.debug("JV-Link: failed to parse record — %s", exc)
        return None


# JRA-VAN venue codes → display names
_VENUE_CODE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}
