import win32com.client  # type: ignore
from datetime import date
import time

key = "FAA9-6K7A-85Y3-XGJK-L"

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    nvlink.NVSetServiceKey(key)
    nvlink.NVInit("UNKNOWN")
    
    fromtime = date.today().strftime("%Y%m%d") + "000000"
    
    for opt in [1, 2]:
        print(f"\nTesting NVOpen with option={opt}...")
        rc_open = nvlink.NVOpen("0B11", fromtime, opt, 0, 0, "")
        print(f"NVOpen returned: {rc_open}")
        if isinstance(rc_open, tuple) and rc_open[0] in (-301, -1):
            start_time = time.time()
            while time.time() - start_time < 5:
                status = nvlink.NVStatus()
                print(f"NVStatus: {status}")
                if status == 0:
                    print("Download completed successfully!")
                    break
                elif status != -203 and status < 0:
                    print(f"Download failed with error: {status}")
                    break
                time.sleep(1)
            
    nvlink.NVClose()
    
except Exception as e:
    print(f"Error: {e}")
