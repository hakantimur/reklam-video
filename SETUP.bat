@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo === Local Ad Director - Kurulum ===
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi. https://python.org adresinden Python 3.11+ kurun.
    echo Bu pencere kapanmayacak.
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo [HATA] Node.js bulunamadi. https://nodejs.org adresinden kurun.
    pause
    exit /b 1
)

where adb >nul 2>&1
if errorlevel 1 (
    echo [UYARI] adb PATH'te bulunamadi. Android SDK platform-tools kurulu ve
    echo PATH'e eklenmis olmali. Emulator kontrolu bu olmadan calismaz.
    echo Kuruluma devam ediliyor, ancak Safha 4/5 canli testleri engellenecek.
)

echo.
echo [1/5] Backend Python ortami kuruluyor...
if not exist backend\.venv (
    python -m venv backend\.venv
)
call backend\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
call backend\.venv\Scripts\pip.exe install --quiet -e "backend[dev]"
if errorlevel 1 (
    echo [HATA] Backend bagimliliklari kurulamadi.
    pause
    exit /b 1
)

echo [2/5] Veritabani semasi uygulaniyor...
pushd backend
..\backend\.venv\Scripts\alembic.exe upgrade head
popd
if errorlevel 1 (
    echo [HATA] Migration basarisiz.
    pause
    exit /b 1
)

echo [3/5] ffmpeg / scrcpy kontrol ediliyor...
if exist scripts\setup\fetch_binaries.py (
    backend\.venv\Scripts\python.exe scripts\setup\fetch_binaries.py
) else (
    echo [UYARI] scripts\setup\fetch_binaries.py henuz yok, bu adim atlandi.
)

echo [4/5] Web arayuzu bagimliliklari kuruluyor...
call npm install --workspaces --if-present
if errorlevel 1 (
    echo [UYARI] npm install sirasinda hata olustu, web arayuzu calismayabilir.
)

echo [5/5] Web arayuzu derleniyor...
call npm run web:build --if-present
if errorlevel 1 (
    echo [UYARI] Web arayuzu derlenemedi; START.bat gelistirme sunucusuna dusecek.
)

echo.
echo === Kurulum tamamlandi ===
echo Uygulamayi baslatmak icin START.bat calistirin.
pause
