@echo off
setlocal enabledelayedexpansion
title Shorts Maker
cd /d "%~dp0"
set TRIED=0

:find
set PY=
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>nul && set "PY=python"
if not defined PY for /d %%D in ("%LocalAppData%\Programs\Python\Python3*" "%ProgramFiles%\Python3*") do if exist "%%~D\python.exe" if not defined PY set "PY="%%~D\python.exe""
if defined PY goto found

if "%TRIED%"=="1" goto nopython
set TRIED=1
echo.
echo Python was not found on this computer. Trying to install it for you...
echo If Windows asks for permission, click Yes. This can take a few minutes.
echo.
where winget >nul 2>nul
if errorlevel 1 goto nopython
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
goto find

:nopython
echo.
echo ================================================================
echo  Shorts Maker needs Python and could not find or install it.
echo  1. Opening the Python download page for you now.
echo  2. Install it, and tick "Add python.exe to PATH" on the first screen.
echo  3. Then double-click Start Shorts Maker.bat again.
echo ================================================================
start "" https://www.python.org/downloads/
pause
exit /b 1

:found
echo Using Python: %PY%
%PY% updater.py
echo Checking add-ons (the first time takes a minute)...
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo The add-ons could not be installed. Check that this computer is online, then try again.
  echo If it keeps failing, send a photo of this window.
  pause
  exit /b 1
)
echo.
echo Starting Shorts Maker. Your browser will open. Keep this window open while you use it.
%PY% app.py
echo.
echo Shorts Maker stopped. If that was not on purpose, the message above says why.
pause
