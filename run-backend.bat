@echo off
setlocal
cd /d "%~dp0ai03-backend"
if not exist .venv (
  python -m venv .venv
  if errorlevel 1 goto error
)
call .venv\Scripts\activate.bat
if not exist .deps-installed (
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if errorlevel 1 goto error
  echo installed> .deps-installed
)
if not exist .env copy .env.example .env >nul
python run.py
 goto end
:error
echo Setup failed. Ensure Python 3.10+ is installed and available as 'python'.
pause
:end
endlocal
