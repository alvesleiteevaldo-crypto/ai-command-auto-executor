@echo off
echo Construindo executavel Windows...

REM Verifica se Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado. Instale Python 3.9+ em https://python.org
    pause
    exit /b 1
)

REM Instala dependencias
echo Instalando dependencias...
pip install -r requirements.txt

REM Cria o executavel
echo Criando executavel...
pyinstaller --onefile --windowed --icon=icon.ico --name=AICommandBridge ai_bridge.py

echo.
echo Sucesso! Executavel criado em: dist\AICommandBridge.exe
echo Copie para C:\Program Files\AICommandBridge ou use o instalador.
pause
