@echo off
cd /d "C:\keiba\horce_racing_prediction"
title Horse Racing Prediction Control Panel
color 0B

:menu
cls
echo ==========================================================
echo       HORSE RACING PREDICTION SYSTEM CONTROL PANEL
echo ==========================================================
echo.
echo   [1] Start Web Admin Dashboard (Flask)
echo   [2] Run Connection Tests (JV-Link / UmaConn)
echo   [3] Run Prediction Pipeline Manually (Fetch, Predict, Publish)
echo   [4] Check Windows Task Scheduler Status
echo   [5] Register/Update Windows Task Scheduler (Requires Admin)
echo   [6] Open Today's Log File in Notepad
echo   [7] Exit
echo.
echo ==========================================================
set /p user_choice="Please select an option [1-7]: "

if "%user_choice%"=="1" goto start_web
if "%user_choice%"=="2" goto test_conn
if "%user_choice%"=="3" goto run_pipeline
if "%user_choice%"=="4" goto check_task
if "%user_choice%"=="5" goto setup_task
if "%user_choice%"=="6" goto open_logs
if "%user_choice%"=="7" goto end

echo Invalid option. Please try again.
pause
goto menu

:start_web
cls
echo ==========================================================
echo  STARTING WEB ADMIN DASHBOARD
echo ==========================================================
echo  URL: http://127.0.0.1:5000/admin
echo  Keep this window open while accessing the dashboard.
echo  Press Ctrl+C in this window to stop the server.
echo ==========================================================
echo.
python web\app.py
echo.
pause
goto menu

:test_conn
cls
echo ==========================================================
echo  RUNNING CONNECTION TESTS (JV-Link / UmaConn)
echo ==========================================================
echo.
python scripts\test_connections.py
echo.
pause
goto menu

:run_pipeline
cls
echo ==========================================================
echo  RUNNING PREDICTION PIPELINE MANUALLY
echo ==========================================================
echo.
python main.py
echo.
pause
goto menu

:check_task
cls
echo ==========================================================
echo  CHECKING WINDOWS TASK SCHEDULER STATUS
echo ==========================================================
echo.
python scheduler\setup_windows_task.py --status
echo.
pause
goto menu

:setup_task
cls
echo ==========================================================
echo  REGISTERING/UPDATING WINDOWS TASK SCHEDULER
echo ==========================================================
echo  NOTE: This action requires Administrator privileges.
echo ==========================================================
echo.
python scheduler\setup_windows_task.py
echo.
pause
goto menu

:open_logs
cls
echo ==========================================================
echo  OPENING TODAY'S LOG FILE
echo ==========================================================
echo.
:: Get current date in YYYY-MM-DD format using PowerShell (locale independent)
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd'"`) do set "today=%%i"
set "logfile=logs\%today%.log"
if exist "%logfile%" (
    echo Opening %logfile% in Notepad...
    start notepad.exe "%logfile%"
    timeout /t 1 >nul
) else (
    echo Log file not found: %logfile%
    echo The pipeline might not have run today yet.
)
echo.
pause
goto menu

:end
echo Exiting Control Panel...
timeout /t 1 >nul
