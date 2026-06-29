"""
WordPress REST API publisher.

Sends prediction data to WordPress and creates / updates a single master page per day.
Each page:
  - Has a noindex meta (via Yoast SEO REST field or injected HTML)
  - Is accessible only when ?auth=line_only is in the URL
  - Uses the page slug  predictions-{race_date}

In demo mode (no WP credentials) the publisher writes static HTML files to
data/html/ so results can be previewed locally via the Flask server.
"""
import os
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from logger.operation_logger import get_logger

log = get_logger()


def publish_daily_master_page(all_predictions: list, horses_by_id: dict, race_date: str) -> dict:
    """
    Returns {"wp_page_id": int|None, "wp_page_url": str}.
    all_predictions is a list of tuples: (race, preds_for_race, horses_for_race)
    """
    if not all_predictions:
        return {}

    html_content = _build_daily_master_html(all_predictions, horses_by_id, race_date)

    if _wp_configured():
        return _post_to_wordpress(race_date, html_content)

    log.info("WordPress: no credentials — writing static HTML for demo")
    return _write_static_html(race_date, html_content)


def _wp_configured() -> bool:
    return bool(config.WP_USERNAME and config.WP_APP_PASSWORD
                and "your-wordpress-site" not in config.WP_BASE_URL)


def _build_daily_master_html(all_predictions: list, horses_by_id: dict, race_date: str) -> str:
    h, m = config.get_schedule()
    scheduled_time = f"{h:02d}:{m:02d}"
    
    sections = []
    
    # Separate JRA and NAR
    jra_venues = {"札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"}
    
    jra_preds = []
    nar_preds = []
    for race_tuple in all_predictions:
        venue = race_tuple[0].get("venue", "")
        if venue in jra_venues:
            jra_preds.append(race_tuple)
        else:
            nar_preds.append(race_tuple)
            
    # Sort each group by venue then race_number
    jra_preds.sort(key=lambda x: (x[0].get("venue", ""), x[0].get("race_number", 0)))
    nar_preds.sort(key=lambda x: (x[0].get("venue", ""), x[0].get("race_number", 0)))
    
    # Place JRA first, then NAR
    if jra_preds:
        sections.append('<h2>中央競馬 (JRA)</h2>')
        for race, predictions, _ in jra_preds:
            rows = ""
            for p in predictions:
                if not p["mark"]:
                    continue
                horse = horses_by_id.get(p["horse_id"], {})
                mark_cell = f'<span class="mark mark-{p["rank"]}">{p["mark"]}</span>'
                rows += (
                    f'<tr>'
                    f'<td>{horse.get("horse_number","")}</td>'
                    f'<td>{horse.get("horse_name","")}</td>'
                    f'<td>{mark_cell}</td>'
                    f'</tr>\n'
                )
            section_html = f"""
  <div class="race-section">
    <h3>{race["race_name"]}  予想</h3>
    <p class="race-meta">{race["venue"]} {race["race_number"]}R</p>
    <table class="prediction-table">
      <thead>
        <tr><th>馬番</th><th>馬名</th><th>印</th></tr>
      </thead>
      <tbody>
{rows}      </tbody>
    </table>
  </div>
"""
            sections.append(section_html)

    if nar_preds:
        sections.append('<h2>地方競馬 (NAR)</h2>')
        for race, predictions, _ in nar_preds:
            rows = ""
            for p in predictions:
                if not p["mark"]:
                    continue
                horse = horses_by_id.get(p["horse_id"], {})
                mark_cell = f'<span class="mark mark-{p["rank"]}">{p["mark"]}</span>'
                rows += (
                    f'<tr>'
                    f'<td>{horse.get("horse_number","")}</td>'
                    f'<td>{horse.get("horse_name","")}</td>'
                    f'<td>{mark_cell}</td>'
                    f'</tr>\n'
                )
            section_html = f"""
  <div class="race-section">
    <h3>{race["race_name"]}  予想</h3>
    <p class="race-meta">{race["venue"]} {race["race_number"]}R</p>
    <table class="prediction-table">
      <thead>
        <tr><th>馬番</th><th>馬名</th><th>印</th></tr>
      </thead>
      <tbody>
{rows}      </tbody>
    </table>
  </div>
"""
            sections.append(section_html)

    all_sections_html = "\n".join(sections)

    return f"""<!-- noindex -->
<meta name="robots" content="noindex,nofollow">
<div id="race-prediction" data-auth-required="line_only">
  <h2>{race_date} 本日の予想まとめ</h2>
{all_sections_html}
</div>
"""


def _post_to_wordpress(race_date: str, html_content: str) -> dict:
    from fetcher.http_utils import get_robust_session
    from requests.auth import HTTPBasicAuth
    
    session = get_robust_session(retries=3, backoff_factor=2.0)

    slug = f"predictions-{race_date}"
    title = f"{race_date} 本日の全レース予想"
    endpoint = f"{config.WP_BASE_URL.rstrip('/')}/wp-json/wp/v2/pages"
    auth = HTTPBasicAuth(config.WP_USERNAME, config.WP_APP_PASSWORD)

    # Check if page already exists
    try:
        resp = session.get(endpoint, params={"slug": slug}, auth=auth, timeout=15)
        existing = resp.json() if resp.ok else []
    except Exception as e:
        log.warning("WordPress: Error checking existing page: %s", e)
        existing = []
        
    page_id = existing[0]["id"] if existing else None

    payload = {
        "title": title,
        "content": html_content,
        "status": "publish",
        "slug": slug,
        "meta": {"_yoast_wpseo_meta-robots-noindex": "1"},
    }

    try:
        if page_id:
            resp = session.post(f"{endpoint}/{page_id}", json=payload, auth=auth, timeout=30)
            log.info("WordPress: updated master page id=%d  slug=%s", page_id, slug)
        else:
            resp = session.post(endpoint, json=payload, auth=auth, timeout=30)
            log.info("WordPress: created new master page  slug=%s", slug)
            
        resp.raise_for_status()
        page_data = resp.json()
        page_url = f"{config.WP_BASE_URL.rstrip('/')}/{slug}?{config.AUTH_PARAM}={config.AUTH_VALUE}"
        log.info("WordPress: master page URL → %s", page_url)
        return {"wp_page_id": page_data["id"], "wp_page_url": page_url}
    except Exception as e:
        log.error("WordPress: Failed to publish page: %s", e)
        return {}


def _write_static_html(race_date: str, html_content: str) -> dict:
    out_dir = config.DATA_DIR / "html"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = f"predictions-{race_date}"
    out_path = out_dir / f"{slug}.html"

    full_page = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,nofollow">
<title>{race_date} 本日の全レース予想</title>
<style>
  body{{font-family:sans-serif;max-width:700px;margin:40px auto;padding:0 16px;background:#fafafa}}
  h2{{color:#1a1a2e;text-align:center;border-bottom:2px solid #1a1a2e;padding-bottom:10px}} 
  h3{{color:#333;margin-bottom:5px;margin-top:0}}
  .race-section{{background:#fff;border-radius:8px;padding:20px;margin-bottom:30px;box-shadow:0 2px 5px rgba(0,0,0,0.05)}}
  .race-meta{{color:#666;font-size:.9em;margin-top:0}}
  .prediction-table{{border-collapse:collapse;width:100%}}
  .prediction-table th,.prediction-table td{{border:1px solid #eee;padding:8px 12px;text-align:center}}
  .prediction-table thead{{background:#1a1a2e;color:#fff}}
  .prediction-table tr:nth-child(even){{background-color:#f9f9f9}}
  .mark{{font-size:1.4em;font-weight:bold}}
  .mark-1{{color:#d4af37}} .mark-2{{color:#c0c0c0}}
  .mark-3{{color:#cd7f32}} .mark-4{{color:#888}}
  .note{{font-size:.8em;color:#999;margin-bottom:20px;text-align:center}}
  .access-denied{{display:none}}
</style>
<script>
  (function(){{
    var p=new URLSearchParams(location.search);
    if(p.get('auth')!=='line_only'){{
      document.addEventListener('DOMContentLoaded',function(){{
        document.getElementById('race-prediction').style.display='none';
        document.getElementById('access-denied').style.display='block';
      }});
    }}
  }})();
</script>
</head>
<body>
<div id="access-denied" style="display:none;text-align:center;padding:60px">
  <h2>アクセスが制限されています</h2>
  <p>このページはLINEリッチメニューからのみアクセス可能です。</p>
</div>
{html_content}
</body>
</html>"""

    out_path.write_text(full_page, encoding="utf-8")
    page_url = f"http://localhost:{config.FLASK_PORT}/preview/{slug}?{config.AUTH_PARAM}={config.AUTH_VALUE}"
    log.info("Static HTML written → %s", out_path)
    return {"wp_page_id": None, "wp_page_url": page_url}
