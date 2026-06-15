import win32com.client
import sys
import time

def test_spec(nvlink, spec, fromtime):
    print(f"\n--- Testing Data Spec: {spec} ---")
    try:
        rc, _, dl_count, _ = nvlink.NVOpen(spec, fromtime, 1, 0, 0, "")
        if rc < 0 and rc not in (-301, -1):
            print(f"NVOpen failed with code {rc}")
            return
            
        if rc in (-301, -1) or dl_count > 0:
            for _ in range(15):
                if nvlink.NVStatus() == 0:
                    break
                time.sleep(1)
                
        rc, buff, size, filename = nvlink.NVRead("", 110000, "")
        if rc == 0:
            try:
                decoded = buff.encode("latin-1").decode("cp932")
            except:
                decoded = str(buff)
            print(f"SUCCESS! Record type: {decoded[:2]}")
            print(f"Preview: {decoded[:200]}")
        else:
            print(f"No data returned (rc={rc})")
    except Exception as e:
        print(f"Error: {e}")

def main():
    try:
        print("Connecting to NVLink...")
        nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
        if nvlink.NVInit("UNKNOWN") != 0:
            print("NVInit failed")
            return
            
        specs_to_test = ["SHUSSO", "UMA", "ODDS", "BAMEI", "SEISEKI", "RACE", "KAIKAI"]
        for spec in specs_to_test:
            test_spec(nvlink, spec, "20260612000000")
            
    finally:
        try: nvlink.NVClose()
        except: pass

if __name__ == "__main__":
    main()
