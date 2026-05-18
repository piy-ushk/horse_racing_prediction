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


def create_task(hour: int = None, minute: int = None) -> bool:
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
    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' created/updated.")
        print(f"     Script : {SCRIPT_PATH}")
        print(f"     Time   : {time_str} daily")
        return True
    print(f"[FAIL] {result.stderr.strip()}")
    return False


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
