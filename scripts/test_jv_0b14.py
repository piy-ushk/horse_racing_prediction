import win32com.client  # type: ignore
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
software_id = os.getenv("JRAVAN_SOFTWARE_ID")

try:
    jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
    jvlink.JVInit(software_id)
    
    for spec in ["0B11", "0B12", "0B14", "0B15", "0B31", "RA", "SE", "CH", "H1"]:
        open_res = jvlink.JVOpen(spec, "20260613000000", 1, 0, 0, "")
        rc = open_res[0] if isinstance(open_res, tuple) else open_res
        print(f"JVOpen({spec}): {rc}")
        if rc in (-1, 0):
            jvlink.JVClose()
except Exception as e:
    print(f"Error: {e}")
