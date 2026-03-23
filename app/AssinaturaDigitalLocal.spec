# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['flask', 'flask.json.provider', 'flask_cors', 'werkzeug', 'werkzeug.serving', 'werkzeug.exceptions', 'jinja2', 'click', 'cryptography', 'cryptography.hazmat.bindings._rust', 'cryptography.hazmat.primitives', 'cryptography.hazmat.primitives.asymmetric', 'cryptography.hazmat.primitives.asymmetric.padding', 'cryptography.hazmat.primitives.hashes', 'cryptography.hazmat.backends', 'cryptography.hazmat.backends.openssl', 'cryptography.x509', 'cryptography.x509.oid', 'OpenSSL', 'OpenSSL.crypto', 'pystray', 'pystray._win32', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont']
hiddenimports += collect_submodules('cryptography')
hiddenimports += collect_submodules('flask')


a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AssinaturaDigitalLocal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
