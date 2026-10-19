@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run setup-windows.bat first.
  pause
  exit /b 1
)
echo Keep the Studio app running so local Ollama and ComfyUI services are available.
echo Do not render another video at the same time. This test actually generates AI scenes.
.venv\Scripts\python.exe scripts\selftest.py --full %*
if errorlevel 1 (
  echo AI test failed. Check the error and work\logs.
  pause
  exit /b 1
)
pause
