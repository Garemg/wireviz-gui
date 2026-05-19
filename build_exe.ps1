# build_exe.ps1
# Compila wireviz-gui en un .exe standalone para Windows.
# Requisito previo: Graphviz instalado en el sistema (dot.exe en el PATH).
# No requiere entorno virtual.

$ErrorActionPreference = "Stop"
$python = "C:/Users/Emilio/AppData/Local/Programs/Python/Python313/python.exe"

Write-Host "=== wireviz-gui Build Script ===" -ForegroundColor Cyan

# Verificar Python
Write-Host "`n[1/4] Verificando Python..." -ForegroundColor Yellow
& $python --version

# Verificar dependencias criticas
Write-Host "`n[2/4] Verificando dependencias..." -ForegroundColor Yellow
& $python -c "import wireviz, graphviz, PIL, tk_tools, click, yaml, PyInstaller; print('  Todas las dependencias OK')"

# Limpiar build anterior
Write-Host "`n[3/4] Limpiando builds anteriores..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# Compilar (PyInstaller escribe INFO por stderr; desactivar Stop temporalmente)
Write-Host "`n[4/4] Compilando con PyInstaller..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
& $python -m PyInstaller wireviz_gui.spec --clean
$ErrorActionPreference = "Stop"
$buildOk = Test-Path "dist\wireviz-gui.exe"

if ($buildOk) {
    Write-Host "`n=== BUILD EXITOSO ===" -ForegroundColor Green
    Write-Host "Ejecutable generado en: dist\wireviz-gui.exe" -ForegroundColor Green
    Write-Host "`nNOTA: Graphviz debe estar instalado en el sistema y en el PATH." -ForegroundColor Magenta
    Write-Host "      Descarga: https://graphviz.org/download/" -ForegroundColor Magenta
} else {
    Write-Host "`n=== BUILD FALLIDO ===" -ForegroundColor Red
    exit 1
}
