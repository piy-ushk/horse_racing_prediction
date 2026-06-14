import win32com.client
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
software_id = os.getenv("JRAVAN_SOFTWARE_ID")

with open(Path(__file__).parent.parent / "dump_o1.log", "w", encoding="utf-8") as f:
    def log(msg):
        print(msg)
        f.write(msg + "\n")

    try:
        jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
        rc = jvlink.JVInit(software_id)
        log(f"JVInit: {rc}")

        # The 16-digit race key discovered from 0B11
        race_key = "2026061402010201"

        log(f"Querying 0B31 with race key: {race_key}")
        rc = jvlink.JVRTOpen("0B31", race_key)
        log(f"JVRTOpen(0B31): {rc}")
        if rc >= 0:
            for _ in range(5):
                rc, buff, size, filename = jvlink.JVRead("", 4096, "")
                if rc <= 0: break
                log(f"0B31 record: {buff[:500]}")
            jvlink.JVClose()

    except Exception as e:
        log(f"Error: {e}")
