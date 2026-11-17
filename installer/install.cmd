@echo off
setlocal EnableExtensions

set "SETUP_ROOT=%~dp0"
set "PAYLOAD_ARCHIVE=%SETUP_ROOT%SkyCityPayload.tar"
set "EXTRACT_ROOT=%TEMP%\SkyCitySetup_%RANDOM%_%RANDOM%"

if not exist "%PAYLOAD_ARCHIVE%" (
    echo Sky City payload is missing.
    exit /b 2
)

mkdir "%EXTRACT_ROOT%" >nul 2>&1
if errorlevel 1 (
    echo Could not create a temporary extraction directory.
    exit /b 3
)

tar.exe -xf "%PAYLOAD_ARCHIVE%" -C "%EXTRACT_ROOT%"
if errorlevel 1 (
    echo Could not unpack the Sky City payload.
    rmdir /s /q "%EXTRACT_ROOT%" >nul 2>&1
    exit /b 4
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SETUP_ROOT%install.ps1" -PayloadRoot "%EXTRACT_ROOT%"
set "INSTALL_RESULT=%ERRORLEVEL%"
rmdir /s /q "%EXTRACT_ROOT%" >nul 2>&1
exit /b %INSTALL_RESULT%
