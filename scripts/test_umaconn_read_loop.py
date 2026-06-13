import win32com.client  # type: ignore
from datetime import date
import time

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    nvlink.NVInit("UNKNOWN")
    
    fromtime = "20260612000000"
    print(f"Testing NVOpen with RACE from {fromtime}...")
    rc_open = nvlink.NVOpen("RACE", fromtime, 1, 0, 0, "")
    print(f"NVOpen returned: {rc_open}")

    print("Reading data loop (handling -3 as downloading)...")
    records_read = 0
    timeout_time = time.time() + 30
    
    while time.time() < timeout_time:
        rc, buff, size, filename = nvlink.NVRead("", 110000, "")
        if rc == -3:
            print("NVRead: -3 (Downloading in progress, waiting 1s...)")
            time.sleep(1)
            continue
        elif rc == 0:
            print("NVRead: 0 (No more data / EOF)")
            break
        elif rc < 0:
            print(f"NVRead error: {rc}")
            break
        else:
            print(f"NVRead Success! rc={rc}, size={size}, filename={filename}")
            records_read += 1
            if records_read > 3:
                print("Successfully read a few records. Breaking early.")
                break

    nvlink.NVClose()
    
except Exception as e:
    print(f"Error: {e}")
