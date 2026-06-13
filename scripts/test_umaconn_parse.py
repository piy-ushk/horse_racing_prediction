import win32com.client  # type: ignore
import time

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    nvlink.NVInit("UNKNOWN")
    rc = nvlink.NVOpen("RACE", "20260612000000", 1, 0, 0, "")
    
    timeout_time = time.time() + 30
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
            print(f"Read success: rc={rc} bytes")
            lines = str(buff).splitlines()
            print(f"Number of lines: {len(lines)}")
            print("First 10 lines:")
            for i, line in enumerate(lines[:10]):
                print(f"[{i}] {line[:100]}")
            break
        else:
            print(f"Error {rc}")
            break

    nvlink.NVClose()
except Exception as e:
    print(f"Error: {e}")
