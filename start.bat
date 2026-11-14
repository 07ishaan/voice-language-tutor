@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Voice Language Tutor Setup

rem Use the bundled project venv; create it with Python 3.11 on first launch.
set "PY=%~dp0.venv\Scripts\python.exe"
set "BASEPY="
if not exist "%PY%" goto find_python
goto python_ready

:find_python
py -3.11 --version >nul 2>nul
if not errorlevel 1 (
  set "BASEPY=py -3.11"
  goto make_venv
)

where winget >nul 2>nul
if errorlevel 1 goto no_python
echo Installing Python 3.11 for this Windows account...
winget install --id Python.Python.3.11 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto install_python_failed
py -3.11 --version >nul 2>nul
if not errorlevel 1 (
  set "BASEPY=py -3.11"
  goto make_venv
)
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" goto make_venv_from_installed_python
goto install_python_failed

:make_venv
echo Creating the app's private Python environment...
%BASEPY% -m venv "%~dp0.venv"
if errorlevel 1 goto setup_failed
goto python_ready

:make_venv_from_installed_python
echo Creating the app's private Python environment...
"%LocalAppData%\Programs\Python\Python311\python.exe" -m venv "%~dp0.venv"
if errorlevel 1 goto setup_failed

:python_ready
"%PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,11) else 1)" >nul 2>nul
if errorlevel 1 (
  echo This app needs Python 3.11. Remove the .venv folder and run start.bat again.
  pause
  exit /b 1
)

"%PY%" -c "import fastapi,uvicorn,httpx,torch,torchaudio; from chatterbox.mtl_tts import ChatterboxMultilingualTTS" >nul 2>nul
if errorlevel 1 goto install_dependencies
goto dependencies_ready

:install_dependencies
echo Installing the app and Chatterbox. This may take several minutes and several GB of downloads.
"%PY%" -m pip install --upgrade pip
if errorlevel 1 goto setup_failed
"%PY%" -m pip install "setuptools<81" wheel
if errorlevel 1 goto setup_failed
"%PY%" -m pip install --only-binary=:all: PyYAML==6.0.2
if errorlevel 1 goto setup_failed
nvidia-smi -L >nul 2>nul
if errorlevel 1 goto install_cpu_torch
echo NVIDIA GPU detected; installing PyTorch with CUDA 12.4 support.
"%PY%" -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
if errorlevel 1 goto setup_failed
goto install_app_packages

:install_cpu_torch
echo No NVIDIA driver detected; installing the CPU version of PyTorch.
"%PY%" -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto setup_failed

:install_app_packages
"%PY%" -m pip install -r requirements.txt -r requirements-chatterbox.txt
if errorlevel 1 goto setup_failed
"%PY%" -c "import fastapi,uvicorn,httpx,torch,torchaudio; from chatterbox.mtl_tts import ChatterboxMultilingualTTS" >nul 2>nul
if errorlevel 1 goto chatterbox_failed

:dependencies_ready

rem A clean distribution has no .env. Ask for this PC's API key and optional WAV.
if not exist .env (
  copy /y .env.example .env >nul
  if errorlevel 1 goto setup_failed
)
"%PY%" configure_first_run.py
if errorlevel 1 goto setup_failed

set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" (
  where winget >nul 2>nul
  if errorlevel 1 goto no_chrome
  echo Installing Google Chrome...
  winget install --id Google.Chrome --exact --silent --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto install_chrome_failed
  set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"
)
if not exist "%CHROME%" goto no_chrome

rem Start one Chrome app window and stop the local server when that window closes.
set "TOKEN_FILE=%TEMP%\voice-tutor-token-%RANDOM%-%RANDOM%.tmp"
"%PY%" -c "import secrets; print(secrets.token_urlsafe(32))" > "%TOKEN_FILE%"
if errorlevel 1 goto setup_failed
set /p "APP_TOKEN="<"%TOKEN_FILE%"
del /q "%TOKEN_FILE%" >nul 2>&1
if not defined APP_TOKEN goto setup_failed
set "VOICE_TUTOR_APP_TOKEN=%APP_TOKEN%"
start "" /b "%ComSpec%" /c ""%~dp0open-chrome-app.bat" "%APP_TOKEN%""
echo Starting the tutor in Chrome. Close its app window to stop the server.
"%PY%" server.py
set "SERVER_EXIT=%ERRORLEVEL%"
if not "%SERVER_EXIT%"=="0" (
  echo The tutor server stopped with an error.
  pause
)
exit /b %SERVER_EXIT%

:no_python
echo Python 3.11 and winget were not found. Install Python 3.11, then run this launcher again.
pause
exit /b 1
:install_python_failed
echo Could not install Python automatically. Install Python 3.11 and run start.bat again.
pause
exit /b 1
:no_chrome
echo Chrome was not found or could not be installed. Install Google Chrome and run start.bat again.
pause
exit /b 1
:install_chrome_failed
echo Chrome installation failed. Install Google Chrome and run start.bat again.
pause
exit /b 1
:chatterbox_failed
echo The installed Chatterbox package does not include multilingual support.
echo Confirm that chatterbox-tts 0.1.6 installed successfully, then run start.bat again.
pause
exit /b 1
:setup_failed
echo Setup did not complete. Check your internet connection and available disk space, then run start.bat again.
pause
exit /b 1
