@echo off
title CA FinConnect - Starting Website...
color 0A
echo.
echo  ==============================================
echo    CA FinConnect - Shrinath Shrimangale
echo  ==============================================
echo.
echo  [Step 1] Checking Python installation...
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo.
    echo  ERROR: Python is not installed!
    echo.
    echo  Please download and install Python from:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During install, check the box
    echo  "Add Python to PATH" before clicking Install.
    echo.
    pause
    start https://www.python.org/downloads/
    exit
)
echo  Python found! OK
echo.

echo  [Step 2] Installing required packages...
pip install flask werkzeug gunicorn razorpay >nul 2>&1
echo  All packages installed! OK
echo.

echo  [Step 3] Starting the website...
echo.
echo  ==============================================
echo   Website is RUNNING at: http://localhost:5000
echo   Open your browser and go to that address!
echo  ==============================================
echo.
echo  (Keep this window open while using the website)
echo  (Press Ctrl+C or close this window to stop)
echo.
start http://localhost:5000
python app.py
pause
