import win32com.client  # type: ignore

try:
    print("Attempting NVSetUIProperties()...")
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    
    # Sometimes it requires an empty string or 0
    try:
        nvlink.NVSetUIProperties()
        print("Success! Did a window open?")
    except Exception as e:
        print(f"Failed with no args: {e}")
        try:
            nvlink.NVSetUIProperties(0)
            print("Success with arg 0!")
        except Exception as e2:
            print(f"Failed with arg 0: {e2}")

except Exception as e:
    print(f"Error: {e}")
