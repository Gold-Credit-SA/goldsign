@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  Gold Credit - Build do Instalador
echo ============================================================
echo.

set "APP_DIR=%~dp0"
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "SCRIPT=%APP_DIR%GoldCreditAssinaturaInstaller.iss"

if not exist "!APP_DIR!dist\GoldCreditAssinatura.exe" (
    echo [ERRO] Executavel nao encontrado em dist\GoldCreditAssinatura.exe
    echo Gere primeiro o app com o build normal.
    exit /b 1
)

if not exist "!ISCC!" (
    echo [ERRO] Inno Setup nao encontrado em:
    echo !ISCC!
    exit /b 1
)

if exist "!APP_DIR!installer\GoldCreditAssinaturaSetup.exe" del /q "!APP_DIR!installer\GoldCreditAssinaturaSetup.exe" 2>nul

echo [1/1] Compilando instalador...
"!ISCC!" "!SCRIPT!"
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao compilar o instalador.
    exit /b 1
)

echo.
echo ============================================================
echo  INSTALADOR GERADO COM SUCESSO
echo  Arquivo: installer\GoldCreditAssinaturaSetup.exe
echo ============================================================
echo.

endlocal
