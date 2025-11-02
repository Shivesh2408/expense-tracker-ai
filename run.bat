@echo off
setlocal ENABLEDELAYEDEXPANSION

cd /d "%~dp0"

echo === Checking Python installation ===
set PY_CMD=
where py >nul 2>nul && set PY_CMD=py -3
if "%PY_CMD%"=="" (
  where python >nul 2>nul && set PY_CMD=python
)
if "%PY_CMD%"=="" (
  echo Python is not on PATH. Please install Python 3.11+ and check "Add to PATH".
  echo Download: https://www.python.org/downloads/
  pause
  exit /b 1
)
for /f "tokens=*" %%v in ('%PY_CMD% --version 2^>^&1') do set PY_VER=%%v
echo Using: %PY_VER%

echo === Creating virtual environment (if missing) ===
if not exist .venv (
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
  )
)

echo === Activating virtual environment ===
call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)

echo === Installing dependencies ===
if exist requirements.txt (
  python -m pip install --upgrade pip
  if errorlevel 1 echo (pip upgrade failed, continuing...)
  python -m pip install -r requirements.txt
) else (
  echo requirements.txt not found. Installing Flask only...
  python -m pip install Flask
)
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo === Starting web server ===
python app.py
if errorlevel 1 (
  echo.
  echo The app exited with an error. Review the messages above.
  pause
  exit /b 1
)

endlocal
exit /b 0


