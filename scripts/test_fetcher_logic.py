import requests
from bs4 import BeautifulSoup

def test_fetcher_logic():
    target_date = "2026-06-11"
    venue_code = "50" # Saga
    race_number = 1
    
    nk_date = target_date.replace('-', '')
    nk_race_id = f"{nk_date[:4]}{venue_code}{nk_date[4:8]}{race_number:02d}"
    nk_url = f"https://nar.netkeiba.com/race/shutuba.html?race_id={nk_race_id}"
    print(f"URL: {nk_url}")
    
    resp = requests.get(nk_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=5)
    print(f"Status: {resp.status_code}")
    
    soup = BeautifulSoup(resp.content, "html.parser")
    rows = soup.select(".HorseList")
    print(f"Found {len(rows)} HorseList rows")
    
    horse_names_map = {}
    for row in rows:
        umaban_td = row.select_one("td[class^='Umaban']")
        name_a = row.select_one(".HorseName a")
        print(f"Row {row.get('id')} - umaban_td: {umaban_td is not None}, name_a: {name_a is not None}")
        
        if umaban_td and name_a:
            try:
                h_idx = int(umaban_td.text.strip())
                horse_names_map[h_idx] = name_a.text.strip()
            except ValueError as e:
                print(f"ValueError parsing umaban: {e}")
                
    print(f"Map size: {len(horse_names_map)}")

if __name__ == "__main__":
    test_fetcher_logic()
