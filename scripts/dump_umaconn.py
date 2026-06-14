import win32com.client
import os
import sys
import time
from pathlib import Path

with open(Path(__file__).parent.parent / "dump_umaconn.log", "w", encoding="utf-8") as f:
    def log(msg):
        print(msg)
        f.write(msg + "\n")

    try:
        log("UmaConn: connecting to COM server (NVDTLabLib.NVLink)...")
        nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
        rc = nvlink.NVInit("UNKNOWN")
        log(f"NVInit: {rc}")

        # Hardcode to last Friday (2026-06-12) to force fetch historical local racing data
        fromtime = "20260612000000"
        
        log(f"Querying RACE with historical fromtime: {fromtime}")
        rc, read_count, dl_count, last_ts = nvlink.NVOpen("RACE", fromtime, 1, 0, 0, "")
        log(f"NVOpen(RACE): {rc}, dl_count: {dl_count}")
        
        if rc in (-301, -1) or dl_count > 0:
            log("Waiting for UmaConn download...")
            start_time = time.time()
            while time.time() - start_time < 60:
                status = nvlink.NVStatus()
                if status == 0:
                    log("Download completed!")
                    break
                elif status < 0:
                    log(f"Download failed/no data: {status}")
                    break
                time.sleep(2)
        
        for _ in range(15):
            rc, buff, size, filename = nvlink.NVRead("", 110000, "")
            if rc == 0: break
            if rc < 0 and rc not in (-1, -3): break
            if rc in (-1, -3): 
                time.sleep(0.5)
                continue
            log(f"RACE record: {str(buff)[:500]}")
            
        nvlink.NVClose()
        
    except Exception as e:
        log(f"Error: {e}")
