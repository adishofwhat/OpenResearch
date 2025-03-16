@echo off
REM OpenResearch run script for Windows
REM This script provides a simple way to run the OpenResearch application

echo =======================================
echo        OpenResearch Application
echo =======================================
echo.

if "%1"=="" goto :usage

if "%1"=="api" goto :api
if "%1"=="cli" goto :cli
if "%1"=="cli-quiet" goto :cli-quiet
if "%1"=="docker" goto :docker
if "%1"=="docker-build" goto :docker-build
if "%1"=="install" goto :install
if "%1"=="help" goto :usage

echo Unknown option: %1
goto :usage

:usage
echo Usage: run.bat [OPTION]
echo.
echo Options:
echo   api        Start the API server
echo   cli        Run the CLI interface
echo   cli-quiet  Run the CLI interface in quiet mode (minimal output)
echo   docker     Start all services with Docker Compose
echo   docker-build Rebuild and start all services
echo   install    Install dependencies
echo   help       Show this help message
echo.
goto :eof

:install
echo Installing API dependencies...
pip install -r requirements.txt

echo Installing CLI dependencies...
pip install -r cli_requirements.txt

echo Dependencies installed successfully!
goto :eof

:api
echo Starting API server...
echo API will be available at http://localhost:8001
echo Press Ctrl+C to stop
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
goto :eof

:cli
echo Starting CLI interface...
echo.
python cli.py %2 %3 %4 %5 %6 %7 %8 %9
goto :eof

:cli-quiet
echo Starting CLI interface in quiet mode...
echo.
python cli.py --quiet %2 %3 %4 %5 %6 %7 %8
goto :eof

:docker
echo Starting services with Docker Compose...
echo This may take a few minutes
echo.
docker-compose up
goto :eof

:docker-build
echo Rebuilding and starting services with Docker Compose...
echo This may take a few minutes
echo.
docker-compose up --build
goto :eof 