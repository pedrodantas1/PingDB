# -*- mode: python ; coding: utf-8 -*-

# Este é um arquivo de especificações para o PyInstaller.
# Ele nos dá mais controle sobre o processo de compilação.

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pyodbc', 'pkg_resources.py2_warn'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['unittest', 'pydoc', 'bz2', 'select'], # Exclui módulos desnecessários
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PingDB',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Diz ao PyInstaller para usar o UPX se ele o encontrar
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Equivalente a --noconsole
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None # Você pode adicionar um ícone aqui, ex: icon='app.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True, # Também comprime as DLLs e outros binários
    upx_exclude=[],
    name='PingDB', # Nome da pasta de saída
)
