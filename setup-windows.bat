@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\setup-windows.ps1 %*
if errorlevel 1 (
  echo Setup did not finish. Read the error above, fix the cause, and run again.
  pause
  exit /b 1
)
pause
