import requests, re, time

with open("netkeiba_venues.txt", "w", encoding="utf-8") as f:
    for xx in range(30, 65):
        url = f"https://nar.netkeiba.com/race/shutuba.html?race_id=2026{xx:02d}060801"
        resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
        m = re.search(r'<title>(.*?)</title>', resp.text, flags=re.IGNORECASE)
        t = m.group(1) if m else ""
        if "  |   地方競馬レース情報 - netkeiba" not in t:
            f.write(f"{xx:02d}: {t}\n")
        time.sleep(0.1)
