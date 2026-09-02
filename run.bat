@echo off
chcp 65001 > nul
title NollySub Launcher
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel% == 0 (
    py nollysub.py
    if %errorlevel% neq 0 pause
    exit /b
)

where python >nul 2>nul
if %errorlevel% == 0 (
    python nollysub.py
    if %errorlevel% neq 0 pause
    exit /b
)

if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" nollysub.py
    if %errorlevel% neq 0 pause
    exit /b
)

echo [HATA] Python bulunamadi!
pause
