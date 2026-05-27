# build_exe.ps1
# Compila wireviz-gui en un .exe standalone para Windows.
# Usa el entorno virtual del proyecto (.venv) si existe; si no, el Python del sistema.
# Ejecutar desde la raiz del repositorio: .\build_exe.ps1

$ErrorActionPreference = "Stop"

# ── Detectar Python ──────────────────────────────────────────────────────────
if (Test-Path ".venv\Scripts\python.exe") {
    $python = ".\.venv\Scripts\python.exe"
    Write-Host "  Python desde venv: $python" -ForegroundColor DarkGray
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = (Get-Command python | Select-Object -ExpandProperty Source)
    Write-Host "  Python del sistema: $python" -ForegroundColor DarkGray
} else {
    Write-Host "ERROR: Python no encontrado. Crea el entorno virtual primero:" -ForegroundColor Red
    Write-Host "  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .venv\Scripts\pip install -e .[dev]" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== wireviz-gui Build Script ===" -ForegroundColor Cyan

# ── Verificar Python ─────────────────────────────────────────────────────────
Write-Host "`n[1/5] Verificando Python..." -ForegroundColor Yellow
& $python --version

# ── Verificar dependencias ───────────────────────────────────────────────────
Write-Host "`n[2/5] Verificando dependencias..." -ForegroundColor Yellow
& $python -c "import wireviz, graphviz, PIL, tk_tools, click, yaml, PyInstaller; print('  Todas las dependencias OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Faltan dependencias. Ejecuta:" -ForegroundColor Red
    Write-Host "  .venv\Scripts\pip install -e .[dev]" -ForegroundColor Yellow
    exit 1
}

# ── Bundlear Graphviz si está en PATH ────────────────────────────────────────
Write-Host "`n[3/5] Buscando Graphviz para bundlear..." -ForegroundColor Yellow
$gvCmd = Get-Command dot -ErrorAction SilentlyContinue
$vendorDir = "vendor\graphviz"
if ($gvCmd) {
    $gvBin = Split-Path $gvCmd.Source
    Write-Host "  Graphviz encontrado en: $gvBin" -ForegroundColor Green
    if (-not (Test-Path $vendorDir)) {
        Write-Host "  Copiando binarios Graphviz a $vendorDir ..." -ForegroundColor DarkGray
        New-Item -ItemType Directory -Force $vendorDir | Out-Null
        # Copiar ejecutables, DLLs y archivo config de Graphviz al vendor.
        # EXCLUIR Tcl/Tk: sus DLLs (tcl86.dll / tk86.dll) conflictan con los de
        # Python 3.13 que PyInstaller bundlea. En el EXE, dot.exe encontrará
        # tcl86.dll de Python (compatible 8.6.x) via _MEIPASS en PATH.
        # INCLUIR config8 (o config6): sin él dot.exe no encuentra sus plugins
        # y devuelve "Format not recognized".
        Get-ChildItem -Path $gvBin -File | Where-Object {
            ($_.Extension -in ".exe", ".dll" -or $_.Name -match "^config") -and
            $_.Name -notmatch '^(tcl|tk)'
        } | ForEach-Object { Copy-Item $_.FullName $vendorDir -ErrorAction SilentlyContinue }
        Write-Host "  Graphviz copiado a vendor\graphviz\" -ForegroundColor Green
    } else {
        Write-Host "  vendor\graphviz\ ya existe, se usara la copia guardada." -ForegroundColor DarkGray
    }
} else {
    Write-Host "  AVISO: Graphviz no encontrado en PATH." -ForegroundColor Yellow
    if (Test-Path $vendorDir) {
        Write-Host "  Usando copia previa en vendor\graphviz\" -ForegroundColor DarkGray
    } else {
        Write-Host "  El EXE dependera de que Graphviz este instalado en el equipo destino." -ForegroundColor Yellow
        Write-Host "  Descarga: https://graphviz.org/download/" -ForegroundColor Yellow
    }
}

# ── Limpiar build anterior ───────────────────────────────────────────────────
Write-Host "`n[4/5] Limpiando builds anteriores..." -ForegroundColor Yellow
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# ── Compilar ─────────────────────────────────────────────────────────────────
Write-Host "`n[5/5] Compilando con PyInstaller..." -ForegroundColor Yellow

# CRÍTICO: quitar Graphviz del PATH mientras corre PyInstaller.
# El hook-_tkinter.py de PyInstaller escanea dependencias DLL y puede encontrar
# tcl86.dll de Graphviz (v8.6.10) antes que el de Python (v8.6.15), metiéndolo
# en _MEIPASS/tcl86.dll. El _tcl_data/init.tcl de Python requiere exactamente
# 8.6.15, lo que causa: "version conflict for package Tcl: have 8.6.10, need 8.6.15".
$savedPath = $env:PATH
$env:PATH = ($env:PATH -split ";" | Where-Object { $_ -notmatch "(?i)graphviz" }) -join ";"
Write-Host "  PATH de Graphviz ocultado al hook de PyInstaller" -ForegroundColor DarkGray

$ErrorActionPreference = "Continue"
& $python -m PyInstaller wireviz_gui.spec --clean 2>&1
$ErrorActionPreference = "Stop"

$env:PATH = $savedPath  # restaurar PATH original

$buildOk = Test-Path "dist\wireviz-gui.exe"
if ($buildOk) {
    $size = [math]::Round((Get-Item "dist\wireviz-gui.exe").Length / 1MB, 1)
    Write-Host "`n=== BUILD EXITOSO ===" -ForegroundColor Green
    Write-Host "Ejecutable: dist\wireviz-gui.exe ($size MB)" -ForegroundColor Green
    if (Test-Path $vendorDir) {
        Write-Host "Graphviz: bundleado (el EXE no necesita Graphviz instalado)" -ForegroundColor Green
    } else {
        Write-Host "NOTA: instalar Graphviz en el equipo destino:" -ForegroundColor Magenta
        Write-Host "      https://graphviz.org/download/" -ForegroundColor Magenta
    }
    Write-Host "`nPara generar PDF en el equipo destino, ejecutar:" -ForegroundColor Cyan
    Write-Host "  .\install_playwright.ps1" -ForegroundColor Cyan
} else {
    Write-Host "`n=== BUILD FALLIDO ===" -ForegroundColor Red
    exit 1
}
