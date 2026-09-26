@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo AI COMMAND BRIDGE 2.0 - BUILD WINDOWS
echo ==========================================

python --version >nul 2>&1
if errorlevel 1 (
  echo ERRO: Python 3.10+ nao encontrado.
  pause
  exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements-v2.txt
if errorlevel 1 goto :erro

python -m py_compile ai_bridge_v2.pyw
if errorlevel 1 goto :erro

python -m PyInstaller --noconfirm --clean --onefile --windowed --name AICommandBridge ai_bridge_v2.pyw
if errorlevel 1 goto :erro

set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo.
  echo EXE criado em dist\AICommandBridge.exe
  echo Para criar o instalador, instale o Inno Setup 6 e rode este arquivo novamente.
  pause
  exit /b 0
)

"%ISCC%" installer-v2.iss
if errorlevel 1 goto :erro

echo.
echo PRONTO:
echo dist\AICommandBridge.exe
echo dist\installer\AICommandBridge-Setup-2.0.0.exe
pause
exit /b 0

:erro
echo.
echo FALHA NA COMPILACAO.
pause
exit /b 1
