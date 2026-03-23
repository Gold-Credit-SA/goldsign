@echo off
echo ============================================================
echo  Gold Credit - Build Assinatura Digital ICP-Brasil
echo ============================================================
echo.

REM Verificar Python
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Instale Python 3.10+ e tente novamente.
    pause
    exit /b 1
)

REM Instalar dependencias
echo [1/3] Instalando dependencias...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
echo        OK

REM Limpar build anterior
echo [2/3] Limpando build anterior...
if exist dist\GoldCreditAssinatura.exe del /q dist\GoldCreditAssinatura.exe 2>nul
if exist build rmdir /s /q build 2>nul
if exist GoldCreditAssinatura.spec del /q GoldCreditAssinatura.spec 2>nul
echo        OK

REM Compilar executavel
echo [3/3] Compilando (pode levar 1-3 minutos)...
pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "GoldCreditAssinatura" ^
    --hidden-import=flask ^
    --hidden-import=flask.json.provider ^
    --hidden-import=flask_cors ^
    --hidden-import=werkzeug ^
    --hidden-import=werkzeug.serving ^
    --hidden-import=werkzeug.exceptions ^
    --hidden-import=jinja2 ^
    --hidden-import=click ^
    --hidden-import=cryptography ^
    --hidden-import=cryptography.hazmat.bindings._rust ^
    --hidden-import=cryptography.hazmat.primitives ^
    --hidden-import=cryptography.hazmat.primitives.asymmetric ^
    --hidden-import=cryptography.hazmat.primitives.asymmetric.padding ^
    --hidden-import=cryptography.hazmat.primitives.hashes ^
    --hidden-import=cryptography.hazmat.backends ^
    --hidden-import=cryptography.hazmat.backends.openssl ^
    --hidden-import=cryptography.x509 ^
    --hidden-import=cryptography.x509.oid ^
    --hidden-import=OpenSSL ^
    --hidden-import=OpenSSL.crypto ^
    --hidden-import=pystray ^
    --hidden-import=pystray._win32 ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=PIL.ImageDraw ^
    --hidden-import=PIL.ImageFont ^
    --collect-submodules=cryptography ^
    --collect-submodules=flask ^
    app_launcher.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Build falhou. Veja os erros acima.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  BUILD CONCLUIDO COM SUCESSO!
echo  Executavel: dist\GoldCreditAssinatura.exe
echo ============================================================
echo.
echo  Distribuicao:
echo  1. Copie dist\GoldCreditAssinatura.exe para a maquina do cliente
echo  2. Cliente executa o .exe - aparece icone na bandeja do sistema
echo  3. Servico ativo em http://localhost:8765
echo.
pause
