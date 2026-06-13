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
            print(f"Total string length: {len(buff_str)}")
            
            # Search for '0B' or 'OB'
            ob_indices = [m.start() for m in re.finditer(r'0B|OB', buff_str)]
            print(f"Found {len(ob_indices)} occurrences of '0B' or 'OB'.")
            
            if ob_indices:
                idx = ob_indices[0]
                print(f"First occurrence context: {buff_str[max(0, idx-10):min(len(buff_str), idx+200)]}")
            
            # Search for 'RA' (Race Info)
            ra_indices = [m.start() for m in re.finditer(r'RA', buff_str)]
            print(f"Found {len(ra_indices)} occurrences of 'RA'.")
            if ra_indices:
                idx = ra_indices[0]
                print(f"First 'RA' context: {buff_str[max(0, idx-10):min(len(buff_str), idx+200)]}")
            break
            
    nvlink.NVClose()
except Exception as e:
    print(f"Error: {e}")
