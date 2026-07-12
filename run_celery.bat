@echo off
chcp 65001 >nul
cd /d "%~dp0"

IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Create it with: python -m venv .venv
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo ===================================================
echo   Cutanix - Celery Worker
echo   App: cutanix   Broker: %CELERY_BROKER_URL%
echo ===================================================
echo.

celery -A cutanix worker -l info -P solo

echo.
echo [Worker stopped]
pause
