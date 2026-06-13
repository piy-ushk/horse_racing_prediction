import win32com.client  # type: ignore
import time
import re

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    nvlink.NVInit("UNKNOWN")
    
    # Use today's date
    rc = nvlink.NVOpen("RACEDIFN", "20260614000000", 1, 0, 0, "")
    print(f"NVOpen returned: {rc}")
    
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
            print(f"First 100 chars: {buff_str[:100]}")
            
            # Check for record headers
            for header in ['0B', 'OB', 'RA', 'SE', 'CH', 'H1', 'O1']:
                indices = [m.start() for m in re.finditer(f'^{header}| {header}', buff_str)]
                if not indices:
                    # Also try anywhere in string just in case
                    indices = [m.start() for m in re.finditer(header, buff_str)]
                if indices:
                    print(f"Found '{header}' at index {indices[0]}")
            break
        else:
            print(f"Error {rc}")
            break

    nvlink.NVClose()
except Exception as e:
    print(f"Error: {e}")
