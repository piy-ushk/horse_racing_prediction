import win32com.client
import sys
import time

def main():
    try:
        print("Connecting to NVLink...")
        nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
        rc = nvlink.NVInit("UNKNOWN")
        if rc != 0:
            print(f"NVInit failed: {rc}")
            return
            
        print("Querying RACEDIFN for 2026-06-12...")
        rc, _, dl_count, _ = nvlink.NVOpen("RACEDIFN", "20260612000000", 1, 0, 0, "")
        
        if rc in (-301, -1) or dl_count > 0:
            print("Waiting for download...")
            for _ in range(30):
                if nvlink.NVStatus() == 0:
                    break
                time.sleep(2)
                
        print("Reading records...")
        for _ in range(5):
            rc, buff, size, filename = nvlink.NVRead("", 110000, "")
            if rc == 0: break
            if rc < 0 and rc not in (-1, -3): break
            if rc in (-1, -3): 
                time.sleep(0.5)
                continue
            
            try:
                decoded = buff.encode("latin-1").decode("cp932")
            except:
                decoded = str(buff)
            print(f"Record: {decoded[:200]}")
            
    finally:
        try: nvlink.NVClose()
        except: pass

if __name__ == "__main__":
    main()
