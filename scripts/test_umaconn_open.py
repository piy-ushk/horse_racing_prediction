import win32com.client  # type: ignore
import sys
from datetime import date

key = "FAA9-6K7A-85Y3-XGJK-L"

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    
    # Try setting the key directly
    print("Setting service key...")
    try:
        nvlink.NVSetServiceKey(key)
        print("NVSetServiceKey called successfully.")
    except Exception as e:
        print(f"NVSetServiceKey failed: {e}")
        try:
            nvlink.m_servicekey = key
            print("m_servicekey set successfully.")
        except Exception as e2:
            print(f"m_servicekey failed: {e2}")

    rc = nvlink.NVInit("UNKNOWN")
    print(f"NVInit returned {rc}")
    
    fromtime = date.today().strftime("%Y%m%d") + "000000"
    
    # Test NVOpen again
    print(f"Testing NVOpen('0B11', '{fromtime}', 4, 0, 0, '')...")
    rc_open = nvlink.NVOpen("0B11", fromtime, 4, 0, 0, "")
    print(f"NVOpen returned: {rc_open}")
    if isinstance(rc_open, tuple) and rc_open[0] in (-301, -1):
        import time
        start_time = time.time()
        while time.time() - start_time < 10:
            status = nvlink.NVStatus()
            print(f"NVStatus: {status}")
            if status <= 0:
                break
            time.sleep(1)

    # Test NVRTOpen
    print("Testing NVRTOpen('0B11', '')...")
    try:
        rc_rt = nvlink.NVRTOpen("0B11", "")
        print(f"NVRTOpen returned: {rc_rt}")
    except Exception as e:
        print(f"NVRTOpen failed: {e}")
        
    nvlink.NVClose()
    
except Exception as e:
    print(f"Error: {e}")
