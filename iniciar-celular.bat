@echo off
title Vendas e Tratativas - Acesso Celular
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    python -m venv .venv
    call .venv\Scripts\pip install -r requirements.txt -q
)

if not exist ".env" (
    copy .env.example .env >nul
)

echo.
echo  Encerrando versao antiga na porta 5050...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5050" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo.
echo  ========================================
echo   MODO CELULAR - link na internet
echo   (nao precisa mesma Wi-Fi)
echo  ========================================
echo.

set USAR_TUNEL=1
start "" "http://127.0.0.1:5050/login"
.venv\Scripts\python.exe run.py
pause
