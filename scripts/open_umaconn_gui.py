import win32com.client  # type: ignore
from datetime import date
import sys
import time

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    rc = nvlink.NVInit("UNKNOWN")
    print(f"NVInit returned {rc}")
    
    fromtime = date.today().strftime("%Y%m%d") + "000000"
    
    # Using option=3 (Setup/Dialog mode) to force the UI to open
    print("Attempting to open the UmaConn Setup GUI programmatically...")
    print("If a window pops up, please enter your key there!")
    
    rc_open = nvlink.NVOpen("0B11", fromtime, 3, 0, 0, "")
    print(f"NVOpen(option=3) returned: {rc_open}")
    
    if isinstance(rc_open, tuple) and rc_open[0] in (-301, -1):
        start_time = time.time()
        while time.time() - start_time < 30:  # wait longer for UI interaction
            status = nvlink.NVStatus()
            if status != -203:
                print(f"NVStatus changed! Current: {status}")
            if status == 0:
                print("Success!")
                break
            time.sleep(2)
            
    nvlink.NVClose()
    
except Exception as e:
    print(f"Error: {e}")
