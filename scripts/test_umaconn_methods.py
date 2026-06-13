import win32com.client  # type: ignore
import sys

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    methods = [m for m in dir(nvlink) if not m.startswith("_")]
    print("Methods available in NVDTLabLib.NVLink:")
    for m in methods:
        print(f" - {m}")
except Exception as e:
    print(f"Error: {e}")
