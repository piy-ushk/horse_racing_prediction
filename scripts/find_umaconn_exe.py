import os

search_dirs = [
    r"C:\Program Files (x86)",
    r"C:\Program Files",
    r"C:\RateBuster",
    r"C:\UmaConn",
    r"C:\Users\Administrator\AppData\Local",
    r"C:\Users\Administrator\AppData\Roaming"
]

print("Searching for UmaConn executables...")
found = False

for root_dir in search_dirs:
    if os.path.exists(root_dir):
        for root, dirs, files in os.walk(root_dir):
            # Skip some deep/unlikely directories to speed up search
            if "Windows" in root or "Microsoft" in root:
                continue
            for file in files:
                if "umaconn" in file.lower() and file.lower().endswith(".exe"):
                    print(f"FOUND: {os.path.join(root, file)}")
                    found = True

if not found:
    print("Could not find any UmaConn executable. Is it installed?")
else:
    print("\nPlease try running one of the executables above by typing its full path in PowerShell.")
