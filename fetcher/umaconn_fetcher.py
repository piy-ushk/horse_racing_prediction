"""
UmaConn 地方競馬DATA fetcher — Windows COM DLL (NVDTLabLib.NVLink).

UmaConn is NOT an HTTP API. It is a local Windows COM library, mirroring
JV-Link but for regional/local racing (地方競馬). Method names use the
"NV" prefix instead of "JV".

Requirements:
  - UmaConn software installed: C:\\Windows\\SysWOW64\\NVDTLab.dll
  - License key (UMACONN_API_KEY) registered via the UmaConn GUI first run
  - 32-bit Python (the DLL is 32-bit only; 64-bit Python cannot load it)
  - pip install pywin32  (32-bit build)

COM ProgID : NVDTLabLib.NVLink
Init param : "UNKNOWN"  (literal string — the key is stored by the GUI)

Reference  : https://qiita.com/masachaco/items/7aa4afa4ca70d4eb93d9
             https://gist.github.com/miyamamoto/cbe26d18173fce119a3f6ef56e31d9d5
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from logger.operation_logger import get_logger

log = get_logger()

# NVLink dataspec for win/place odds — mirrors JV-Link "0B11"
# Confirm the exact code against the UmaConn official data spec PDF.
_DATASPEC_ODDS = "0B11"
_NV_BUFFER_SIZE = 110000


def enrich_odds(races: list, horses_by_race: dict, target_date: str) -> dict:
    """
    Fetch local/regional race odds from UmaConn COM and merge into horses_by_race.
    In demo mode this is a no-op; the JV-Link mock data is sufficient.
    Returns the (possibly enriched) horses_by_race dict.
    """
    if config.DEMO_MODE:
        log.info("UmaConn: DEMO MODE — skipping")
        return horses_by_race
    return _nvlink_fetch(races, horses_by_race, target_date)


def _nvlink_fetch(races: list, horses_by_race: dict, target_date: str) -> dict:
    """
    Real UmaConn integration via Windows COM (NVDTLabLib.NVLink).

    Data flow (mirrors JV-Link exactly, with NV prefix):
      NVInit("UNKNOWN")        — initialise (license resolved from GUI setup)
      NVOpen(dataspec, ...)    — open a data stream for today's odds
      loop NVRead(...)         — read fixed-width NVDATA records
      NVClose()                — release the connection

    NOTE: This DLL is 32-bit only. You must run Python (x86) 32-bit.
    """
    try:
        import win32com.client  # type: ignore
    except ImportError:
        raise RuntimeError(
            "pywin32 is required. Run: pip install pywin32  "
            "(use the 32-bit Python installer — NVDTLab.dll is 32-bit only)"
        )

    race_date_str = target_date.replace("-", "")
    fromtime = f"{race_date_str}000000"  # YYYYMMDDHHMMSS

    log.info("UmaConn: connecting to COM server (NVDTLabLib.NVLink)...")
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")

    rc = nvlink.NVInit("UNKNOWN")
    if rc != 0:
        raise RuntimeError(
            f"NVInit failed — code {rc}. "
            "Open the UmaConn GUI once to complete the initial setup and "
            "register the license key (UMACONN_API_KEY)."
        )

    log.info("UmaConn: opening odds stream (dataspec=%s from=%s)...", _DATASPEC_ODDS, fromtime)
    rc, read_count, dl_count, last_ts = nvlink.NVOpen(
        _DATASPEC_ODDS, fromtime, 4, 0, 0, ""
    )
    if rc < 0:
        if rc == -301:
            log.warning("UmaConn: No live local data available today or outside racing hours.")
            return horses_by_race
        raise RuntimeError(f"NVOpen failed — code {rc}")

    new_races: list[dict] = []
    new_horses: dict[str, list] = {}

    try:
        while True:
            rc, buff, size, filename = nvlink.NVRead("", _NV_BUFFER_SIZE, "")
            if rc == 0:
                break
            if rc < 0:
                log.error("UmaConn: NVRead error — code %d", rc)
                break

            parsed = _parse_odds_record(buff, race_date_str)
            if parsed is None:
                continue

            race_id = parsed["race_id"]
            if race_id not in new_horses:
                new_races.append({
                    "race_id": race_id,
                    "race_name": parsed["race_name"],
                    "race_date": parsed["race_date"],
                    "venue": parsed["venue"],
                    "race_number": parsed["race_number"],
                })
                new_horses[race_id] = []

            new_horses[race_id].append({
                "horse_id": parsed["horse_id"],
                "race_id": race_id,
                "horse_name": parsed["horse_name"],
                "horse_number": parsed["horse_number"],
                "odds": parsed["odds"],
            })
    finally:
        nvlink.NVClose()

    # Merge local races into the existing dict (which may contain JRA races)
    for race in new_races:
        rid = race["race_id"]
        if rid not in horses_by_race:
            races.append(race)
            horses_by_race[rid] = new_horses[rid]
            log.info(
                "UmaConn: added local race %s — %d horses",
                race["race_name"], len(new_horses[rid]),
            )
        else:
            # Update odds for horses already present from JV-Link
            existing = {h["horse_id"]: h for h in horses_by_race[rid]}
            for h in new_horses[rid]:
                if h["horse_id"] in existing:
                    existing[h["horse_id"]]["odds"] = h["odds"]
                else:
                    horses_by_race[rid].append(h)

    log.info("UmaConn: fetch complete — %d local races", len(new_races))
    return horses_by_race


def _parse_odds_record(buff: str, race_date: str) -> dict | None:
    """
    Parse one NVDATA odds record.

    The NVDATA format mirrors the JRA-VAN JVDATA layout.
    Field offsets follow the UmaConn data specification PDF.
    Adjust slice indices if the official spec differs from JV-Link.
    """
    if not buff or len(buff) < 30:
        return None
    try:
        record_type = buff[0:2].strip()
        if record_type not in ("0B", "OB"):
            return None

        venue_code   = buff[12:14].strip()
        race_num_str = buff[14:16].strip()
        horse_num_str = buff[16:18].strip()

        if not race_num_str.isdigit() or not horse_num_str.isdigit():
            return None

        race_number  = int(race_num_str)
        horse_number = int(horse_num_str)

        horse_name_raw = buff[18:54]
        try:
            horse_name = horse_name_raw.encode("latin-1").decode("cp932").strip()
        except Exception:
            horse_name = horse_name_raw.strip()

        odds_raw = buff[54:58].strip()
        odds = int(odds_raw) / 10.0 if odds_raw.isdigit() else 0.0
        if odds <= 0:
            return None

        venue_name = _LOCAL_VENUE_CODE_MAP.get(venue_code, venue_code)
        fmt_date   = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"
        race_id    = f"{race_date}_{venue_code}_{race_number:02d}"
        horse_id   = f"{race_id}_H{horse_number:02d}"

        return {
            "race_id":     race_id,
            "race_name":   f"{venue_name}{race_number}R",
            "race_date":   fmt_date,
            "venue":       venue_name,
            "race_number": race_number,
            "horse_id":    horse_id,
            "horse_name":  horse_name,
            "horse_number": horse_number,
            "odds":        odds,
        }
    except Exception as exc:
        log.debug("UmaConn: failed to parse record — %s", exc)
        return None


# UmaConn local venue codes (地方競馬場コード)
_LOCAL_VENUE_CODE_MAP = {
    "30": "門別",   "31": "岩手盛岡", "32": "水沢",
    "35": "浦和",   "36": "船橋",     "37": "大井",   "38": "川崎",
    "42": "金沢",   "43": "笠松",     "44": "名古屋",
    "46": "園田",   "47": "姫路",
    "48": "高知",   "50": "佐賀",
}
