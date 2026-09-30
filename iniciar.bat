@echo off
REM ============================================================
REM  Git Facil - abre o aplicativo no navegador
REM ============================================================
cd /d "%~dp0"
title Git Facil (nao feche esta janela enquanto usar o app)

if not exist ".venv\Scripts\python.exe" (
    echo  O Git Facil ainda nao foi instalado. Rode primeiro o arquivo instalar.bat
    pause
    exit /b 1
)

REM Evita a pergunta de e-mail do Streamlit na primeira execucao
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
    (
        echo [general]
        echo email = ""
    ) > "%USERPROFILE%\.streamlit\credentials.toml"
)

REM Se o app ja estiver aberto, so abre o navegador de novo
netstat -ano | findstr ":8501" | findstr "LISTENING" >nul
if not errorlevel 1 (
    start "" http://localhost:8501
    exit /b 0
)

".venv\Scripts\python.exe" -m streamlit run app.py
