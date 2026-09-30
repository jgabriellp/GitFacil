@echo off
REM ============================================================
REM  Git Facil - instalacao (rodar uma unica vez)
REM ============================================================
cd /d "%~dp0"
title Instalando o Git Facil

echo.
echo  Instalando o Git Facil...
echo.

REM --- 1. Verifica o Python ---------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado.
    echo  Instale em https://www.python.org/downloads/
    echo  IMPORTANTE: marque a opcao "Add python.exe to PATH" na instalacao.
    echo.
    pause
    exit /b 1
)

REM --- 2. Verifica o Git ------------------------------------------------
git --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Git nao encontrado.
    echo  Instale em https://git-scm.com/download/win
    echo  Pode aceitar todas as opcoes padrao da instalacao.
    echo.
    pause
    exit /b 1
)

REM --- 3. Cria o ambiente e instala as dependencias ---------------------
echo  [1/3] Preparando o ambiente...
if not exist ".venv" python -m venv .venv
if errorlevel 1 goto erro

echo  [2/3] Instalando componentes (pode levar alguns minutos)...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
if errorlevel 1 goto erro

REM --- 4. Cria o atalho na area de trabalho -----------------------------
echo  [3/3] Criando atalho na area de trabalho...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Git Facil.lnk');" ^
  "$s.TargetPath = '%~dp0iniciar.bat';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.WindowStyle = 7;" ^
  "$s.IconLocation = 'shell32.dll,146';" ^
  "$s.Save()"

echo.
echo  ============================================================
echo   Pronto! Use o atalho "Git Facil" na sua area de trabalho.
echo  ============================================================
echo.
pause
exit /b 0

:erro
echo.
echo  [ERRO] A instalacao nao terminou. Tire um print desta tela
echo  e envie ao responsavel.
echo.
pause
exit /b 1
