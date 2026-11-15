@echo off
setlocal
set "VER=9.4.1"
set "BASE=%~dp0.gradle-dist"
set "GRADLE=%BASE%\gradle-%VER%\bin\gradle.bat"
set "ZIP=%TEMP%\gradle-%VER%-bin.zip"
if not exist "%GRADLE%" (
  if not exist "%BASE%" mkdir "%BASE%"
  echo Download Gradle %VER%...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://services.gradle.org/distributions/gradle-9.4.1-bin.zip' -OutFile '%ZIP%'; Expand-Archive -Path '%ZIP%' -DestinationPath '%BASE%' -Force"
  if errorlevel 1 exit /b 1
)
call "%GRADLE%" %*
exit /b %ERRORLEVEL%
