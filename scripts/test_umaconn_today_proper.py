import win32com.client  # type: ignore
import time
import re

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    nvlink.NVInit("UNKNOWN")
    
    rc_open = nvlink.NVOpen("RACEDIFN", "20260614000000", 1, 0, 0, "")
    print(f"NVOpen returned: {rc_open}")
    
    if isinstance(rc_open, tuple):
        rc, _, dl_count, _ = rc_open
    else:
        rc = rc_open
        dl_count = 0
        
    if rc in (-301, -1) or dl_count > 0:
        print("Waiting for download to finish...")
        start_time = time.time()
        while time.time() - start_time < 30:
            status = nvlink.NVStatus()
            if status == 0:
                print("Download completed!")
                break
            time.sleep(1)

    timeout_time = time.time() + 60
    while time.time() < timeout_time:
        rc, buff, size, filename = nvlink.NVRead("", 110000, "")
        if rc == -3:
            time.sleep(1)
            continue
        elif rc == -1:
            continue
        elif rc == 0:
            print("EOF")
            break
        elif rc > 0:
            buff_str = str(buff)
            print(f"Read success: rc={rc} bytes")
            
            for header in ['0B', 'OB', 'RA', 'SE', 'CH', 'H1', 'O1']:
                indices = [m.start() for m in re.finditer(header, buff_str)]
                if indices:
                    print(f"Found '{header}' at indices: {indices[:5]}")
            break
        else:
            print(f"Error {rc}")
            break

    nvlink.NVClose()
except Exception as e:
    print(f"Error: {e}")
