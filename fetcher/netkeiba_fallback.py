import requests
from html.parser import HTMLParser
import time
from logger.operation_logger import get_logger

log = get_logger()

# Official JV-Data/Netkeiba venue codes
_VENUE_CODE_MAP = {
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

class NetkeibaOddsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_umaban = False
        self.in_horse_name = False
        self.in_a = False
        self.in_popular = False
        self.in_odds_span = False
        
        self.current_umaban = None
        self.current_horse_name = None
        self.current_odds = None
        
        self.horses = {}
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "td":
            cls = attrs_dict.get("class", "")
            if "Umaban" in cls:
                self.in_umaban = True
            elif "Popular" in cls or "Txt_R" in cls:
                self.in_popular = True
        elif tag == "span":
            cls = attrs_dict.get("class", "")
            if "HorseName" in cls:
                self.in_horse_name = True
            elif self.in_popular:
                self.in_odds_span = True
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
        elif self.in_odds_span:
            try: self.current_odds = float(data)
            except ValueError: pass
            
    def handle_endtag(self, tag):
        if tag == "td" and self.in_umaban:
            self.in_umaban = False
        elif tag == "td" and self.in_popular:
            self.in_popular = False
        elif tag == "span" and self.in_odds_span:
            self.in_odds_span = False
        elif tag == "a" and self.in_a:
            self.in_a = False
        elif tag == "span" and self.in_horse_name:
            self.in_horse_name = False
            
        if tag == "tr":
            if self.current_umaban is not None and self.current_horse_name is not None:
                self.horses[self.current_umaban] = {
                    "horse_name": self.current_horse_name,
                    "odds": self.current_odds if self.current_odds is not None else 0.0
                }
            self.current_umaban = None
            self.current_horse_name = None
            self.current_odds = None

def scrape_races_and_odds(race_date: str) -> tuple[list, dict]:
    """
    Fallback scraper: Bypasses UmaConn and scrapes ALL local races for the target date directly from NetKeiba.
    Returns: (races_list, horses_by_race_id)
    """
    import re
    log.info("Netkeiba Fallback: Initiating direct scrape for %s...", race_date)
    
    date_str = race_date.replace('-', '')
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
    
    races_list = []
    horses_by_race = {}
    
    # 1. We iterate over all 15 venues. For each venue, we probe race 1 to see if it's active today.
    for venue_code, venue_name in _VENUE_CODE_MAP.items():
        # Exception: JV-Data uses "33" for Obihiro, but NetKeiba uses "03"
        nk_venue_code = "03" if venue_code == "33" else venue_code
        
        race_number = 1
        consecutive_failures = 0
        
        while race_number <= 12:  # max 12 races usually
            nk_race_id = f"{date_str[:4]}{nk_venue_code}{date_str[4:8]}{race_number:02d}"
            url = f"https://nar.netkeiba.com/race/shutuba.html?race_id={nk_race_id}"
            
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                if not resp.ok:
                    consecutive_failures += 1
                    break
                    
                parser = NetkeibaOddsParser()
                parser.feed(resp.text)
                
                if not parser.horses:
                    consecutive_failures += 1
                    if consecutive_failures >= 2: # Stop after 2 missing races
                        break
                    race_number += 1
                    continue
                    
                # We found horses! This means the race is active.
                consecutive_failures = 0
                race_id = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}_{venue_code}_{race_number:02d}"
                
                race_info = {
                    "race_id": race_id,
                    "race_name": f"{venue_name}{race_number}R",
                    "race_date": race_date,
                    "venue": venue_name,
                    "race_number": race_number,
                }
                
                horses = []
                for h_num, h_data in parser.horses.items():
                    horse_id = f"{race_id}_{h_num:02d}"
                    horses.append({
                        "race_id": race_id,
                        "horse_id": horse_id,
                        "horse_number": h_num,
                        "horse_name": h_data["horse_name"],
                        "weight": 0.0,
                        "weight_diff": 0.0,
                        "odds": h_data["odds"]
                    })
                    
                races_list.append(race_info)
                horses_by_race[race_id] = horses
                log.info("Netkeiba Fallback: Scraped %s - %d horses", race_info["race_name"], len(horses))
                
            except Exception as e:
                log.warning("Netkeiba Fallback: Error scraping %s: %s", nk_race_id, e)
                consecutive_failures += 1
                if consecutive_failures >= 2:
                    break
                    
            race_number += 1
            time.sleep(0.5) # Be polite
            
    log.info("Netkeiba Fallback: Completed direct scrape. Found %d local races total.", len(races_list))
    return races_list, horses_by_race


_JRA_VENUE_CODE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}

def scrape_jra_races_and_odds(race_date: str) -> tuple[list, dict]:
    """
    Fallback scraper: Bypasses JV-Link and scrapes ALL JRA races for the target date directly from NetKeiba.
    Returns: (races_list, horses_by_race_id)
    """
    import re
    log.info("Netkeiba JRA Fallback: Initiating direct scrape for %s...", race_date)
    
    date_str = race_date.replace('-', '')
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
    
    # 1. Fetch JRA race list subpage for the date
    url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date_str}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if not resp.ok:
            log.warning("Netkeiba JRA Fallback: Failed to fetch JRA race list subpage. Code: %d", resp.status_code)
            return [], {}
    except Exception as e:
        log.warning("Netkeiba JRA Fallback: Error fetching JRA race list: %s", e)
        return [], {}
        
    # Extract unique 12-digit race IDs
    race_ids = set()
    for match in re.finditer(r"race_id=(\d{12})", resp.text):
        race_ids.add(match.group(1))
        
    sorted_race_ids = sorted(list(race_ids))
    if not sorted_race_ids:
        log.info("Netkeiba JRA Fallback: No JRA races scheduled on %s.", race_date)
        return [], {}
        
    log.info("Netkeiba JRA Fallback: Found %d JRA races scheduled.", len(sorted_race_ids))
    
    races_list = []
    horses_by_race = {}
    
    for rid in sorted_race_ids:
        race_url = f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}"
        
        v_code = rid[4:6]
        venue_name = _JRA_VENUE_CODE_MAP.get(v_code, v_code)
        race_num = int(rid[10:12])
        
        try:
            r_resp = requests.get(race_url, headers=headers, timeout=5)
            if not r_resp.ok:
                log.warning("Netkeiba JRA Fallback: Failed to fetch race details for %s", rid)
                continue
                
            parser = NetkeibaOddsParser()
            parser.feed(r_resp.text)
            
            if not parser.horses:
                log.debug("Netkeiba JRA Fallback: No horses parsed (possibly entries not drawn yet) for %s", rid)
                continue
                
            date_str = race_date.replace("-", "")
            race_id = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}_{v_code}_{race_num:02d}"
            
            # Extract race name using regex
            race_name = ""
            name_match = re.search(r'<h1 class="RaceName">\s*(.*?)\s*(?:<|$)', r_resp.text)
            if name_match:
                race_name = name_match.group(1).strip()
            else:
                nav_match = re.search(fr'<a href="[^"]*race_id={rid}[^"]*" title="([^"]+)"', r_resp.text)
                if nav_match:
                    race_name = nav_match.group(1).strip()
                else:
                    race_name = f"{venue_name}{race_num}R"
            if race_name and not race_name.startswith(f"{venue_name}{race_num}R"):
                race_name = f"{venue_name}{race_num}R {race_name}"
                
            race_info = {
                "race_id": race_id,
                "race_name": race_name,
                "race_date": race_date,
                "venue": venue_name,
                "race_number": race_num,
            }
            
            horses = []
            for h_num, h_data in parser.horses.items():
                # For JRA, horse ID uses the _H prefix: race_id_H{horse_number:02d}
                horse_id = f"{race_id}_H{h_num:02d}"
                horses.append({
                    "race_id": race_id,
                    "horse_id": horse_id,
                    "horse_number": h_num,
                    "horse_name": h_data["horse_name"],
                    "weight": 0.0,
                    "weight_diff": 0.0,
                    "odds": h_data["odds"]
                })
                
            races_list.append(race_info)
            horses_by_race[race_id] = horses
            log.info("Netkeiba JRA Fallback: Scraped %s - %d horses", race_name, len(horses))
            
        except Exception as e:
            log.warning("Netkeiba JRA Fallback: Error scraping race %s: %s", rid, e)
            
        time.sleep(0.5)
        
    log.info("Netkeiba JRA Fallback: Completed JRA direct scrape. Found %d races.", len(races_list))
    return races_list, horses_by_race

