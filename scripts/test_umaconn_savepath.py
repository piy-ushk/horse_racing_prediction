import win32com.client  # type: ignore
import sys
import os
from datetime import date
import time

key = "FAA9-6K7A-85Y3-XGJK-L"
save_path = r"C:\UmaConnData"

if not os.path.exists(save_path):
    os.makedirs(save_path)

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    
    print("Setting service key...")
    nvlink.NVSetServiceKey(key)
    
    print(f"Setting save path to {save_path}...")
    try:
        nvlink.NVSetSavePath(save_path)
    except Exception as e:
        print(f"NVSetSavePath failed: {e}")
        try:
            nvlink.m_savepath = save_path
        except:
            pass

    rc = nvlink.NVInit("UNKNOWN")
    print(f"NVInit returned {rc}")
    
    fromtime = date.today().strftime("%Y%m%d") + "000000"
    
    print(f"Testing NVOpen('0B11', '{fromtime}', 4, 0, 0, '')...")
    rc_open = nvlink.NVOpen("0B11", fromtime, 4, 0, 0, "")
    print(f"NVOpen returned: {rc_open}")
    
    if isinstance(rc_open, tuple) and rc_open[0] in (-301, -1):
        start_time = time.time()
        while time.time() - start_time < 15:
            status = nvlink.NVStatus()
            print(f"NVStatus: {status}")
            if status == 0:
                print("Download completed successfully!")
                break
            elif status < 0:
                print(f"Download failed with error: {status}")
                break
            time.sleep(2)
            
    nvlink.NVClose()
    
except Exception as e:
    print(f"Error: {e}")
