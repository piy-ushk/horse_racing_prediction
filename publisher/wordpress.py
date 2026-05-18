"""
WordPress REST API publisher.

Sends prediction data to WordPress and creates / updates race prediction pages.
Each page:
  - Has a noindex meta (via Yoast SEO REST field or injected HTML)
  - Is accessible only when ?auth=line_only is in the URL
  - Uses the page slug  race-{race_id}

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


def publish_race(race: dict, predictions: list, horses_by_id: dict) -> dict:
    """
    Returns {"wp_page_id": int|None, "wp_page_url": str}.
    """
    html_content = _build_page_html(race, predictions, horses_by_id)

    if _wp_configured():
        return _post_to_wordpress(race, html_content)

    log.info("WordPress: no credentials — writing static HTML for demo")
    return _write_static_html(race, html_content)


def _wp_configured() -> bool:
    return bool(config.WP_USERNAME and config.WP_APP_PASSWORD
                and "your-wordpress-site" not in config.WP_BASE_URL)


def _build_page_html(race: dict, predictions: list, horses_by_id: dict) -> str:
    h, m = config.get_schedule()
    scheduled_time = f"{h:02d}:{m:02d}"
    rows = ""
    for p in predictions:
        horse = horses_by_id.get(p["horse_id"], {})
        mark_cell = f'<span class="mark mark-{p["rank"]}">{p["mark"]}</span>' if p["mark"] else ""
        rows += (
            f'<tr>'
            f'<td>{p["rank"]}</td>'
            f'<td>{horse.get("horse_number","")}</td>'
            f'<td>{horse.get("horse_name","")}</td>'
            f'<td>{p["odds"]:.1f}</td>'
            f'<td>{mark_cell}</td>'
            f'</tr>\n'
        )

    return f"""<!-- noindex -->
<meta name="robots" content="noindex,nofollow">
<div id="race-prediction" data-auth-required="line_only">
  <h2>{race["race_name"]}  予想</h2>
  <p class="race-meta">{race["race_date"]} | {race["venue"]} {race["race_number"]}R</p>
  <table class="prediction-table">
    <thead>
      <tr><th>順位</th><th>馬番</th><th>馬名</th><th>オッズ</th><th>印</th></tr>
    </thead>
    <tbody>
{rows}    </tbody>
  </table>
  <p class="note">※ 予想は当日{scheduled_time}時点のオッズに基づいています</p>
</div>
"""


def _post_to_wordpress(race: dict, html_content: str) -> dict:
    import requests
    from requests.auth import HTTPBasicAuth

    slug = f"race-{race['race_id'].lower()}"
    title = f"{race['race_name']} 予想 {race['race_date']}"
    endpoint = f"{config.WP_BASE_URL.rstrip('/')}/wp-json/wp/v2/pages"
    auth = HTTPBasicAuth(config.WP_USERNAME, config.WP_APP_PASSWORD)

    # Check if page already exists
    resp = requests.get(endpoint, params={"slug": slug}, auth=auth, timeout=15)
    existing = resp.json() if resp.ok else []
    page_id = existing[0]["id"] if existing else None

    payload = {
        "title": title,
        "content": html_content,
        "status": "publish",
        "slug": slug,
        "meta": {"_yoast_wpseo_meta-robots-noindex": "1"},
    }

    if page_id:
        resp = requests.post(f"{endpoint}/{page_id}", json=payload, auth=auth, timeout=15)
        log.info("WordPress: updated page id=%d  slug=%s", page_id, slug)
    else:
        resp = requests.post(endpoint, json=payload, auth=auth, timeout=15)
        log.info("WordPress: created new page  slug=%s", slug)

    resp.raise_for_status()
    page_data = resp.json()
    page_url = f"{config.WP_BASE_URL.rstrip('/')}/{slug}?{config.AUTH_PARAM}={config.AUTH_VALUE}"
    log.info("WordPress: page URL → %s", page_url)
    return {"wp_page_id": page_data["id"], "wp_page_url": page_url}


def _write_static_html(race: dict, html_content: str) -> dict:
    out_dir = config.DATA_DIR / "html"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = f"race-{race['race_id'].lower()}"
    out_path = out_dir / f"{slug}.html"

    full_page = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,nofollow">
<title>{race["race_name"]} 予想</title>
<style>
  body{{font-family:sans-serif;max-width:700px;margin:40px auto;padding:0 16px;background:#fafafa}}
  h2{{color:#1a1a2e}} .race-meta{{color:#666;font-size:.9em}}
  .prediction-table{{border-collapse:collapse;width:100%}}
  .prediction-table th,.prediction-table td{{border:1px solid #ccc;padding:8px 12px;text-align:center}}
  .prediction-table thead{{background:#1a1a2e;color:#fff}}
  .mark{{font-size:1.4em;font-weight:bold}}
  .mark-1{{color:#d4af37}} .mark-2{{color:#c0c0c0}}
  .mark-3{{color:#cd7f32}} .mark-4{{color:#888}}
  .note{{font-size:.8em;color:#999;margin-top:16px}}
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
