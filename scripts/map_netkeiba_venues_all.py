import requests, re
from concurrent.futures import ThreadPoolExecutor

def fetch(args):
    day, xx = args
    url = f"https://nar.netkeiba.com/race/shutuba.html?race_id=2026{xx:02d}06{day:02d}01"
    try:
        resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=2)
        m = re.search(r'<title>(.*?)</title>', resp.text, flags=re.IGNORECASE)
        t = m.group(1) if m else ""
        if "  |   地方競馬レース情報 - netkeiba" not in t and t:
            m_venue = re.search(r'日\s+(.+?)1R', t)
            if m_venue:
                return (xx, m_venue.group(1))
    except Exception:
        pass
    return None

args_list = [(d, xx) for d in range(1, 15) for xx in range(30, 65)]

mapping = {}
with ThreadPoolExecutor(max_workers=20) as ex:
    for r in ex.map(fetch, args_list):
        if r:
            code, name = r
            if name not in mapping:
                mapping[name] = code

with open("netkeiba_venues_map.txt", "w", encoding="utf-8") as f:
    for name, code in mapping.items():
        f.write(f"{name}: {code}\n")
