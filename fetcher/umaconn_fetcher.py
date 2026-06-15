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


_netkeiba_cache = {}

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
            
        if venue_code not in _LOCAL_VENUE_CODE_MAP:
            log.debug("UmaConn: skipping unknown venue code %s", venue_code)
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

        # Attempt to fetch real Japanese horse names from NetKeiba with caching
        horse_names_map = {}
        if race_id in _netkeiba_cache:
            horse_names_map = _netkeiba_cache[race_id]
        else:
            try:
                import requests
                from html.parser import HTMLParser

                class NetkeibaParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.in_umaban = False
                        self.in_horse_name = False
                        self.in_a = False
                        self.current_umaban = None
                        self.current_horse_name = None
                        self.map = {}
                        
                    def handle_starttag(self, tag, attrs):
                        attrs_dict = dict(attrs)
                        if tag == "td":
                            cls = attrs_dict.get("class", "")
                            if cls.startswith("Umaban"):
                                self.in_umaban = True
                        elif tag == "span":
                            cls = attrs_dict.get("class", "")
                            if "HorseName" in cls:
                                self.in_horse_name = True
                        elif tag == "a" and self.in_horse_name:
                            self.in_a = True
                            
                    def handle_data(self, data):
                        data = data.strip()
                        if not data: return
                        if self.in_umaban:
                            try: self.current_umaban = int(data)
                            except ValueError: pass
                        elif self.in_a:
                            self.current_horse_name = data
                            
                    def handle_endtag(self, tag):
                        if tag == "td" and self.in_umaban:
                            self.in_umaban = False
                        elif tag == "a" and self.in_a:
                            self.in_a = False
                        elif tag == "span" and self.in_horse_name:
                            self.in_horse_name = False
                            if self.current_umaban is not None and self.current_horse_name is not None:
                                self.map[self.current_umaban] = self.current_horse_name
                                self.current_umaban = None
                                self.current_horse_name = None

                # NetKeiba NAR Race ID format: YYYY + venue_code + MMDD + race_number(2 digits)
                nk_date = target_date.replace('-', '')
                
                # Exception: JV-Data uses "33" for Obihiro, but NetKeiba uses "03"
                nk_venue_code = "03" if venue_code == "33" else venue_code
                nk_race_id = f"{nk_date[:4]}{nk_venue_code}{nk_date[4:8]}{race_number:02d}"
                nk_url = f"https://nar.netkeiba.com/race/shutuba.html?race_id={nk_race_id}"
                
                resp = requests.get(nk_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=5)
                if resp.ok:
                    parser = NetkeibaParser()
                    parser.feed(resp.text)
                    horse_names_map = parser.map
                    _netkeiba_cache[race_id] = horse_names_map
            except Exception as e:
                log.warning("NetKeiba scrape failed for %s: %s", race_id, e)

        # Parse horses (15-byte blocks starting at byte 90)
        parsed_horses_info = {}
        offset = 90
        raw_votes = {}
        
        reg_horses_str = buff[27:29].strip()
        num_horses_to_parse = int(reg_horses_str) if reg_horses_str.isdigit() else 18
        
        for _ in range(num_horses_to_parse):
            chunk = buff[offset : offset + 15]
            if len(chunk) < 15 or not chunk[0:2].isdigit():
                break
                
            h_num = int(chunk[0:2])
            if h_num == 0:
                offset += 15
                continue
                
            votes_str = chunk[2:13].strip()
            if "-" in votes_str:
                votes = 0
            else:
                votes = int(votes_str) if votes_str.isdigit() else 0
                
            raw_votes[h_num] = votes
            parsed_horses_info[h_num] = horse_names_map.get(h_num, f"Local Horse {h_num:02d}")
            offset += 15
            
        # Calculate Odds = (Total Pool * 0.8) / Votes
        total_pool = sum(raw_votes.values())
        
        horses = []
        for h_num, horse_name in parsed_horses_info.items():
            votes = raw_votes.get(h_num, 0)
            if votes > 0:
                odds = round((total_pool * 0.8) / votes, 1)
            else:
                odds = 0.0
                
            horse_id = f"{race_id}_{h_num:02d}"
            horses.append({
                "race_id": race_id,
                "horse_id": horse_id,
                "horse_number": h_num,
                "horse_name": horse_name,
                "weight": 0.0,
                "weight_diff": 0.0,
                "odds": odds
            })
            
        return race_info, horses
        
    except Exception as exc:
        log.debug("UmaConn: failed to parse H1 record — %s", exc)
        return None, []


# UmaConn local venue codes (地方競馬場コード) - Official JV-Data Spec
_LOCAL_VENUE_CODE_MAP = {
    "33": "帯広",
    "30": "門別",
    "35": "盛岡",
    "36": "水沢",
    "42": "浦和",
    "43": "船橋",
    "44": "大井",
    "45": "川崎",
    "46": "金沢",
    "47": "笠松",
    "48": "名古屋",
    "50": "園田",
    "51": "姫路",
    "54": "高知",
    "55": "佐賀"
}
