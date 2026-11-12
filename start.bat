@echo off
setlocal
cd /d "%~dp0"
title Mai Sakurajima Tutor

rem ---- 1. Python installed? ----
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11 or newer from python.org
  echo and tick "Add python.exe to PATH" during the install.
  pause
  exit /b 1
)

rem ---- 2. First run: create .env ----
if not exist .env copy .env.example .env >nul

rem ---- 3. Groq key filled in? ----
findstr /c:"paste_your_groq_key_here" .env >nul
if not errorlevel 1 (
  echo.
  echo Paste your Groq API key after GROQ_API_KEY=  then save and close Notepad.
  start /wait notepad .env
)

rem ---- 4. Install packages the first time ----
python -c "import fastapi, uvicorn, httpx" >nul 2>nul
if errorlevel 1 (
  echo Installing required packages, this happens only once...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Package install failed. Check your internet connection.
    pause
    exit /b 1
  )
)

rem ---- 5. Is Voicebox running? ----
powershell -NoProfile -Command "try { Invoke-WebRequest http://localhost:17493/docs -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo.
  echo WARNING: Voicebox does not seem to be running. Open the Voicebox app,
  echo otherwise Mai will not be able to speak.
  echo.
)

rem ---- 6. Open the browser shortly after the server starts, then run it ----
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"
echo Starting the tutor. Close this window to stop it.
python server.py
pause
