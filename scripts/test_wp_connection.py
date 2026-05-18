"""
WordPress REST API connection test.

Run this before going live to verify that:
  1. The WordPress site is reachable
  2. Application password authentication works
  3. The system can create and delete a test page

Usage:
    python scripts/test_wp_connection.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import config

try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    print("[FAIL] 'requests' not installed. Run: pip install requests")
    sys.exit(1)


def test_wp_connection():
    print(f"\nWordPress Connection Test")
    print(f"  URL  : {config.WP_BASE_URL}")
    print(f"  User : {config.WP_USERNAME or '(not set)'}")
    print()

    if not config.WP_USERNAME or not config.WP_APP_PASSWORD:
        print("[SKIP] WP_USERNAME / WP_APP_PASSWORD not set in .env")
        print("       Add WordPress application password credentials to .env first.")
        return False

    auth = HTTPBasicAuth(config.WP_USERNAME, config.WP_APP_PASSWORD)
    base = config.WP_BASE_URL.rstrip("/")

    # 1. Check API root
    print("[1] Checking WordPress REST API root...")
    try:
        r = requests.get(f"{base}/wp-json/wp/v2", timeout=10)
        r.raise_for_status()
        print(f"    OK — status {r.status_code}")
    except Exception as e:
        print(f"    FAIL — {e}")
        return False

    # 2. Verify authentication
    print("[2] Verifying authentication...")
    try:
        r = requests.get(f"{base}/wp-json/wp/v2/users/me", auth=auth, timeout=10)
        if r.status_code == 401:
            print("    FAIL — 401 Unauthorized. Check WP_USERNAME and WP_APP_PASSWORD.")
            return False
        r.raise_for_status()
        user = r.json()
        print(f"    OK — authenticated as: {user.get('name', '?')} (id={user.get('id')})")
    except Exception as e:
        print(f"    FAIL — {e}")
        return False

    # 3. Create a test page
    print("[3] Creating a test page...")
    payload = {
        "title": "[TEST] Horse Racing System — Delete Me",
        "content": "<p>Connection test. This page can be deleted.</p>",
        "status": "draft",
        "slug": "race-system-test-ping",
    }
    try:
        r = requests.post(f"{base}/wp-json/wp/v2/pages", json=payload, auth=auth, timeout=15)
        r.raise_for_status()
        page_id = r.json()["id"]
        print(f"    OK — test page created (id={page_id})")
    except Exception as e:
        print(f"    FAIL — {e}")
        return False

    # 4. Delete the test page
    print("[4] Cleaning up test page...")
    try:
        r = requests.delete(
            f"{base}/wp-json/wp/v2/pages/{page_id}",
            params={"force": True},
            auth=auth,
            timeout=15,
        )
        r.raise_for_status()
        print(f"    OK — test page deleted")
    except Exception as e:
        print(f"    WARN — could not delete test page id={page_id}: {e}")

    print("\n[ALL TESTS PASSED] WordPress integration is ready.")
    return True


if __name__ == "__main__":
    ok = test_wp_connection()
    sys.exit(0 if ok else 1)
