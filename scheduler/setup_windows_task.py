"""
Windows Task Scheduler helper.

Run once (as Administrator) to register the daily pipeline task.
Usage:
    python scheduler/setup_windows_task.py              # create/update at configured time
    python scheduler/setup_windows_task.py --time HH:MM # create at a specific time
    python scheduler/setup_windows_task.py --delete     # remove the task
    python scheduler/setup_windows_task.py --status     # show current task info
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

TASK_NAME = "HorseRacingPrediction"
SCRIPT_PATH = Path(__file__).parent.parent / "main.py"
PYTHON_EXE = sys.executable


import tempfile
import xml.etree.ElementTree as ET

def create_task(hour: int | None = None, minute: int | None = None) -> bool:
    if hour is None or minute is None:
        hour, minute = config.get_schedule()
    time_str = f"{hour:02d}:{minute:02d}"
    cmd = [
        "schtasks", "/Create",
        "/TN", TASK_NAME,
        "/TR", f'"{PYTHON_EXE}" "{SCRIPT_PATH}"',
        "/SC", "DAILY",
        "/ST", time_str,
        "/RL", "HIGHEST",
        "/F",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[FAIL] {result.stderr.strip()}")
        return False
        
    # Now export, modify, and re-import to set advanced settings
    xml_out = subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME, "/XML"], capture_output=True, text=True)
    if xml_out.returncode == 0:
        try:
            # Task Scheduler XML has a default namespace
            ET.register_namespace("", "http://schemas.microsoft.com/windows/2004/02/mit/task")
            root = ET.fromstring(xml_out.stdout)
            ns = {"ns": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
            
            settings = root.find("ns:Settings", ns)
            if settings is not None:
                # Run task as soon as possible after a scheduled start is missed
                start_when_avail = settings.find("ns:StartWhenAvailable", ns)
                if start_when_avail is None:
                    ET.SubElement(settings, "StartWhenAvailable").text = "true"
                else:
                    start_when_avail.text = "true"
                    
                # Wake the computer to run this task
                wake = settings.find("ns:WakeToRun", ns)
                if wake is None:
                    ET.SubElement(settings, "WakeToRun").text = "true"
                else:
                    wake.text = "true"
                    
                # Allow running on battery
                disallow_bat = settings.find("ns:DisallowStartIfOnBatteries", ns)
                if disallow_bat is not None: disallow_bat.text = "false"
                stop_bat = settings.find("ns:StopIfGoingOnBatteries", ns)
                if stop_bat is not None: stop_bat.text = "false"

            actions = root.find("ns:Actions", ns)
            if actions is not None:
                exec_action = actions.find("ns:Exec", ns)
                if exec_action is not None:
                    # Set Start In (WorkingDirectory)
                    wd = exec_action.find("ns:WorkingDirectory", ns)
                    if wd is None:
                        ET.SubElement(exec_action, "WorkingDirectory").text = str(SCRIPT_PATH.parent)
                    else:
                        wd.text = str(SCRIPT_PATH.parent)

            # Write modified XML to a temp file and import it
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xml", mode="w", encoding="utf-16") as f:
                temp_xml = f.name
                # ET.tostring doesn't add the XML declaration by default in all versions nicely for schtasks,
                # but schtasks usually accepts it.
                xml_str = ET.tostring(root, encoding="unicode")
                f.write(xml_str)
                
            subprocess.run(["schtasks", "/Create", "/TN", TASK_NAME, "/XML", temp_xml, "/F"], capture_output=True)
            Path(temp_xml).unlink(missing_ok=True)
        except Exception as e:
            print(f"[WARN] Could not apply advanced task settings: {e}")

    print(f"[OK] Task '{TASK_NAME}' created/updated.")
    print(f"     Script : {SCRIPT_PATH}")
    print(f"     Time   : {time_str} daily (WakeToRun Enabled)")
    return True


def delete_task() -> bool:
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' deleted.")
        return True
    print(f"[FAIL] {result.stderr.strip()}")
    return False


def get_task_status() -> str | None:
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--delete" in args:
        delete_task()
    elif "--status" in args:
        status = get_task_status()
        print(status if status else "Task not found.")
    elif "--time" in args:
        idx = args.index("--time")
        try:
            h, m = map(int, args[idx + 1].split(":"))
            create_task(h, m)
        except (IndexError, ValueError):
            print("Usage: --time HH:MM")
    else:
        create_task()
