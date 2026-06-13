import win32com.client  # type: ignore
import time

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    nvlink.NVInit("UNKNOWN")
    rc = nvlink.NVOpen("RACE", "20260612000000", 1, 0, 0, "")
    
    records_read = 0
    timeout_time = time.time() + 30
    
    while time.time() < timeout_time and records_read < 10:
        rc, buff, filename = nvlink.NVGets("", 110000, "")
        if rc == -3:
            time.sleep(1)
            continue
        elif rc == -1:
            continue
        elif rc == 0:
            break
        elif rc > 0:
            print(f"[{records_read}] rc={rc} type={buff[:2]} len={len(buff)}")
            print(f"Data: {buff[:100]}")
            records_read += 1
            
    nvlink.NVClose()
except Exception as e:
    print(f"Error: {e}")
