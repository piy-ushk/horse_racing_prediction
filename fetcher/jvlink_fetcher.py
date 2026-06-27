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
import time
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from logger.operation_logger import get_logger
from fetcher.mock_data import generate_mock_races, generate_mock_horses

log = get_logger()

# Buffer size for one JV-Link record (bytes)
_RECORD_BUFFER = 4096


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
    try:
        import win32com.client  # type: ignore
    except ImportError:
        raise RuntimeError(
            "pywin32 is required for JV-Link. "
            "Run: pip install pywin32  "
            "Or set DEMO_MODE=true to use mock data."
        )

    software_id = config.JRAVAN_SOFTWARE_ID
    if not software_id:
        raise RuntimeError("JRAVAN_SOFTWARE_ID not set in .env.")

    log.info("JV-Link: connecting to COM server (software_id=%s)...", software_id)
    jvlink = win32com.client.Dispatch("JVDTLab.JVLink")

    rc = jvlink.JVInit(software_id)
    if rc != 0:
        raise RuntimeError(f"JVInit failed — code {rc}")

    date_key = race_date.replace("-", "")
    
    races_dict = {}
    horses_by_race = {}
    race_keys = set()
    
    # Pass 1: Discover ALL JRA races and horses using Netkeiba
    # We bypass 0B11 completely because 0B11 (Real-time weights) only publishes 
    # data 50 minutes before a race, which means a 9:30 AM run only discovers Race 1!
    log.info("JV-Link: Fetching full JRA race and horse list from Netkeiba (bypassing 0B11 limitation)...")
    
    races_dict = {}
    horses_by_race = {}
    race_keys = set()
    
    try:
        from fetcher.netkeiba_fallback import scrape_jra_races_and_odds
        nk_races, nk_horses = scrape_jra_races_and_odds(race_date)
        
        if not nk_races:
            log.warning("JV-Link: No JRA races found via Netkeiba for %s. Skipping JRA.", race_date)
            return [], {}
            
        for nk_r in nk_races:
            rid = nk_r["race_id"]
            races_dict[rid] = nk_r
            horses_by_race[rid] = nk_horses.get(rid, [])
            
            if "jvlink_race_key" in nk_r:
                race_keys.add(nk_r["jvlink_race_key"])
                
        log.info("JV-Link: Successfully initialized %d JRA races.", len(races_dict))
    except Exception as e:
        log.error("JV-Link: Failed to initialize JRA races via Netkeiba: %s", e)
        return [], {}

    # Pass 2: Fetch 0B31 (Odds) for each discovered race
    log.info("JV-Link: fetching odds from 0B31 for %d races...", len(race_keys))
    for r_key in sorted(list(race_keys)):
        v_code = r_key[8:10]
        r_num = int(r_key[14:16])
        race_id = f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:8]}_{v_code}_{r_num:02d}"
        
        rc = jvlink.JVRTOpen("0B31", r_key)
        if rc < 0:
            log.debug("JV-Link: JVRTOpen(0B31) failed for %s", r_key)
            continue
            
        try:
            while True:
                rc, buff, size, filename = jvlink.JVRead("", _RECORD_BUFFER, "")
                if rc == 0: break
                if rc < 0 and rc not in (-1, -3): break
                if rc in (-1, -3): 
                    time.sleep(0.1)
                    continue
                    
                if not buff: continue
                idx = 0
                while idx < len(buff):
                    o1_idx = buff.find("O1", idx)
                    if o1_idx == -1:
                        break
                    
                    if o1_idx + 43 > len(buff):
                        break
                        
                    # Parse O1 odds (Tansho / Win odds)
                    # O1 record header is 43 bytes. Then 8 bytes per horse.
                    odds_offset = o1_idx + 43
                    
                    for i in range(18): # Max 18 horses in JRA
                        chunk_start = odds_offset + i*8
                        chunk_end = chunk_start + 8
                        if chunk_end > len(buff):
                            break
                            
                        chunk = buff[chunk_start:chunk_end]
                        if len(chunk) < 8 or not chunk[0:2].strip().isdigit():
                            break
                        
                        h_num = int(chunk[0:2])
                        odds_str = chunk[2:6]
                        
                        if odds_str.isdigit() and int(odds_str) > 0:
                            odds_val = int(odds_str) / 10.0
                        else:
                            odds_val = 0.0
                            
                        # Find this horse and update odds
                        for horse in horses_by_race.get(race_id, []):
                            if horse["horse_number"] == h_num:
                                if odds_val > 0:
                                    horse["odds"] = odds_val
                                break
                                
                    idx = o1_idx + 180 # Move past this record
                            
        finally:
            jvlink.JVClose()
            
    races = list(races_dict.values())
    log.info("JV-Link: fetch complete — %d races", len(races))
    return races, horses_by_race

# JRA-VAN venue codes → display names
_VENUE_CODE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}
