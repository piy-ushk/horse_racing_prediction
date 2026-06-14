import win32com.client
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
software_id = os.getenv("JRAVAN_SOFTWARE_ID")

with open(Path(__file__).parent.parent / "dump.log", "w", encoding="utf-8") as f:
    def log(msg):
        print(msg)
        f.write(msg + "\n")

    try:
        jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
        rc = jvlink.JVInit(software_id)
        log(f"JVInit: {rc}")

        date_key = "20260614"

        # Dump 0B11 (Horse Weight)
        log(f"Querying 0B11 with day key: {date_key}")
        rc = jvlink.JVRTOpen("0B11", date_key)
        log(f"JVRTOpen(0B11): {rc}")
        if rc >= 0:
            for _ in range(3):
                # JVRead is the correct method, JVGetsR does not exist!
                rc, buff, size, filename = jvlink.JVRead("", 4096, "")
                if rc <= 0: break
                log(f"0B11 record: {buff[:200]}")
            jvlink.JVClose()

        # Dump 0B14 (Course Info)
        log(f"Querying 0B14 with day key: {date_key}")
        rc = jvlink.JVRTOpen("0B14", date_key)
        log(f"JVRTOpen(0B14): {rc}")
        if rc >= 0:
            for _ in range(3):
                rc, buff, size, filename = jvlink.JVRead("", 2048, "")
                if rc <= 0: break
                log(f"0B14 record: {buff[:200]}")
            jvlink.JVClose()

        # Dump 0B31 with day key (just in case it works!)
        log(f"Querying 0B31 with day key: {date_key}")
        rc = jvlink.JVRTOpen("0B31", date_key)
        log(f"JVRTOpen(0B31): {rc}")
        if rc >= 0:
            rc, buff, size, filename = jvlink.JVRead("", 4096, "")
            log(f"0B31 record: {buff[:200]}")
            jvlink.JVClose()

    except Exception as e:
        log(f"Error: {e}")
