@echo off
title Enviar codigo para GitHub
cd /d "%~dp0"

git remote set-url origin https://github.com/wsdataanalyst/Vendas-Tratativas.git

echo.
echo  Enviando para: https://github.com/wsdataanalyst/Vendas-Tratativas
echo  (inclui render.yaml para o Render)
echo.

git push -u origin main
if errorlevel 1 (
    echo.
    echo  ERRO no push. Faca login:
    echo    gh auth login
    echo  Ou use token do GitHub como senha.
    pause
    exit /b 1
)

git push origin main:master
echo.
echo  OK! Codigo enviado.
echo  No Render, use a branch: main
echo  (ou master - ambas terao o codigo)
echo.
pause
