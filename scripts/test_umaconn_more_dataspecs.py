import win32com.client  # type: ignore

try:
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    nvlink.NVInit("UNKNOWN")
    
    dataspecs = [
        "RACEDIFN", "RACEDIF", "RACE_A", "RACE_B", "ODDS_A", "ODDS_B", "OD", "OZZ", "TAN", "FUKU", "ODDS", "BABA", "0B11", "0B12", "H1", "H2", "SE", "CH", "RA", "PAY"
    ]
    
    print("--- Testing more dataspecs with NVOpen ---")
    for spec in dataspecs:
        rc = nvlink.NVOpen(spec, "20260612000000", 1, 0, 0, "")
        if isinstance(rc, tuple) and rc[0] != -111:
            print(f"Dataspec {spec} -> ACCEPTED! rc={rc}")
        elif not isinstance(rc, tuple) and rc != -111:
            print(f"Dataspec {spec} -> ACCEPTED! rc={rc}")
        
        # Abort any started download
        if isinstance(rc, tuple) and rc[0] in (-1, -301):
            nvlink.NVCancel()
            
    nvlink.NVClose()
except Exception as e:
    print(f"Error: {e}")
