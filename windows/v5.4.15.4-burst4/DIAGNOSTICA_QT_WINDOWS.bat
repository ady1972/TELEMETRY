@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GOATS RT Manager V5.4.13.6 - QT WINDOWS
call DIAGNOSTICA_GOATS_RT_MANAGER.bat
exit /b %ERRORLEVEL%
