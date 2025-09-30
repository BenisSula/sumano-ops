@echo off
REM Sumano OMS Development Startup Script for Windows

echo 🚀 Starting Sumano OMS Development Environment
echo ==============================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo 📝 Creating .env file from template...
    copy env.example .env
    echo ✅ .env file created. Please review and update as needed.
)

REM Build and start services
echo 🔨 Building and starting services...
docker-compose up --build -d

REM Wait for services to start
echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check health
echo 🏥 Checking service health...
curl -f http://localhost:8000/health/ >nul 2>&1
if errorlevel 1 (
    echo ❌ Backend health check failed. Check logs with: docker-compose logs
) else (
    echo ✅ Backend is healthy!
    echo 🌐 Backend API: http://localhost:8000
    echo 🏥 Health Check: http://localhost:8000/health/
    echo 📄 PDF Test: http://localhost:8000/api/pdf/test/
)

echo.
echo 📋 Useful commands:
echo   View logs: docker-compose logs -f
echo   Stop services: docker-compose down
echo   Restart: docker-compose restart
echo   Shell access: docker-compose exec ops_backend bash

pause
