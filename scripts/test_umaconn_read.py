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
    
    if isinstance(rc_open, tuple):
        rc, read_count, dl_count, last_ts = rc_open
    else:
        rc = rc_open
        dl_count = 0
        
    if rc in (-301, -1) or dl_count > 0:
        start_time = time.time()
        while time.time() - start_time < 10:
            status = nvlink.NVStatus()
            if status == 0:
                print("Download completed successfully!")
                break
            time.sleep(1)

    print("Testing NVRead...")
    try:
        rc_read, buff, size, filename = nvlink.NVRead("", 110000, "")
        print(f"NVRead returned: rc={rc_read}, size={size}, filename={filename}")
        print(f"Buffer snippet: {buff[:50]}")
    except Exception as e:
        print(f"NVRead failed: {e}")

    print("Testing NVGets...")
    try:
        # NVGets might have different return structure
        ret = nvlink.NVGets("", 110000, "")
        print(f"NVGets returned tuple of length {len(ret)}: {ret[0]}")
        if len(ret) > 1:
            print(f"Buffer snippet: {str(ret[1])[:50]}")
    except Exception as e:
        print(f"NVGets failed: {e}")

    nvlink.NVClose()
    
except Exception as e:
    print(f"Error: {e}")
