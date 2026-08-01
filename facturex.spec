# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import nicegui

nicegui_path = os.path.dirname(nicegui.__file__)
block_cipher = None

datas = [
    (nicegui_path, 'nicegui'),
    ('assets', 'assets'),
]

# Inclusion de la base de données SQLite FactureX.db si elle existe
if os.path.exists('FactureX.db'):
  datas.append(('FactureX.db', '.'))

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'nicegui',
        'uvicorn',
        'starlette',
        'sqlite3',
        'reportlab',
        'database',
        'ui_parametres',
        'ui_prestations',
        'ui_clients',
        'ui_devis',
        'ui_interventions',
        'ui_factures',
        'ui_analytics',
        'ui_passerelle',
        'ui_maintenance',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Dans facturex.spec :

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EasyFacture',  # <-- L'exécutable généré s'appellera EasyFacture.exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico'
    if os.path.exists('assets/logo.ico')
    else None,  # <-- Icône appliquée à l'exe
)