@echo off
chcp 65001 > nul
echo ================================================
echo   Stock Screener - Stopping servers...
echo ================================================

REM Kill process listening on port 8000 (backend)
set BACKEND_KILLED=0
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a > nul 2>&1
    set BACKEND_KILLED=1
)
if %BACKEND_KILLED%==1 (
    echo [OK] Backend stopped (port 8000)
) else (
    echo [--] Backend was not running
)

REM Kill process listening on port 5173 (frontend)
set FRONTEND_KILLED=0
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a > nul 2>&1
    set FRONTEND_KILLED=1
)
if %FRONTEND_KILLED%==1 (
    echo [OK] Frontend stopped (port 5173)
) else (
    echo [--] Frontend was not running
)

REM Also close the console windows by title (best-effort)
taskkill /fi "WINDOWTITLE eq StockScreener-Backend" /f > nul 2>&1
taskkill /fi "WINDOWTITLE eq StockScreener-Frontend" /f > nul 2>&1

echo.
echo ================================================
echo   Done. All Stock Screener servers stopped.
echo ================================================
pause
