import win32com.client  # type: ignore
from datetime import date
import time

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    rc = nvlink.NVInit("UNKNOWN")
    print(f"NVInit returned {rc}")
    
    fromtime = date.today().strftime("%Y%m%d") + "000000"
    
    dataspecs = ["0B11", "0B12", "0B13", "0B14", "0B15", "0B31", "0B32", "RACE", "ODDS"]
    
    print("\n--- Testing different dataspecs with NVOpen ---")
    for ds in dataspecs:
        rc_open = nvlink.NVOpen(ds, fromtime, 1, 0, 0, "")
        print(f"Dataspec {ds} -> NVOpen returned: {rc_open}")
        if isinstance(rc_open, tuple) and rc_open[0] in (-301, -1):
            print("  -> Download triggered. Attempting to abort...")
            try:
                nvlink.NVCancel()
            except:
                pass
            time.sleep(1)

    nvlink.NVClose()
    
except Exception as e:
    print(f"Error: {e}")
