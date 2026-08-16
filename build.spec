# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# reportlab imports PIL lazily; PyInstaller does not always pick the whole
# package up on its own, and a partial PIL makes the built .exe fail at
# startup with "cannot import name 'Image' from 'PIL'". Collect it in full.
pil_datas, pil_binaries, pil_hidden = collect_all('PIL')

# ttkbootstrap ships icon/font assets (bootstrap.ttf and friends) that are
# loaded from disk at startup. Without them the built .exe dies immediately
# with FileNotFoundError on bootstrap.ttf, so collect the package in full.
tb_datas, tb_binaries, tb_hidden = collect_all('ttkbootstrap')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pil_binaries + tb_binaries,
    datas=pil_datas + tb_datas,
    hiddenimports=['reportlab', 'openpyxl'] + pil_hidden + tb_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RKE_Payroll',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
