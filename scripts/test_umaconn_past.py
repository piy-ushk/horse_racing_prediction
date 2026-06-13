import win32com.client  # type: ignore
import time

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    nvlink.NVInit("UNKNOWN")
    
    # Force the save path explicitly
    nvlink.NVSetSavePath(r"C:\UmaConnData")
    
    # Try fetching data for YESTERDAY / TODAY to ensure data actually exists
    fromtime_past = "20260612000000" 
    
    print(f"Testing NVOpen with RACE from {fromtime_past}...")
    rc_open = nvlink.NVOpen("RACE", fromtime_past, 1, 0, 0, "")
    print(f"NVOpen returned: {rc_open}")
    
    if isinstance(rc_open, tuple) and rc_open[0] in (-301, -1):
        print("Waiting for download to complete...")
        start_time = time.time()
        while time.time() - start_time < 30:
            status = nvlink.NVStatus()
            print(f"NVStatus: {status}")
            if status == 0:
                print("Download completed successfully!")
                break
            elif status < 0:
                print(f"Download failed with error: {status}")
                break
            time.sleep(1)

    nvlink.NVClose()
    
except Exception as e:
    print(f"Error: {e}")
