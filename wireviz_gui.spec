# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Automatically resolve paths relative to this .spec file
SPEC_DIR = Path(SPECPATH)

# wireviz HTML templates must be bundled
import wireviz as _wv
WIREVIZ_TEMPLATES = Path(_wv.__file__).parent / "templates"

a = Analysis(
    [str(SPEC_DIR / 'wireviz_gui' / '__main__.py')],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=[
        # wireviz HTML report templates
        (str(WIREVIZ_TEMPLATES), 'wireviz/templates'),
    ],
    hiddenimports=[
        'wireviz',
        'wireviz.wireviz',
        'wireviz.DataClasses',
        'wireviz.Harness',
        'wireviz.wv_colors',
        'wireviz.wv_helper',
        'wireviz.wv_bom',
        'wireviz.wv_gv_html',
        'wireviz.wv_html',
        'wireviz.svgembed',
        'tk_tools',
        'tk_tools.tooltips',
        'tk_tools.widgets',
        'tk_tools.groups',
        'tk_tools.canvas',
        'tk_tools.images',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'graphviz',
        'click',
        'yaml',
        'engineering_notation',
        'stringify',
        'jinja2',
        'jinja2.ext',
        'markupsafe',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wireviz-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=str(SPEC_DIR / 'images' / 'slightlynybbled_icon.ico'),
)
