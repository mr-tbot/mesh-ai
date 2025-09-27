@echo off
setlocal

REM --- Always start in the folder where this .bat lives ---
cd /d "%~dp0"

REM --- Activate virtual environment if it exists ---
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

REM --- Run mesh-ai, accepting either underscore or hyphen ---
if exist "mesh_ai.py" (
  python mesh_ai.py %*
) else if exist "mesh-ai.py" (
  python mesh-ai.py %*
) else (
  echo [ERROR] Could not find mesh_ai.py or mesh-ai.py in: %cd%
  echo Available Python files:
  dir /b *.py
  pause
  exit /b 1
)

pause