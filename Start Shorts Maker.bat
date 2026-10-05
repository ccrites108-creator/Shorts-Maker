@echo off
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
%PY% updater.py
echo Checking add-ons (the first time takes a minute)...
%PY% -m pip install -q -r requirements.txt
echo.
echo Starting Shorts Maker. Your browser will open. Keep this window open while you use it.
%PY% app.py
pause
