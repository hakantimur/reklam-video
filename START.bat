@echo off
setlocal
cd /d "%~dp0"

if not exist backend\.venv\Scripts\python.exe (
    echo [HATA] Backend kurulu degil. Once SETUP.bat calistirin.
    pause
    exit /b 1
)

echo === Local Ad Director baslatiliyor ===

set LAD_PORT=8765
set PIDFILE=%~dp0.run\backend.pid
if not exist "%~dp0.run" mkdir "%~dp0.run"

echo Backend baslatiliyor (port %LAD_PORT%)...
start "LocalAdDirector-Backend" /min cmd /c "backend\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port %LAD_PORT% --app-dir backend > .run\backend.log 2>&1"

echo Servisin ayaga kalkmasi bekleniyor...
set /a tries=0
:waitloop
set /a tries+=1
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:%LAD_PORT%/api/v1/health > "%~dp0.run\healthcode.txt" 2>nul
set /p HEALTHCODE=<"%~dp0.run\healthcode.txt"
if "%HEALTHCODE%"=="200" goto ready
if %tries% GEQ 30 (
    echo [HATA] Backend %LAD_PORT% portunda ayaga kalkmadi. Log: .run\backend.log
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto waitloop

:ready
echo Backend hazir: http://127.0.0.1:%LAD_PORT%
start "" http://127.0.0.1:%LAD_PORT%
echo.
echo Uygulamayi kapatmak icin STOP.bat calistirin.
echo Bu pencereyi kapatabilirsiniz; arka plan servisi calismaya devam eder.
pause
