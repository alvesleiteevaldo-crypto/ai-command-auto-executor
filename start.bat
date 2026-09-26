@echo off
setlocal
cd /d "%~dp0"

if exist "AICommandBridge.exe" (
  start "" "AICommandBridge.exe"
  exit /b 0
)

if exist "dist\AICommandBridge.exe" (
  start "" "dist\AICommandBridge.exe"
  exit /b 0
)

pythonw ai_bridge_v2.pyw
