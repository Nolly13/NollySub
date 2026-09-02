@echo off
chcp 65001 > nul
title NollySub - Anime Turkce Altyazi Indirici
cd /d "%~dp0"

echo ========================================================
echo   NollySub Baslatiliyor...
echo ========================================================

where py >nul 2>nul
if %errorlevel% == 0 (
    py nollysub.py
    if %errorlevel% neq 0 (
        echo.
        echo [HATA] Uygulama calisirken bir hata olustu.
        pause
    )
    exit /b
)

where python >nul 2>nul
if %errorlevel% == 0 (
    python nollysub.py
    if %errorlevel% neq 0 (
        echo.
        echo [HATA] Uygulama calisirken bir hata olustu.
        pause
    )
    exit /b
)

if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" nollysub.py
    if %errorlevel% neq 0 (
        echo.
        echo [HATA] Uygulama calisirken bir hata olustu.
        pause
    )
    exit /b
)

echo.
echo [HATA] Python sisteminizde bulunamadi!
echo Lutfen Python 3'un yuklu oldugundan emin olun.
echo.
pause
