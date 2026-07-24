# -*- mode: python ; coding: utf-8 -*-
#
# Build (Windows, via GitHub Actions): pyinstaller fileswift.spec
#
# Gera uma pasta (onedir, não onefile) em dist/FileSwift/ com o executável e
# tudo que ele precisa. onedir foi escolhido em vez de onefile porque inicia
# mais rápido (onefile precisa se auto-extrair pra uma pasta temp toda vez) e
# tem taxa de falso-positivo de antivírus/SmartScreen bem menor. O Inno Setup
# depois empacota essa pasta inteira num instalador único.

from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static/logo.png', 'static')]
binaries = []
hiddenimports = ['PIL._tkinter_finder']

# zeroconf/ifaddr têm imports condicionais por plataforma (backend Windows),
# qrcode/PIL têm plugins carregados dinamicamente — collect_all() em vez de
# tentar adivinhar hidden imports um por um, mais robusto pra quem não
# consegue testar localmente em Windows.
for pkg in ('zeroconf', 'ifaddr', 'qrcode', 'PIL'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['FileSwift.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FileSwift',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='windows/fileswift.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FileSwift',
)
