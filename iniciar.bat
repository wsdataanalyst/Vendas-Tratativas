@echo off
title Vendas e Tratativas - Modo Local
cd /d "%~dp0"

echo.
echo  ========================================
echo   MODO LOCAL (PC precisa ficar ligado)
echo.
echo   Para celular SEM depender do PC:
echo   Leia: COMO-USAR-NA-NUVEM.md
echo   (Render + Supabase - GRATIS)
echo  ========================================
echo.
pause

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    call .venv\Scripts\pip install -r requirements.txt -q
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5050" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul

start "" "http://127.0.0.1:5050/login"
.venv\Scripts\python.exe run.py
pause
