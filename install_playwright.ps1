# install_playwright.ps1
# Instala el navegador Chromium necesario para la generacion de PDF.
# Ejecutar una vez en cada equipo donde se quiera usar la exportacion a PDF.

$ErrorActionPreference = "Stop"

Write-Host "=== Instalador de Playwright / Chromium ===" -ForegroundColor Cyan
Write-Host "Este script instala el navegador headless necesario para generar PDF."

# Detectar playwright: primero en el venv, luego en el sistema
$playwrightCmd = $null
if (Test-Path ".venv\Scripts\playwright.exe") {
    $playwrightCmd = ".\.venv\Scripts\playwright.exe"
} elseif (Get-Command playwright -ErrorAction SilentlyContinue) {
    $playwrightCmd = "playwright"
} else {
    # Intentar via python -m playwright
    $python = if (Test-Path ".venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
    Write-Host "`nInstalando Playwright..." -ForegroundColor Yellow
    & $python -m pip install playwright --quiet
    $playwrightCmd = "$python -m playwright"
}

Write-Host "`nDescargando Chromium (~150 MB)..." -ForegroundColor Yellow
if ($playwrightCmd -eq "$python -m playwright") {
    & $python -m playwright install chromium
} else {
    & $playwrightCmd install chromium
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== Chromium instalado correctamente ===" -ForegroundColor Green
    Write-Host "La exportacion a PDF ya esta disponible en wireviz-gui." -ForegroundColor Green
} else {
    Write-Host "`nERROR: La instalacion de Chromium fallo." -ForegroundColor Red
    Write-Host "Prueba manualmente: playwright install chromium" -ForegroundColor Yellow
    exit 1
}
