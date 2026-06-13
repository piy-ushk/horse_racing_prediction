import win32com.client  # type: ignore
import time
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
software_id = os.getenv("JRAVAN_SOFTWARE_ID")

try:
    jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
    rc = jvlink.JVInit(software_id)
    print(f"JVInit: {rc}")
    
    # Try JVRTOpen first
    rc = jvlink.JVRTOpen("0B11", "")
    print(f"JVRTOpen: {rc}")
    
    # Try JVOpen
    open_res = jvlink.JVOpen("0B11", "20260613000000", 1, 0, 0, "")
    print(f"JVOpen: {open_res}")
    
    rc_open = open_res[0] if isinstance(open_res, tuple) else open_res
    if rc_open in (-1, 0) or (isinstance(open_res, tuple) and open_res[2] > 0):
        print("Waiting for JVStatus...")
        start_time = time.time()
        while time.time() - start_time < 10:
            if jvlink.JVStatus() == 0:
                print("Download ready!")
                break
            time.sleep(1)
            
        rc_read, buff, filename = jvlink.JVGetsR("", 110000, "")
        print(f"JVGetsR rc={rc_read}, filename={filename}")
        print(f"Buff: {str(buff)[:200]}")
        
    jvlink.JVClose()
except Exception as e:
    print(f"Error: {e}")
