@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ================================================
echo   Stock Screener - Starting...
echo ================================================

REM Check Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

REM Check Node.js
node --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

REM Install frontend dependencies if node_modules is missing
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    npm install
    cd ..
)

REM Start backend in a new window
start "StockScreener-Backend" cmd /k "cd /d %~dp0 && echo [Backend] Starting uvicorn on http://localhost:8000 && python -m uvicorn backend.main:app --reload --port 8000"

REM Start frontend in a new window
start "StockScreener-Frontend" cmd /k "cd /d %~dp0\frontend && echo [Frontend] Starting Vite on http://localhost:5173 && npm run dev"

REM Wait 5 seconds for servers to start, then open browser
echo Waiting for servers to start...
timeout /t 5 /nobreak > nul

echo Opening browser...
start http://localhost:5173

echo.
echo ================================================
echo   Both servers are running!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   Run stop.bat to shut down both servers.
echo ================================================
timeout /t 3 /nobreak > nul
