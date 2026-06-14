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
"""
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from logger.operation_logger import get_logger

log = get_logger()

_DATASPEC_ODDS = "RACE"
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
    try:
        import win32com.client  # type: ignore
    except ImportError:
        raise RuntimeError(
            "pywin32 is required. Run: pip install pywin32  "
            "(use the 32-bit Python installer — NVDTLab.dll is 32-bit only)"
        )

    race_date_str = target_date.replace("-", "")
    fromtime = f"{race_date_str}000000"

    log.info("UmaConn: connecting to COM server (NVDTLabLib.NVLink)...")
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")

    rc = nvlink.NVInit("UNKNOWN")
    if rc != 0:
        raise RuntimeError(
            f"NVInit failed — code {rc}. "
            "Open the UmaConn GUI once to complete the initial setup."
        )

    log.info("UmaConn: opening odds stream (dataspec=%s from=%s)...", _DATASPEC_ODDS, fromtime)
    rc, read_count, dl_count, last_ts = nvlink.NVOpen(
        _DATASPEC_ODDS, fromtime, 1, 0, 0, ""
    )
    if rc in (-301, -1) or dl_count > 0:
        log.info("UmaConn: Data download/connection in progress. Waiting for completion...")
        start_time = time.time()
        timeout = 180
        completed = False
        while time.time() - start_time < timeout:
            status = nvlink.NVStatus()
            if status == 0:
                completed = True
                log.info("UmaConn: Download completed successfully.")
                break
            elif status > 0:
                pass # Downloading
            else:
                if status == -203:
                    log.warning("UmaConn: No local data found for today (status -203). Normal if no local races are scheduled.")
                    completed = False
                else:
                    log.error("UmaConn: Download failed with status %d", status)
                break
            time.sleep(2)
        
        if not completed:
            log.warning("UmaConn: No live local data available today or outside racing hours.")
            return horses_by_race
    elif rc < 0:
        raise RuntimeError(f"NVOpen failed — code {rc}")

    new_races: list[dict] = []
    new_horses: dict[str, list] = {}

    try:
        while True:
            rc, buff, size, filename = nvlink.NVRead("", _NV_BUFFER_SIZE, "")
            if rc == 0: break
            if rc == -1: continue
            if rc == -3:
                time.sleep(1)
                continue
            if rc < 0:
                log.error("UmaConn: NVRead error — code %d", rc)
                break

            parsed_race, parsed_horses = _parse_h1_record(str(buff), target_date)
            if not parsed_race or not parsed_horses:
                continue

            race_id = parsed_race["race_id"]
            if race_id not in new_horses:
                new_races.append(parsed_race)
                new_horses[race_id] = []

            new_horses[race_id].extend(parsed_horses)
            
    finally:
        nvlink.NVClose()

    # Merge local races into the existing dict
    for race in new_races:
        rid = race["race_id"]
        if rid not in horses_by_race:
            races.append(race)
            horses_by_race[rid] = new_horses[rid]
            log.info("UmaConn: added local race %s — %d horses", race["race_name"], len(new_horses[rid]))
        else:
            existing = {h["horse_id"]: h for h in horses_by_race[rid]}
            for h in new_horses[rid]:
                if h["horse_id"] in existing:
                    existing[h["horse_id"]]["odds"] = h["odds"]
                else:
                    horses_by_race[rid].append(h)

    log.info("UmaConn: fetch complete — %d local races", len(new_races))
    return horses_by_race


def _parse_h1_record(buff: str, target_date: str) -> tuple[dict|None, list]:
    """
    Parse an NVDATA H1 record (UmaConn RACE).
    H1 records contain total pari-mutuel votes per horse, which we convert to odds.
    """
    if not buff or len(buff) < 90:
        return None, []
        
    try:
        if buff[0:2] != "H1":
            return None, []

        venue_code = buff[19:21].strip()
        race_num_str = buff[25:27].strip()
        
        if not race_num_str.isdigit():
            return None, []
            
        race_number = int(race_num_str)
        venue_name = _LOCAL_VENUE_CODE_MAP.get(venue_code, venue_code)
        race_id = f"{target_date.replace('-', '')[:8][:4]}-{target_date.replace('-', '')[:8][4:6]}-{target_date.replace('-', '')[:8][6:8]}_{venue_code}_{race_number:02d}"
        
        race_info = {
            "race_id": race_id,
            "race_name": f"{venue_name}{race_number}R",
            "race_date": target_date,
            "venue": venue_name,
            "race_number": race_number,
        }

        # Parse horses (15-byte blocks starting at byte 90)
        horses = []
        offset = 90
        raw_votes = {}
        
        for _ in range(18): # Max horses
            chunk = buff[offset : offset + 15]
            if len(chunk) < 15 or not chunk[0:2].isdigit():
                break
                
            h_num = int(chunk[0:2])
            votes_str = chunk[2:13].strip()
            
            # Scratched horses are marked with dashes
            if "-" in votes_str:
                votes = 0
            else:
                votes = int(votes_str) if votes_str.isdigit() else 0
                
            raw_votes[h_num] = votes
            offset += 15
            
        # Calculate Odds = (Total Pool * 0.8) / Votes
        total_pool = sum(raw_votes.values())
        
        for h_num, votes in raw_votes.items():
            if votes > 0:
                odds = round((total_pool * 0.8) / votes, 1)
            else:
                odds = 0.0
                
            horse_id = f"{race_id}_H{h_num:02d}"
            horses.append({
                "horse_id": horse_id,
                "race_id": race_id,
                "horse_name": f"Local Horse {h_num:02d}", # H1 doesn't provide names
                "horse_number": h_num,
                "odds": odds,
            })
            
        return race_info, horses
        
    except Exception as exc:
        log.debug("UmaConn: failed to parse H1 record — %s", exc)
        return None, []


# UmaConn local venue codes (地方競馬場コード)
_LOCAL_VENUE_CODE_MAP = {
    "30": "門別",   "31": "岩手盛岡", "32": "水沢",
    "35": "浦和",   "36": "船橋",     "37": "大井",   "38": "川崎",
    "42": "金沢",   "43": "笠松",     "44": "名古屋",
    "46": "園田",   "47": "姫路",
    "48": "高知",   "50": "佐賀",
}
