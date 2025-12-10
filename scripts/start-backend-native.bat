@echo off
REM =======================================================================
REM i3T4AN (Ethan Blair)
REM Project:      Vector Knowledge Base
REM File:         Native backend startup script (Windows)
REM =======================================================================

echo === Vector Knowledge Base - Native Backend Startup ===
echo.

SET VENV_DIR=venv
SET BACKEND_DIR=backend
SET PORT=8000

REM Check if Docker services are running
echo Checking Docker services...
docker ps | findstr vkb-qdrant >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Qdrant container not running.
    echo Starting Qdrant and Frontend containers...
    docker-compose up -d qdrant frontend
    echo Waiting for Qdrant to be ready...
    timeout /t 5 /nobreak >nul
) else (
    echo Qdrant container is running
)

REM Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

echo Using Python:
python --version

REM Create virtual environment if it doesn't exist
if not exist "%VENV_DIR%\" (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
)

REM Activate virtual environment
echo Activating virtual environment...
call %VENV_DIR%\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

REM Check GPU availability
echo.
echo Detecting compute device...
python -c "import torch; print('  GPU: CUDA (' + torch.cuda.get_device_name(0) + ')' if torch.cuda.is_available() else '  GPU: Not available, using CPU'); print('  PyTorch version:', torch.__version__)"

REM Set environment variables for native mode
SET QDRANT_HOST=localhost
SET QDRANT_PORT=6333

echo.
echo Starting backend server on http://localhost:%PORT%
echo Press Ctrl+C to stop

REM Display MCP status
echo.
echo MCP Server Configuration:
if "%MCP_ENABLED%"=="" SET MCP_ENABLED=true
if "%MCP_PATH%"=="" SET MCP_PATH=/mcp
if "%MCP_ENABLED%"=="true" (
    echo   MCP Endpoint: http://localhost:%PORT%%MCP_PATH%
    echo   Connect Claude Desktop or other MCP clients to this URL
) else (
    echo   MCP Server: Disabled
)
echo.

REM Change to backend directory and start
cd %BACKEND_DIR%
uvicorn main:app --host 0.0.0.0 --port %PORT% --reload
