import requests, re
from concurrent.futures import ThreadPoolExecutor

def fetch(xx):
    url = f"https://nar.netkeiba.com/race/shutuba.html?race_id=2026{xx:02d}061201"
    resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
    m = re.search(r'<title>(.*?)</title>', resp.text, flags=re.IGNORECASE)
    t = m.group(1) if m else ""
    if "  |   地方競馬レース情報 - netkeiba" not in t and t:
        # e.g., "C2 出馬表 | 2026年6月8日 水沢1R 地方競馬レース情報 - netkeiba"
        # Extract the track name before the '1R'
        m_venue = re.search(r'日\s+(.+?)1R', t)
        v = m_venue.group(1) if m_venue else t
        return f"{xx:02d}: {v}"
    return None

with ThreadPoolExecutor(max_workers=10) as ex:
    results = list(ex.map(fetch, range(30, 65)))

with open("netkeiba_venues_map.txt", "w", encoding="utf-8") as f:
    for r in results:
        if r:
            f.write(f"{r}\n")
