import win32com.client  # type: ignore
import os
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv(Path(__file__).parent.parent / ".env")
software_id = os.getenv("JRAVAN_SOFTWARE_ID")

try:
    jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
    jvlink.JVInit(software_id)
    
    # Try the standard JRA-VAN dataspecs for JVOpen
    for spec in ["RACE", "DIFF", "BLOD", "DICT"]:
        open_res = jvlink.JVOpen(spec, "20260613000000", 1, 0, 0, "")
        rc = open_res[0] if isinstance(open_res, tuple) else open_res
        print(f"JVOpen({spec}): {rc}")
        if rc in (-1, 0) or (isinstance(open_res, tuple) and len(open_res)>2 and open_res[2] > 0):
            print(f"Waiting for {spec} download...")
            start_time = time.time()
            while time.time() - start_time < 10:
                if jvlink.JVStatus() == 0:
                    break
                time.sleep(1)
            
            rc_read, buff, filename = jvlink.JVGetsR("", 110000, "")
            print(f"JVGetsR {spec}: {rc_read}, {filename}")
            print(f"Data: {str(buff)[:100]}")
            jvlink.JVClose()
            
except Exception as e:
    print(f"Error: {e}")
