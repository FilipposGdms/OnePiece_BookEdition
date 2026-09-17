@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   One Piece Book Edition
echo ========================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=py"
) else (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found in PATH.
        echo Install Python 3.11 or newer and try again.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :error
) else (
    echo [1/3] Virtual environment already exists.
)

echo [2/3] Installing/updating dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] Starting reader...
echo.
echo Open: http://127.0.0.1:8000
echo Press CTRL+C to stop the server.
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload
exit /b %errorlevel%

:error
echo.
echo [ERROR] Setup failed.
pause
exit /b 1
