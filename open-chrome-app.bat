@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"
set "APP_TOKEN=%~1"
if not defined APP_TOKEN exit /b 1
if not exist "%CHROME%" exit /b 1

for /L %%I in (1,1,90) do (
  "%PY%" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/config', timeout=1)" >nul 2>&1 && goto :open_app
  timeout /t 1 /nobreak >nul
)
exit /b 1

:open_app
start "" "%CHROME%" --app=http://127.0.0.1:8000/#app_shutdown=%APP_TOKEN% --no-first-run --no-default-browser-check
exit /b 0
