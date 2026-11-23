@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title GOATS RT Manager V5.4.15.14

echo.
echo GOATS RT MANAGER V5.4.15.14 - AVVIO
echo ---------------------------------
echo Runtime Python/Qt in LOCALAPPDATA - sicuro anche da cartelle Google Drive/OneDrive.
echo.

set "BOOT=goats_bootstrap.py"
set "PYEXE="

rem Cerca un Python reale. Il virtual environment NON viene piu' creato nella
rem cartella del Manager, quindi Google Drive non puo' bloccare DLL o cache Qt.
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
) do (
    if exist %%P (
        %%P -c "import sys; assert (3,10) <= sys.version_info[:2] < (3,15)" >nul 2>nul
        if not errorlevel 1 (
            set "PYEXE=%%~P"
            goto :run
        )
    )
)

where py >nul 2>nul
if not errorlevel 1 (
    for %%V in (3.13 3.12 3.11 3.10 3.14) do (
        for /f "usebackq delims=" %%E in (`py -%%V -c "import sys,os; print(sys.executable if os.path.isfile(sys.executable) else '')" 2^>nul`) do (
            if not defined PYEXE set "PYEXE=%%E"
        )
        if defined PYEXE goto :run
    )
)

for /f "usebackq delims=" %%E in (`python -c "import sys,os; print(sys.executable if os.path.isfile(sys.executable) else '')" 2^>nul`) do set "PYEXE=%%E"
if defined PYEXE goto :run

echo ERRORE: Python reale 3.10-3.14 non trovato.
echo Installa preferibilmente Python 3.13 da python.org.
pause
exit /b 1

:run
echo Python reale trovato: %PYEXE%
"%PYEXE%" "%BOOT%"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo.
    echo Avvio terminato con codice %RC%.
    echo Esegui DIAGNOSTICA_GOATS_RT_MANAGER.bat per il dettaglio.
    pause
)
exit /b %RC%
