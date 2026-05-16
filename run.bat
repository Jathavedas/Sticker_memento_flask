@echo off
echo ===================================================
echo   IGNITING MEMENTO WORLD STICKER ENGINE...
echo ===================================================
echo.

:: Activate the virtual environment
call venv\Scripts\activate.bat

:: Open the browser automatically
echo Opening browser to http://127.0.0.1:8000...
start http://127.0.0.1:8000

:: Start the Flask server
echo Starting Server... Keep this window open!
python app.py

pause