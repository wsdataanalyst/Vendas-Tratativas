@echo off
title Criar repositorio - wsdataanalyst/vendas-tratativas
cd /d "%~dp0"

git remote remove origin 2>nul
git remote add origin https://github.com/wsdataanalyst/Vendas-Tratativas.git

where gh >nul 2>&1
if errorlevel 1 (
    echo.
    echo  GitHub CLI (gh) nao instalado.
    echo  Instale: winget install GitHub.cli
    echo  Ou baixe: https://cli.github.com
    pause
    exit /b 1
)

echo.
echo  === Passo 1: Login no GitHub (so na primeira vez) ===
gh auth status >nul 2>&1
if errorlevel 1 (
    echo  Uma janela do navegador vai abrir. Autorize o acesso.
    gh auth login -h github.com -p https -w
    if errorlevel 1 (
        echo  Login cancelado ou falhou.
        pause
        exit /b 1
    )
)

echo.
echo  === Passo 2: Criar repositorio e enviar codigo ===
echo  Repo ja existe? Use enviar-github.bat
gh repo create wsdataanalyst/Vendas-Tratativas --public --source=. --remote=origin --push

if errorlevel 1 (
    echo.
    echo  Se o repo ja existir, tente:
    echo    git remote set-url origin https://github.com/wsdataanalyst/vendas-tratativas.git
    echo    git push -u origin main
) else (
    echo.
    echo  Pronto! Repositorio criado e codigo enviado.
    gh repo view --web
)

pause
