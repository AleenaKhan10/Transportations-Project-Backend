@echo off
REM Installation and Test Runner for WebSocket Transcription Test
REM This batch file automates the setup and execution of the test

echo ============================================================
echo   WebSocket Transcription Test - Setup and Run
echo ============================================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo [1/4] Node.js found:
node --version
echo.

REM Check if npm is installed
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm is not installed or not in PATH
    pause
    exit /b 1
)

echo [2/4] npm found:
npm --version
echo.

REM Install dependencies
echo [3/4] Installing dependencies...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully!
echo.

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found!
    echo Please create .env file from .env.example and configure:
    echo   - TEST_USERNAME
    echo   - TEST_PASSWORD
    echo   - API_BASE_URL
    echo   - WS_BASE_URL
    echo.
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo Please edit .env file with your credentials before running the test.
    echo.
    pause
)

REM Run the test
echo [4/4] Running WebSocket test...
echo.
echo ============================================================
echo   Test Starting...
echo ============================================================
echo.

node websocket_test.js

echo.
echo ============================================================
echo   Test Complete
echo ============================================================
pause
