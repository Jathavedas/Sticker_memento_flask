@echo off
echo ===================================================
echo   MEMENTO WORLD - STICKER ENGINE SETUP
echo ===================================================
echo.

echo [1/3] Creating Python Virtual Environment...
python -m venv venv

echo [2/3] Activating Virtual Environment...
call venv\Scripts\activate.bat

echo [3/3] Installing Required Libraries (This may take a minute)...
pip install --upgrade pip
pip install flask opencv-python numpy pillow werkzeug

echo.
echo ===================================================
echo   SETUP COMPLETE! 
echo   You can now double-click 'run.bat' to start.
echo ===================================================
pause