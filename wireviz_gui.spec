# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

# Automatically resolve paths relative to this .spec file
SPEC_DIR = Path(SPECPATH)

# wireviz HTML templates must be bundled
import wireviz as _wv
WIREVIZ_TEMPLATES = Path(_wv.__file__).parent / "templates"

# ── Optional: bundled Graphviz (copied by build_exe.ps1 to vendor/graphviz/) ──
# IMPORTANT: use 'datas' NOT 'binaries' for Graphviz files.
# When listed as 'binaries', PyInstaller follows DLL dependencies of dot.exe
# and pulls in Graphviz's tcl86.dll (8.6.10), which conflicts with Python's
# tcl86.dll (8.6.15). As 'datas', files are copied as-is with no DLL scan.
# __main__.py adds sys._MEIPASS/graphviz to PATH at startup so dot.exe works.
VENDOR_GV = SPEC_DIR / "vendor" / "graphviz"
gv_datas = []
if VENDOR_GV.exists():
    for f in VENDOR_GV.iterdir():
        if f.is_file():  # incluir todo: .exe, .dll y config8 (registro de plugins)
            gv_datas.append((str(f), "graphviz"))
    print(f"  [spec] Graphviz: {len(gv_datas)} files as datas (sin escaneo de DLL)")

# ── Optional: company logo ────────────────────────────────────────────────────
LOGO = SPEC_DIR / "images" / "logo-torsa.jpg"
extra_datas = []
if LOGO.exists():
    extra_datas.append((str(LOGO), "images"))
    print("  [spec] Bundling logo-torsa.jpg")

a = Analysis(
    [str(SPEC_DIR / 'wireviz_gui' / '__main__.py')],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=[
        # wireviz HTML report templates
        (str(WIREVIZ_TEMPLATES), 'wireviz/templates'),
    ] + extra_datas + gv_datas,
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
        'playwright',
        'playwright.sync_api',
        'playwright._impl._api_types',
        'playwright._impl._browser_type',
        'playwright._impl._page',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

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
