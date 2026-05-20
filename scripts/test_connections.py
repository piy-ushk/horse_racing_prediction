"""
Real COM connection test — JV-Link and UmaConn.

Run this on the Windows VPS AFTER:
  - JV-Link installed and license key registered
  - UmaConn installed and GUI run once (license registered)
  - .env has JRAVAN_SOFTWARE_ID and DEMO_MODE=false

Usage:
    python scripts/test_connections.py
    python scripts/test_connections.py --jvlink-only
    python scripts/test_connections.py --umaconn-only
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from logger.operation_logger import get_logger

log = get_logger()

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[94m[INFO]\033[0m"


def _check_32bit():
    import struct
    bits = struct.calcsize("P") * 8
    if bits != 32:
        print(f"{FAIL} Python is {bits}-bit — UmaConn requires 32-bit Python (NVDTLab.dll is 32-bit only)")
        print("       Install Python 3.11 (32-bit) from python.org and re-run.")
        return False
    print(f"{PASS} Python is 32-bit")
    return True


def _check_pywin32():
    try:
        import win32com.client  # noqa: F401
        print(f"{PASS} pywin32 available")
        return True
    except ImportError:
        print(f"{FAIL} pywin32 not installed — run: pip install pywin32 && python -m pywin32_postinstall -install")
        return False


def _check_dll(path: str, label: str) -> bool:
    if Path(path).exists():
        print(f"{PASS} {label} DLL found: {path}")
        return True
    print(f"{FAIL} {label} DLL NOT found: {path}")
    return False


def _check_com_registry(prog_id: str, label: str) -> bool:
    import winreg
    keys_to_try = [
        rf"SOFTWARE\Classes\{prog_id}",
        rf"SOFTWARE\WOW6432Node\Classes\{prog_id}",
    ]
    for key in keys_to_try:
        try:
            winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key)
            print(f"{PASS} {label} COM registered ({key})")
            return True
        except FileNotFoundError:
            continue
    print(f"{FAIL} {label} COM NOT in registry (ProgID: {prog_id})")
    return False


def test_jvlink() -> bool:
    print("\n--- JV-Link (JRA-VAN 中央競馬) ---")

    software_id = config.JRAVAN_SOFTWARE_ID
    license_key = config.JRAVAN_LICENSE_KEY

    if not software_id:
        print(f"{FAIL} JRAVAN_SOFTWARE_ID is empty in .env")
        print("       Log into jra-van.jp -> ソフトウェア登録 -> copy the ソフトウェアID")
        return False

    if not license_key:
        print(f"{FAIL} JRAVAN_LICENSE_KEY is empty in .env")
        return False

    print(f"{INFO} Software ID : {software_id}")
    print(f"{INFO} License key : {license_key}")

    ok = _check_com_registry("JVDTLab.JVLink", "JV-Link")
    if not ok:
        print("       Install JV-Link from jra-van.jp and register license via GUI")
        return False

    try:
        import win32com.client
        print(f"{INFO} Creating COM object JVDTLab.JVLink...")
        jvlink = win32com.client.Dispatch("JVDTLab.JVLink")

        print(f"{INFO} Calling JVInit({software_id})...")
        rc = jvlink.JVInit(software_id)
        if rc == 0:
            print(f"{PASS} JVInit returned 0 — authenticated successfully")
        else:
            print(f"{FAIL} JVInit returned {rc}")
            _print_jvlink_init_error(rc)
            return False

        # Open a real-time odds stream briefly to confirm data access
        print(f"{INFO} Opening real-time stream (JVRTOpen dataspec=0B11)...")
        rc = jvlink.JVRTOpen("0B11", "")
        if rc >= 0:
            print(f"{PASS} JVRTOpen succeeded (rc={rc}) — data stream accessible")
            jvlink.JVClose()
        else:
            print(f"{WARN} JVRTOpen returned {rc} — may be outside racing hours or no live data today")
            print("       This is expected on non-race days. JVInit passed so authentication is OK.")
            jvlink.JVClose()

        return True

    except Exception as exc:
        print(f"{FAIL} JV-Link COM error: {exc}")
        return False


def test_umaconn() -> bool:
    print("\n--- UmaConn (地方競馬DATA) ---")

    dll_path = r"C:\Windows\SysWOW64\NVDTLab.dll"
    ok = _check_dll(dll_path, "UmaConn")
    if not ok:
        print("       Install UmaConn from saikyo.k-ba.com")
        return False

    ok = _check_com_registry("NVDTLabLib.NVLink", "UmaConn")
    if not ok:
        print("       Run the UmaConn GUI once and complete the initial setup")
        return False

    try:
        import win32com.client
        print(f"{INFO} Creating COM object NVDTLabLib.NVLink...")
        nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")

        # UmaConn stores its license via the GUI — init param is literal "UNKNOWN"
        print(f"{INFO} Calling NVInit('UNKNOWN')...")
        rc = nvlink.NVInit("UNKNOWN")
        if rc == 0:
            print(f"{PASS} NVInit returned 0 — authenticated successfully")
        else:
            print(f"{FAIL} NVInit returned {rc}")
            _print_umaconn_init_error(rc)
            return False

        # Try opening a data stream briefly
        from datetime import date
        fromtime = date.today().strftime("%Y%m%d") + "000000"
        print(f"{INFO} Opening odds stream (NVOpen dataspec=0B11 from={fromtime})...")
        try:
            rc, read_count, dl_count, last_ts = nvlink.NVOpen("0B11", fromtime, 4, 0, 0, "")
            if rc >= 0:
                print(f"{PASS} NVOpen succeeded (rc={rc}, records={read_count}) — data stream accessible")
            else:
                print(f"{WARN} NVOpen returned {rc} — may be outside racing hours or no live data today")
                print("       This is expected on non-race days. NVInit passed so authentication is OK.")
        finally:
            try:
                nvlink.NVClose()
            except Exception:
                pass

        return True

    except Exception as exc:
        print(f"{FAIL} UmaConn COM error: {exc}")
        return False


def _print_jvlink_init_error(rc: int):
    errors = {
        -1:  "ソフトウェアIDが無効 — jra-van.jp でソフトウェアIDを再確認してください",
        -2:  "JV-Linkが起動していない — JVLinkSetup.exe を起動して利用キーを登録してください",
        -3:  "ネットワーク接続エラー — インターネット接続を確認してください",
        -111:"利用キーが未登録 — JV-Link管理画面から利用キーを登録してください",
    }
    msg = errors.get(rc, "不明なエラーコード — JRA-VAN技術仕様書を参照してください")
    print(f"       エラー詳細: {msg}")


def _print_umaconn_init_error(rc: int):
    errors = {
        -1:  "UmaConn GUIの初期設定が未完了 — GUIを起動して利用キーを登録してください",
        -2:  "NVDTLab.dll が正しく登録されていない — UmaConnを再インストールしてください",
        -3:  "ネットワーク接続エラー",
    }
    msg = errors.get(rc, "不明なエラーコード — UmaConnドキュメントを参照してください")
    print(f"       エラー詳細: {msg}")


def main():
    args = sys.argv[1:]
    jvlink_only  = "--jvlink-only"  in args
    umaconn_only = "--umaconn-only" in args

    print("=" * 55)
    print("  Horse Racing — Real Connection Test")
    print("=" * 55)
    print(f"{INFO} DEMO_MODE in config: {config.DEMO_MODE}")
    if config.DEMO_MODE:
        print(f"{WARN} DEMO_MODE=true in .env — set DEMO_MODE=false to test real connections")
        print()

    results = {}

    print("\n--- Environment ---")
    env_ok = _check_32bit() and _check_pywin32()

    if not env_ok:
        print("\nFix environment issues above, then re-run.")
        sys.exit(1)

    if not umaconn_only:
        results["JV-Link"]  = test_jvlink()

    if not jvlink_only:
        results["UmaConn"] = test_umaconn()

    print("\n" + "=" * 55)
    print("  Summary")
    print("=" * 55)
    all_pass = True
    for name, ok in results.items():
        status = PASS if ok else FAIL
        print(f"  {status}  {name}")
        if not ok:
            all_pass = False

    if all_pass:
        print("\nAll connections verified. Set DEMO_MODE=false in .env")
        print("then run: python main.py")
    else:
        print("\nFix failures above, then re-run this script.")
        sys.exit(1)


if __name__ == "__main__":
    main()
