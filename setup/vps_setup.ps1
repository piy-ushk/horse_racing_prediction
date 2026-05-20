# =============================================================
# Horse Racing Prediction System — Windows VPS Setup Script
# =============================================================
# Run once on a fresh Windows Server VPS, as Administrator:
#
#   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\setup\vps_setup.ps1
#
# What this does:
#   1. Installs Python 3.11 (32-bit) — required for UmaConn DLL
#   2. Installs Git
#   3. pip-installs all dependencies + pywin32 (32-bit)
#   4. Runs pywin32 post-install (registers COM support)
#   5. Copies .env.example → .env (fill in JRAVAN_SOFTWARE_ID manually after)
#   6. Verifies the demo pipeline runs correctly
#
# Manual steps BEFORE running this script:
#   - Install JV-Link from jra-van.jp and register license key
#   - Install UmaConn and register license via GUI (one-time)
#   - Copy project files to C:\keiba\horce_racing_prediction\
#
# Manual step AFTER running this script:
#   - Obtain JRAVAN_SOFTWARE_ID from jra-van.jp (see Step 5 of SETUP_VPS.md)
#   - Edit C:\keiba\horce_racing_prediction\.env and fill in:
#       JRAVAN_SOFTWARE_ID=<your software ID>
#       WP_USERNAME=<wordpress username>
#       WP_APP_PASSWORD=<wordpress app password>
#       DEMO_MODE=false
# =============================================================

$ErrorActionPreference = "Stop"

$PROJECT_DIR = "C:\keiba\horce_racing_prediction"

function Write-Step($msg) {
    Write-Host "`n>>> $msg" -ForegroundColor Cyan
}

function Write-OK($msg) {
    Write-Host "    [OK] $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "    [!!] $msg" -ForegroundColor Yellow
}

# --- 0. Admin check ---
Write-Step "Checking administrator privileges..."
$currentPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: Run this script as Administrator (right-click PowerShell -> Run as Administrator)" -ForegroundColor Red
    exit 1
}
Write-OK "Running as Administrator"

# --- 1. Project directory check ---
Write-Step "Checking project directory at $PROJECT_DIR..."
if (-not (Test-Path $PROJECT_DIR)) {
    Write-Host "ERROR: Project not found at $PROJECT_DIR" -ForegroundColor Red
    Write-Host "       Copy the project folder there first, then re-run this script." -ForegroundColor Yellow
    exit 1
}
Write-OK "Project directory exists"

# --- 2. Python 3.11 32-bit ---
Write-Step "Installing Python 3.11 (32-bit / x86)..."
Write-Warn "UmaConn's NVDTLab.dll is 32-bit only — 64-bit Python CANNOT load it."

$pythonInstalled = $false
try {
    $ver = & python -c "import struct; print(struct.calcsize('P')*8)" 2>&1
    if ($ver -eq "32") {
        Write-OK "Python 32-bit already installed"
        $pythonInstalled = $true
    } else {
        Write-Warn "Python found but it is $ver-bit — need 32-bit for UmaConn"
    }
} catch {
    Write-Warn "Python not found in PATH"
}

if (-not $pythonInstalled) {
    # Python 3.11.9 32-bit installer (stable LTS-compatible release)
    $pyUrl      = "https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe"
    $pyInstaller = "$env:TEMP\python-3.11.9-x86.exe"

    Write-Host "    Downloading Python 3.11.9 (32-bit)..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing

    Write-Host "    Installing (silent)..." -ForegroundColor Gray
    Start-Process -FilePath $pyInstaller `
        -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" `
        -Wait -NoNewWindow

    # Refresh PATH in current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")

    $ver = & python -c "import struct; print(struct.calcsize('P')*8)"
    if ($ver -eq "32") {
        Write-OK "Python 3.11 (32-bit) installed successfully"
    } else {
        Write-Host "ERROR: Python installed but is $ver-bit. Install 32-bit manually from python.org." -ForegroundColor Red
        exit 1
    }
}

# --- 3. Git ---
Write-Step "Checking Git..."
try {
    $gitVer = & git --version 2>&1
    Write-OK "Git already installed: $gitVer"
} catch {
    Write-Host "    Git not found — downloading installer..." -ForegroundColor Gray
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-32-bit.exe"
    $gitInstaller = "$env:TEMP\git-installer.exe"
    Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller -UseBasicParsing
    Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT /NORESTART" -Wait -NoNewWindow
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-OK "Git installed"
}

# --- 4. pip dependencies ---
Write-Step "Installing Python dependencies..."
Set-Location $PROJECT_DIR

Write-Host "    pip install -r requirements.txt..." -ForegroundColor Gray
& python -m pip install --upgrade pip --quiet
& python -m pip install -r requirements.txt --quiet

Write-Host "    pip install pywin32 (32-bit build)..." -ForegroundColor Gray
& python -m pip install pywin32 --quiet

Write-Host "    Running pywin32 post-install (registers COM DLL support)..." -ForegroundColor Gray
& python -m pywin32_postinstall -install
Write-OK "All dependencies installed"

# --- 5. .env file ---
Write-Step "Setting up .env configuration..."
$envFile    = Join-Path $PROJECT_DIR ".env"
$envExample = Join-Path $PROJECT_DIR ".env.example"

if (Test-Path $envFile) {
    Write-OK ".env already exists — skipping copy (will not overwrite)"
} else {
    Copy-Item $envExample $envFile
    Write-OK ".env created from .env.example"
    Write-Warn "Edit $envFile and fill in:"
    Write-Warn "  JRAVAN_SOFTWARE_ID  — from jra-van.jp (see SETUP_VPS.md step 3)"
    Write-Warn "  WP_USERNAME / WP_APP_PASSWORD — from WordPress admin"
    Write-Warn "  DEMO_MODE=false     — set AFTER the above are filled in"
}

# --- 6. Verify JV-Link COM registration ---
Write-Step "Checking JV-Link COM registration (JVDTLab.JVLink)..."
$jvlinkCheck = & python -c "
import winreg, sys
key = r'SOFTWARE\Classes\JVDTLab.JVLink'
try:
    winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key)
    print('FOUND')
except FileNotFoundError:
    print('NOT_FOUND')
" 2>&1

if ($jvlinkCheck -match "FOUND") {
    Write-OK "JV-Link COM object registered in registry"
} else {
    Write-Warn "JV-Link COM object NOT found in registry"
    Write-Warn "Install JV-Link from jra-van.jp, then run:"
    Write-Warn "  python scheduler\setup_windows_task.py --status   (to confirm after install)"
}

# --- 7. Verify UmaConn DLL ---
Write-Step "Checking UmaConn DLL (NVDTLab.dll)..."
$nvDll = "C:\Windows\SysWOW64\NVDTLab.dll"
if (Test-Path $nvDll) {
    Write-OK "NVDTLab.dll found at $nvDll"
} else {
    Write-Warn "NVDTLab.dll NOT found at $nvDll"
    Write-Warn "Install UmaConn from saikyo.k-ba.com and run GUI once to register license"
}

$umaCheck = & python -c "
import winreg, sys
key = r'SOFTWARE\Classes\NVDTLabLib.NVLink'
try:
    winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key)
    print('FOUND')
except FileNotFoundError:
    try:
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Classes\NVDTLabLib.NVLink')
        print('FOUND')
    except FileNotFoundError:
        print('NOT_FOUND')
" 2>&1

if ($umaCheck -match "FOUND") {
    Write-OK "UmaConn COM object registered in registry"
} else {
    Write-Warn "UmaConn COM object NOT found in registry"
    Write-Warn "Install UmaConn and run GUI once to complete registration"
}

# --- 8. Demo pipeline smoke test ---
Write-Step "Running demo pipeline smoke test..."
$testResult = & python scripts\test_pipeline.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-OK "Demo pipeline passed"
} else {
    Write-Host "    [FAIL] Demo pipeline failed:" -ForegroundColor Red
    Write-Host $testResult -ForegroundColor Red
    Write-Host "`nFix errors above before continuing." -ForegroundColor Yellow
    exit 1
}

# --- Done ---
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS (manual — required before going live):"
Write-Host ""
Write-Host "  1. Get your JV-Link Software ID:"
Write-Host "       - Log into jra-van.jp -> ソフトウェア登録 -> 新規登録"
Write-Host "       - Register your application and copy the issued ソフトウェアID"
Write-Host ""
Write-Host "  2. Edit $envFile and set:"
Write-Host "       JRAVAN_SOFTWARE_ID=<your software ID>"
Write-Host "       WP_USERNAME=<your wp username>"
Write-Host "       WP_APP_PASSWORD=<your app password>"
Write-Host "       DEMO_MODE=false"
Write-Host ""
Write-Host "  3. Run the real connection test:"
Write-Host "       python scripts\test_connections.py"
Write-Host ""
Write-Host "  4. Register the daily Task Scheduler job (as Administrator):"
Write-Host "       python scheduler\setup_windows_task.py"
Write-Host ""
Write-Host "  5. Run the live pipeline once manually to verify:"
Write-Host "       python main.py"
Write-Host ""
