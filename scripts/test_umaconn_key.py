import win32com.client  # type: ignore
import sys

key = "FAA9-6K7A-85Y3-XGJK-L"

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    
    print("Testing NVInit('UNKNOWN')...")
    rc1 = nvlink.NVInit("UNKNOWN")
    print(f"rc = {rc1}")
    
    print(f"Testing NVInit('{key}')...")
    rc2 = nvlink.NVInit(key)
    print(f"rc = {rc2}")
    
    print(f"Testing NVInit('{key.replace('-', '')}')...")
    rc3 = nvlink.NVInit(key.replace("-", ""))
    print(f"rc = {rc3}")
    
except Exception as e:
    print(f"Error: {e}")
