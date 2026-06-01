@echo off
echo ===================================================
echo   PSIV Auto-Tracker Local Relay Setup & Launch
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed on this system!
    echo Please install Python from the Microsoft Store or Python.org,
    echo and make sure to check "Add Python to PATH".
    pause
    exit /b
)

:: Automatically install required libraries quietly
echo [1/2] Checking and installing dependencies...
pip install -q Flask Flask-CORS

:: Launch your backend script silently in the background
echo [2/2] Launching your tracker memory relay...
echo.
echo Leave this window open while playing! You can close it when finished.
echo.
python sniffer.py

pause
