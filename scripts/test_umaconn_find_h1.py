import win32com.client  # type: ignore
import time
import re

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    nvlink.NVInit("UNKNOWN")
    rc = nvlink.NVOpen("RACEDIFN", "20260612000000", 1, 0, 0, "")
    
    timeout_time = time.time() + 30
    while time.time() < timeout_time:
        rc, buff, size, filename = nvlink.NVRead("", 110000, "")
        if rc == -3:
            time.sleep(1)
            continue
        elif rc == -1:
            continue
        elif rc == 0:
            break
        elif rc > 0:
            buff_str = str(buff)
            h1_indices = [m.start() for m in re.finditer(r'H1', buff_str)]
            print(f"Found {len(h1_indices)} occurrences of 'H1'.")
            if len(h1_indices) > 1:
                diff = h1_indices[1] - h1_indices[0]
                print(f"Distance between first two H1s: {diff} bytes")
                for i in range(min(5, len(h1_indices))):
                    idx = h1_indices[i]
                    print(f"Record {i}: {buff_str[idx:idx+50]}")
            break
            
    nvlink.NVClose()
except Exception as e:
    print(f"Error: {e}")
