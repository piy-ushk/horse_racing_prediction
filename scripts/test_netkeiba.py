import requests
from bs4 import BeautifulSoup

def fetch_netkeiba_names(year, venue_code, mmdd, race_num):
    race_id = f"{year}{venue_code}{mmdd}{race_num:02d}"
    url = f"https://nar.netkeiba.com/race/shutuba.html?race_id={race_id}"
    print(f"Fetching: {url}")
    
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    if not resp.ok:
        print(f"Failed: {resp.status_code}")
        return
        
    soup = BeautifulSoup(resp.content, "html.parser")
    horse_elements = soup.select(".HorseList .HorseName a")
    
    names = [el.text.strip() for el in horse_elements]
    for i, name in enumerate(names, 1):
        print(f"Horse {i}: {name}")

if __name__ == "__main__":
    fetch_netkeiba_names("2026", "44", "0612", 2)
