@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title GOATS RT MANAGER V5.4.15.12 - DIAGNOSTICA

echo GOATS RT MANAGER V5.4.15.12 - DIAGNOSTICA
echo.
set "PYEXE="
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%ProgramFiles%\Python314\python.exe"
) do if not defined PYEXE if exist %%P set "PYEXE=%%~P"

if not defined PYEXE (
    where py >nul 2>nul
    if not errorlevel 1 for /f "usebackq delims=" %%E in (`py -3.13 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%E"
)
if not defined PYEXE (
    echo Python reale non trovato.
    pause
    exit /b 1
)

"%PYEXE%" "goats_bootstrap.py" --diagnose
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
