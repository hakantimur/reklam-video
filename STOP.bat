@echo off
setlocal
cd /d "%~dp0"

echo === Local Ad Director durduruluyor ===
if not exist "%~dp0.run" mkdir "%~dp0.run"

REM Yalnizca START.bat'in actigi, benzersiz pencere basligina sahip sureci
REM (ve alt surecleri /T ile) kapatir; baska hicbir uygulamaya dokunmaz.
REM Not: taskkill "eslesme yok" durumunda da exit code 0 doner, bu yuzden
REM sonuc metnine bakiyoruz, errorlevel'a degil.
taskkill /FI "WINDOWTITLE eq LocalAdDirector-Backend*" /T /F > "%~dp0.run\stopresult.txt" 2>&1
findstr /C:"SUCCESS" "%~dp0.run\stopresult.txt" >nul
if errorlevel 1 (
    echo Calisan bir Local Ad Director backend sureci bulunamadi.
) else (
    echo Backend durduruldu.
)

echo Tamamlandi.
pause
