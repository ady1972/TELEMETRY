@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GOATS RT Manager V5.4.15.11 - DIPENDENZE

echo Le dipendenze Python/Qt sono ora installate in:
echo %%LOCALAPPDATA%%\GOATS_RT_Manager
echo e NON nella cartella sincronizzata del Manager.
echo.
echo Avvio il bootstrap GOATS...
call AVVIA_GOATS_RT_MANAGER_V5.bat
exit /b %ERRORLEVEL%
