@echo off
REM ============================================================
REM  RKE Payroll - one-click installer
REM  Right-click this file and choose "Run as administrator".
REM  No Microsoft Store, no Python, no internet tools needed.
REM ============================================================
title RKE Payroll Setup

REM --- must run elevated to add the Defender exclusion ---
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo   Please right-click install.bat and choose
    echo   "Run as administrator", then try again.
    echo.
    pause
    exit /b 1
)

set "APPDIR=%LOCALAPPDATA%\RKE Payroll"
set "EXE=%APPDIR%\RKE_Payroll.exe"
set "URL=https://github.com/shivanshxx/RKE/releases/latest/download/RKE_Payroll.exe"

echo.
echo  ============================================
echo    RKE Payroll - Setup
echo  ============================================
echo.
echo  Installing to: %APPDIR%
echo.

if not exist "%APPDIR%" mkdir "%APPDIR%"

REM --- 1. Tell Defender to leave this folder alone (BEFORE downloading) ---
echo  [1/4] Allowing the folder in Windows Defender...
powershell -NoProfile -Command ^
  "try { Add-MpPreference -ExclusionPath '%APPDIR%' -ErrorAction Stop; Write-Host '        done.' } catch { Write-Host '        skipped (Defender not active or already set)' }"

REM --- 2. Download the latest version ---
echo  [2/4] Downloading the latest version (about 27 MB)...
powershell -NoProfile -Command ^
  "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '%URL%' -OutFile '%EXE%' -UseBasicParsing; Write-Host '        done.' } catch { Write-Host ('        FAILED: ' + $_.Exception.Message); exit 1 }"
if %errorLevel% neq 0 (
    echo.
    echo   Download failed. Check the internet connection and run this again.
    echo.
    pause
    exit /b 1
)

REM --- 3. Sanity-check the file actually arrived ---
echo  [3/4] Checking the download...
for %%A in ("%EXE%") do set SIZE=%%~zA
if not defined SIZE goto badfile
if %SIZE% LSS 5000000 goto badfile
echo        file is OK (%SIZE% bytes).

REM --- 4. Desktop shortcut ---
echo  [4/4] Creating a Desktop shortcut...
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\RKE Payroll.lnk'); $s.TargetPath='%EXE%'; $s.WorkingDirectory='%APPDIR%'; $s.Save(); Write-Host '        done.'"

echo.
echo  ============================================
echo    Setup complete.
echo.
echo    Start it from the "RKE Payroll" icon
echo    on the Desktop.
echo.
echo    Your data is stored in:
echo    %APPDIR%
echo  ============================================
echo.
pause
exit /b 0

:badfile
echo.
echo   The downloaded file is damaged or was blocked by antivirus.
echo   Run this installer again as administrator.
echo.
del "%EXE%" >nul 2>&1
pause
exit /b 1
